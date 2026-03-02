import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


#======评测任务主表======
# 一次评测请求对应一条 Task；批量时一个 Task 下多条 Record
class EvaluationTask(Base):
    __tablename__ = "evaluation_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(36), unique=True, nullable=False)  # UUID，供前端轮询
    started_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(32), nullable=False)  # processing | completed | failed
    model_name = Column(String(128), nullable=True)
    total_duration_sec = Column(Integer, nullable=True)  # 秒，可选

    records = relationship("EvaluationRecord", back_populates="task")


#======评测记录从表======
class EvaluationRecord(Base):
    __tablename__ = "evaluation_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("evaluation_tasks.id"), nullable=True)  # 兼容旧数据
    question = Column(String(512), nullable=False)
    image_base64 = Column(Text, nullable=True)  # 存路径或 base64 简短标识
    final_answer = Column(String(32), nullable=False)
    evidence = Column(Text, nullable=True)
    self_check = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("EvaluationTask", back_populates="records")
