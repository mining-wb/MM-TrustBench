# 测试时用内存库，避免写真实 data/trustbench.db
import os
import sys
os.environ["MM_TRUSTBENCH_TEST"] = "1"
# 避免 ModelWrapper 因缺 API_KEY 在 import 时报错
os.environ.setdefault("API_KEY", "test_key")
# 保证从项目根跑 pytest 时能 import src
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)
