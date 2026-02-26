import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

#======配置区======
# 库文件放 data/ 下，与项目根路径无关
_here = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_here)
_db_path = os.path.join(_project_root, "data", "trustbench.db")
os.makedirs(os.path.dirname(_db_path), exist_ok=True)

# connect_args 让 SQLite 支持多线程（FastAPI 多请求）
_engine = create_engine(f"sqlite:///{_db_path}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
Base = declarative_base()


def get_engine():
    return _engine
