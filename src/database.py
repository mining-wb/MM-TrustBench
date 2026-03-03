import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

#======配置区======
# 测试时用内存库，不落盘
if os.getenv("MM_TRUSTBENCH_TEST"):
    _engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
else:
    _here = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(_here)
    _db_path = os.path.join(_project_root, "data", "trustbench.db")
    os.makedirs(os.path.dirname(_db_path), exist_ok=True)
    _engine = create_engine(f"sqlite:///{_db_path}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
Base = declarative_base()


def get_engine():
    return _engine
