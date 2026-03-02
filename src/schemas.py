from datetime import datetime
from pydantic import BaseModel

#======请求体======
# 评测接口入参：问题必填，图片二选一（本地路径或 base64）
class EvaluateRequest(BaseModel):
    question: str
    image_path: str | None = None
    image_base64: str | None = None


#======响应体======
# 与 TrustPipeline.process() 返回对齐：最终答案、证据、自检
class EvaluateResponse(BaseModel):
    final_answer: str
    evidence: str
    self_check: str


#======历史记录单条======
class HistoryRecordItem(BaseModel):
    question: str
    final_answer: str
    evidence: str | None
    self_check: str | None
    created_at: datetime | None


class HistoryTaskItem(BaseModel):
    task_id: str
    started_at: datetime | None
    status: str
    model_name: str | None
    total_duration_sec: int | None
    records: list[HistoryRecordItem]


class HistoryResponse(BaseModel):
    tasks: list[HistoryTaskItem]


#======批量评测======
# 单条入参与 EvaluateRequest 一致，图片二选一
class BatchItemRequest(BaseModel):
    question: str
    image_path: str | None = None
    image_base64: str | None = None


class BatchEvaluateRequest(BaseModel):
    items: list[BatchItemRequest]


# 立即返回，供前端轮询
class BatchEvaluateResponse(BaseModel):
    task_id: str
    status: str  # processing


#======任务状态（轮询用）======
class TaskRecordItem(BaseModel):
    question: str
    final_answer: str
    evidence: str | None
    self_check: str | None
    created_at: datetime | None


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # processing | completed | failed
    started_at: datetime | None
    model_name: str | None
    total_duration_sec: int | None
    records: list[TaskRecordItem]
