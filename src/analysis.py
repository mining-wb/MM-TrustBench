import os
import re
import json
import sys

# 保证从项目根或 src 下执行都能找到模块
_src_dir = os.path.dirname(os.path.abspath(__file__))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

#======配置区======
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# main 输出的预测结果
PREDICTION_JSONL = os.path.join(_PROJECT_ROOT, "data", "prediction_results.jsonl")
# 阅卷明细写这里，方便开 Excel 或 jsonl 人肉挑错
ANALYSIS_JSONL = os.path.join(_PROJECT_ROOT, "data", "analysis_results.jsonl")


#======工具函数======
def load_jsonl(path: str) -> list:
    """
    读 jsonl，每行一个 json，返回 list。
    """
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def extract_yes_no(text: str) -> str:
    """
    把模型那一长串话洗成 yes 或 no。
    按首出现的 yes/no 词（不区分大小写）取；洗不出来算 unknown。
    """
    if not text or text.strip() == "Error":
        return "unknown"
    text_lower = text.strip().lower()
    # 先找 yes，再找 no，避免 "no" 出现在 "nothing" 里被误判
    if re.search(r"\byes\b", text_lower):
        return "yes"
    if re.search(r"\bno\b", text_lower):
        return "no"
    return "unknown"


def normalize_label(val: str) -> str:
    """
    标准答案字段可能是 answer 或 label，值统一成 yes/no。
    """
    if not val:
        return "unknown"
    v = val.strip().lower()
    if v in ("yes", "y"):
        return "yes"
    if v in ("no", "n"):
        return "no"
    return "unknown"


#======阅卷与指标======
def run_analysis() -> None:
    if not os.path.exists(PREDICTION_JSONL):
        print(f"Error: 找不到 {PREDICTION_JSONL}，请先跑 main.py 生成预测结果")
        return

    rows = load_jsonl(PREDICTION_JSONL)
    total = len(rows)
    if total == 0:
        print("Error: 预测结果为空")
        return

    # 标准答案字段：POPE 用 answer
    label_key = "answer" if "answer" in rows[0] else "label"

    correct = 0
    fp = 0  # 标准 no，模型 yes —— 幻觉
    fn = 0  # 标准 yes，模型 no —— 漏检
    label_no_count = 0  # 标准答案为 no 的题数，用于算幻觉率

    detail_rows = []

    for row in rows:
        gt_raw = row.get(label_key, "")
        gt = normalize_label(gt_raw)
        raw_answer = row.get("model_answer", "")
        pred = extract_yes_no(raw_answer)

        is_correct = (pred != "unknown" and pred == gt)
        if is_correct:
            correct += 1

        if gt == "no":
            label_no_count += 1
            if pred == "yes":
                fp += 1
        elif gt == "yes":
            if pred == "no":
                fn += 1

        # 明细行：原题 + 清洗结果 + 是否对、是否幻觉、是否漏检，方便人肉挑典型
        detail = {
            **row,
            "extracted_pred": pred,
            "correct": is_correct,
            "is_fp": (gt == "no" and pred == "yes"),
            "is_fn": (gt == "yes" and pred == "no"),
        }
        detail_rows.append(detail)

    # 指标
    accuracy = correct / total if total else 0
    hallucination_rate = fp / label_no_count if label_no_count else 0

    # 打印
    print("========== 阅卷结果 ==========")
    print(f"总题数: {total}")
    print(f"正确: {correct}  准确率 (Accuracy): {accuracy:.2%}")
    print(f"幻觉 (FP, 标准 no 却说 yes): {fp}  幻觉率: {hallucination_rate:.2%} (FP / 标准答案为 no 的题数)")
    print(f"漏检 (FN, 标准 yes 却说 no): {fn}")
    print("==============================")

    # 明细写 jsonl，方便开 Excel 或直接翻着找典型反例
    os.makedirs(os.path.dirname(ANALYSIS_JSONL), exist_ok=True)
    with open(ANALYSIS_JSONL, "w", encoding="utf-8") as f:
        for d in detail_rows:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"\n明细已写: {ANALYSIS_JSONL}（可据此人肉挑 3～5 个典型错例，记下图文件名）")

    # 可选：画图
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        _draw_charts(total, correct, fp, fn, label_no_count)
    except ImportError:
        pass

def _draw_charts(total: int, correct: int, fp: int, fn: int, label_no_count: int) -> None:

    """

    正确 vs 错误 柱状图；错例中 幻觉(FP) vs 漏检(FN) 饼图。图存 data 目录。

    """

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))



    # 正确 vs 错误

    wrong = total - correct

    ax1.bar(["正确", "错误"], [correct, wrong], color=["#2ecc71", "#e74c3c"])

    ax1.set_ylabel("题数")

    ax1.set_title("正确 vs 错误")



    # 错例中：幻觉(FP) vs 漏检(FN) 比例

    parts = [fp, fn]

    labels = ["幻觉 (FP)", "漏检 (FN)"]

    if fp + fn == 0:

        parts = [1]

        labels = ["无错例"]

    ax2.pie(parts, labels=labels, autopct="%1.0f%%", startangle=90)

    ax2.set_title("幻觉 vs 漏检 (错例)")



    out_path = os.path.join(_PROJECT_ROOT, "data", "analysis_charts.png")

    plt.tight_layout()

    plt.savefig(out_path, dpi=120)

    plt.close()

    print(f"图表已保存: {out_path}")

if __name__ == "__main__":
    run_analysis()
