from fastapi import FastAPI, HTTPException

from .schemas import EvaluateRequest, EvaluateResponse
from .wrapper import ModelWrapper
from .trust_pipeline import TrustPipeline

#======应用入口======
app = FastAPI(title="MM-TrustBench API", version="0.1.0")

# 引擎只实例化一次，复用
_wrapper = ModelWrapper()
_pipeline = TrustPipeline(_wrapper)


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
    try:
        result = _pipeline.process(
            image_path=request.image_path,
            question=request.question,
            image_base64=request.image_base64,
        )
        return EvaluateResponse(
            final_answer=result["answer"],
            evidence=result.get("evidence", ""),
            self_check=result.get("self_check", ""),
        )
    except Exception as e:
        print(f"Evaluate error: {e}")
        raise HTTPException(status_code=500, detail="模型调用失败")
