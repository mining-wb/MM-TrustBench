from fastapi import FastAPI

from .schemas import EvaluateRequest, EvaluateResponse

#======应用入口======
app = FastAPI(title="MM-TrustBench API", version="0.1.0")


#======探针======
# 服务是否存活，运维/前端轮询用
@app.get("/ping")
def ping():
    return {"status": "ok"}


#======评测接口（占位）======
# 先返假数据，验证路由和请求体通不通，再接 Pipeline
@app.post("/api/v1/evaluate", response_model=EvaluateResponse)
def evaluate(request: EvaluateRequest):
    return EvaluateResponse(
        final_answer="yes",
        evidence="mock",
        self_check="mock",
    )
