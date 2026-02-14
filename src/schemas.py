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
