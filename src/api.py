import logging
import time
import uuid
from fastapi import FastAPI, HTTPException, Request, Query, BackgroundTasks
from fastapi.responses import JSONResponse

from .schemas import (
    EvaluateRequest,
    EvaluateResponse,
    HistoryResponse,
    HistoryTaskItem,
    HistoryRecordItem,
    BatchEvaluateRequest,
    BatchEvaluateResponse,
    TaskStatusResponse,
    TaskRecordItem,
)
from .wrapper import ModelWrapper
from .trust_pipeline import TrustPipeline
from sqlalchemy.orm import joinedload
from .database import get_engine, SessionLocal, Base
from .models import EvaluationTask, EvaluationRecord

#======日志======
logger = logging.getLogger("mm_trustbench")
logger.setLevel(logging.INFO)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(h)

#======应用入口======
app = FastAPI(title="MM-TrustBench API", version="0.1.0")


#======全局异常处理======
# 对外统一返回 JSON：{code, message, data}，便于前端统一解析
@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.detail, "data": None},
    )


@app.exception_handler(Exception)
def general_exception_handler(request: Request, exc: Exception):
    logger.exception("未捕获异常: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务器内部错误", "data": None},
    )

# 启动时建表（库不存在则自动创建）
Base.metadata.create_all(bind=get_engine())

# 引擎只实例化一次，复用
_wrapper = ModelWrapper()
_pipeline = TrustPipeline(_wrapper)


def _run_batch_evaluate(task_id_uuid: str, items: list[dict]) -> None:
    """
    后台执行批量评测：按 task_id 找到 Task，逐条跑 pipeline 写 Record，最后更新 Task 状态与耗时。
    """
    db = SessionLocal()
    try:
        task = db.query(EvaluationTask).filter(EvaluationTask.task_id == task_id_uuid).first()
        if not task:
            logger.warning("batch task not found: %s", task_id_uuid)
            return
        t0 = time.perf_counter()
        for i, it in enumerate(items):
            try:
                result = _pipeline.process(
                    image_path=it.get("image_path"),
                    question=it.get("question", ""),
                    image_base64=it.get("image_base64"),
                )
                if it.get("image_base64"):
                    img_stored = f"[base64, len={len(it['image_base64'])}]"
                else:
                    img_stored = it.get("image_path") or ""
                rec = EvaluationRecord(
                    task_id=task.id,
                    question=it.get("question", ""),
                    image_base64=img_stored,
                    final_answer=result["answer"],
                    evidence=result.get("evidence", ""),
                    self_check=result.get("self_check", ""),
                )
                db.add(rec)
                db.commit()
                logger.info("batch [%s] 第 %d/%d 条完成", task_id_uuid, i + 1, len(items))
            except Exception as e:
                logger.warning("batch 单条失败: %s", e)
                db.rollback()
        elapsed = time.perf_counter() - t0
        task.status = "completed"
        task.total_duration_sec = round(elapsed)
        db.commit()
        logger.info("batch 完成: task_id=%s, 共 %d 条, 耗时=%.2fs", task_id_uuid, len(items), elapsed)
    except Exception as e:
        logger.exception("batch 异常: %s", e)
        if db:
            task = db.query(EvaluationTask).filter(EvaluationTask.task_id == task_id_uuid).first()
            if task:
                task.status = "failed"
                db.commit()
    finally:
        db.close()


#======探针======
# 服务是否存活，运维/前端轮询用
@app.get("/ping")
def ping():
    return {"status": "ok"}


#======评测接口======
@app.post("/api/v1/evaluate", response_model=EvaluateResponse)
def evaluate(request: EvaluateRequest):
    if not request.image_path and not request.image_base64:
        raise HTTPException(status_code=400, detail="必须提供图片路径或Base64")
    t0 = time.perf_counter()
    logger.info("evaluate 请求: question=%s", request.question[:50] if request.question else "")
    try:
        result = _pipeline.process(
            image_path=request.image_path,
            question=request.question,
            image_base64=request.image_base64,
        )
        elapsed = time.perf_counter() - t0
        logger.info("evaluate 完成: answer=%s, 耗时=%.2fs", result.get("answer"), elapsed)
        resp = EvaluateResponse(
            final_answer=result["answer"],
            evidence=result.get("evidence", ""),
            self_check=result.get("self_check", ""),
        )
        # 一主一从：先写 Task，再写 Record
        if request.image_base64:
            image_stored = f"[base64, len={len(request.image_base64)}]"
        else:
            image_stored = request.image_path or ""
        db = SessionLocal()
        try:
            task = EvaluationTask(
                task_id=str(uuid.uuid4()),
                status="completed",
                model_name=getattr(_wrapper, "model", None),
                total_duration_sec=round(elapsed),
            )
            db.add(task)
            db.flush()
            record = EvaluationRecord(
                task_id=task.id,
                question=request.question,
                image_base64=image_stored,
                final_answer=result["answer"],
                evidence=result.get("evidence", ""),
                self_check=result.get("self_check", ""),
            )
            db.add(record)
            db.commit()
        finally:
            db.close()
        return resp
    except Exception as e:
        logger.warning("evaluate 失败: %s", e)
        raise HTTPException(status_code=500, detail="模型调用失败")


#======批量评测（异步）======
# 立即返回 task_id，后台执行；前端轮询 GET /api/v1/task/{task_id}
@app.post("/api/v1/evaluate/batch", response_model=BatchEvaluateResponse)
def evaluate_batch(request: BatchEvaluateRequest, background_tasks: BackgroundTasks):
    if not request.items:
        raise HTTPException(status_code=400, detail="items 不能为空")
    db = SessionLocal()
    try:
        task = EvaluationTask(
            task_id=str(uuid.uuid4()),
            status="processing",
            model_name=getattr(_wrapper, "model", None),
        )
        db.add(task)
        db.commit()
        task_id_uuid = task.task_id
    finally:
        db.close()
    # 序列化为可传参的 dict 列表
    items_payload = []
    for it in request.items:
        items_payload.append({
            "question": it.question,
            "image_path": it.image_path,
            "image_base64": it.image_base64,
        })
    background_tasks.add_task(_run_batch_evaluate, task_id_uuid, items_payload)
    logger.info("batch 已提交: task_id=%s, 共 %d 条", task_id_uuid, len(items_payload))
    return BatchEvaluateResponse(task_id=task_id_uuid, status="processing")


#======任务状态（轮询）======
@app.get("/api/v1/task/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str):
    db = SessionLocal()
    try:
        task = db.query(EvaluationTask).options(joinedload(EvaluationTask.records)).filter(EvaluationTask.task_id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        return TaskStatusResponse(
            task_id=task.task_id,
            status=task.status,
            started_at=task.started_at,
            model_name=task.model_name,
            total_duration_sec=task.total_duration_sec,
            records=[
                TaskRecordItem(
                    question=r.question,
                    final_answer=r.final_answer,
                    evidence=r.evidence,
                    self_check=r.self_check,
                    created_at=r.created_at,
                )
                for r in task.records
            ],
        )
    finally:
        db.close()


#======历史查询======
# 最近 N 条任务，按 task 聚合，每条任务带其 records
@app.get("/api/v1/history", response_model=HistoryResponse)
def get_history(limit: int = Query(10, ge=1, le=100)):
    db = SessionLocal()
    try:
        tasks = (
            db.query(EvaluationTask)
            .options(joinedload(EvaluationTask.records))
            .order_by(EvaluationTask.started_at.desc())
            .limit(limit)
            .all()
        )
        out = []
        for t in tasks:
            out.append(
                HistoryTaskItem(
                    task_id=t.task_id,
                    started_at=t.started_at,
                    status=t.status,
                    model_name=t.model_name,
                    total_duration_sec=t.total_duration_sec,
                    records=[
                        HistoryRecordItem(
                            question=r.question,
                            final_answer=r.final_answer,
                            evidence=r.evidence,
                            self_check=r.self_check,
                            created_at=r.created_at,
                        )
                        for r in t.records
                    ],
                )
            )
        return HistoryResponse(tasks=out)
    finally:
        db.close()
