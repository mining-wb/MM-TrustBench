import os
import sys
import json

# 保证从项目根 python src/main.py 或 src 下 python main.py 都能找到 wrapper
_src_dir = os.path.dirname(os.path.abspath(__file__))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)
from wrapper import ModelWrapper
from trust_pipeline import TrustPipeline

#======配置区======
# 本脚本在 src/ 下，用 __file__ 推到项目根，这样无论从哪执行路径都对
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_JSONL = os.path.join(_PROJECT_ROOT, "data", "annotations", "mini_pope.jsonl")
# 每跑完一题就追加写这里，断网重跑不会重做前面的
OUTPUT_JSONL = os.path.join(_PROJECT_ROOT, "data", "prediction_results.jsonl")
# jsonl 里只有 "image" 文件名、没有完整路径时，用这个目录拼
IMG_DIR = os.path.join(_PROJECT_ROOT, "data", "images")


#======主逻辑======
def load_items(path: str) -> list:
    """
    读 jsonl，每行一个 json，返回 list。
    """
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items


def load_done_keys(path: str) -> set:
    """
    读已有结果文件，把已做过的题目的 key 放进 set，用于断点续传。
    key 用 question_id，没有就用 (image, question) 的元组转 str。
    """
    if not os.path.exists(path):
        return set()
    done = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            k = row.get("question_id")
            if k is None:
                k = (row.get("image"), row.get("question") or row.get("text"))
            done.add(json.dumps(k, sort_keys=True, ensure_ascii=False))
    return done


def main() -> None:
    # 1. 加载 50 道题
    if not os.path.exists(INPUT_JSONL):
        print(f"Error: 找不到 {INPUT_JSONL}，请先运行 setup_data.py")
        return
    items = load_items(INPUT_JSONL)
    total = len(items)
    print(f"Loaded {total} items from {INPUT_JSONL}")

    # 2. 断点续传：已写进结果文件的题不再跑
    done_keys = load_done_keys(OUTPUT_JSONL)
    wrapper = ModelWrapper()
    pipeline = TrustPipeline(wrapper)

    # 3. 输出目录不存在时先建
    os.makedirs(os.path.dirname(OUTPUT_JSONL), exist_ok=True)
    # 4. 追加写入用 "a"；首次写时文件不存在也会自动创建
    with open(OUTPUT_JSONL, "a", encoding="utf-8") as out_f:
        for i, item in enumerate(items):
            # 本题唯一 key，和 load_done_keys 里一致
            k = item.get("question_id")
            if k is None:
                k = (item.get("image"), item.get("question") or item.get("text"))
            key_str = json.dumps(k, sort_keys=True, ensure_ascii=False)
            if key_str in done_keys:
                print(f"[{i+1}/{total}] skip (already done)")
                continue

            # 优先用 local_path（完整路径），没有则用 image 文件名 + IMG_DIR 拼
            image_path = item.get("local_path")
            if not image_path and item.get("image"):
                image_path = os.path.join(IMG_DIR, item["image"])
            question = item.get("question") or item.get("text", "")
            if not image_path or not os.path.exists(image_path):
                print(f"[{i+1}/{total}] skip: no image {image_path}")
                continue

            # 走证据+自检流水线
            print(f"[{i+1}/{total}] {image_path} | {question[:40]}...")
            result = pipeline.process(image_path, question)

            # 原题 + 原始回复 + 最终答案 + 证据/自检，写一行
            row = {
                **item,
                "model_answer": result["raw"],
                "final_answer": result["answer"],
                "evidence": result.get("evidence", ""),
                "self_check": result.get("self_check", ""),
            }
            out_f.write(json.dumps(row, ensure_ascii=False) + "\n")
            out_f.flush()
            done_keys.add(key_str)

    print(f"\nDone. Results: {OUTPUT_JSONL}")


if __name__ == "__main__":
    main()
