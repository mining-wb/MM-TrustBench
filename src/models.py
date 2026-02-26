from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime

from .database import Base


#======评测记录表======
class EvaluationRecord(Base):
    __tablename__ = "evaluation_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(String(512), nullable=False)
    # 图片：可存 base64 或简短标识，看需求
    image_base64 = Column(Text, nullable=True)
    final_answer = Column(String(32), nullable=False)
    evidence = Column(Text, nullable=True)
    self_check = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
