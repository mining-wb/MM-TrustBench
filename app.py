import os
import base64
import requests
import streamlit as st

#======配置区======
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")
API_EVALUATE_URL = f"{API_BASE}/api/v1/evaluate"
API_HISTORY_URL = f"{API_BASE}/api/v1/history"
API_MODELS_URL = f"{API_BASE}/api/v1/models"
API_BATCH_URL = f"{API_BASE}/api/v1/evaluate/batch"
API_TASK_URL = f"{API_BASE}/api/v1/task"

#======页面骨架======
st.set_page_config(page_title="MM-TrustBench", layout="wide")
st.title("MM-TrustBench：视觉大模型幻觉评测台")

# 可用模型下拉（多模型时用）
try:
    models_resp = requests.get(API_MODELS_URL, timeout=5)
    models_resp.raise_for_status()
    models_data = models_resp.json()
    models_list = models_data.get("models") or []
    model_options = [(m.get("id"), m.get("name") or m.get("id")) for m in models_list]
except Exception:
    model_options = [("default", "default")]
if not model_options:
    model_options = [("default", "default")]
current_model_id = st.selectbox(
    "选择模型",
    options=[x[0] for x in model_options],
    format_func=lambda x: next((n for i, n in model_options if i == x), x),
    key="model_select",
)

# 单条评测
uploaded_file = st.file_uploader("上传图片", type=["png", "jpg", "jpeg"])
question = st.text_input("输入问题", placeholder="例如：图里有几个人？")
answer_type = st.radio("答案类型", ["yes_no", "open"], format_func=lambda x: "仅 yes/no（幻觉评测）" if x == "yes_no" else "开放回答（数字或短句）", horizontal=True)
run_btn = st.button("开始评测")

#======联调 + 展示======
if run_btn:
    if not uploaded_file or not question.strip():
        st.warning("请先上传图片并输入问题")
    else:
        # 图片转 base64
        img_bytes = uploaded_file.read()
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        payload = {"question": question.strip(), "image_base64": img_b64, "answer_type": answer_type, "model_id": current_model_id}

        with st.spinner("评测中..."):
            try:
                resp = requests.post(API_EVALUATE_URL, json=payload, timeout=60)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                st.error(f"请求失败：{e}")
                st.stop()

        # 左右分栏：左图右结果
        col_left, col_right = st.columns(2)
        with col_left:
            uploaded_file.seek(0)
            st.image(uploaded_file, use_container_width=True)
        with col_right:
            ans = data.get("final_answer", "")
            if answer_type == "open":
                st.success(f"最终答案：{ans}")
            elif ans == "yes":
                st.success(f"最终答案：{ans}")
            elif ans == "no":
                st.info(f"最终答案：{ans}")
            else:
                st.error(f"最终答案：{ans}（拒答）")
            with st.expander("证据链 (Evidence)"):
                st.text(data.get("evidence", ""))
            with st.expander("自检过程 (Self-check)"):
                st.text(data.get("self_check", ""))

#======批量评测======
st.divider()
st.subheader("批量评测")
st.caption("多组「图片 + 问题」一并提交，后台异步执行；提交后得到任务 ID，可在此查看进度与结果。")
batch_n = st.number_input("题目数量", min_value=1, max_value=10, value=2, key="batch_n")
batch_items = []
for i in range(int(batch_n)):
    with st.container():
        c1, c2 = st.columns(2)
        with c1:
            f = st.file_uploader(f"图片 {i+1}", type=["png", "jpg", "jpeg"], key=f"batch_img_{i}")
        with c2:
            q = st.text_input(f"问题 {i+1}", key=f"batch_q_{i}")
        batch_items.append((f, q))
batch_answer_type = st.radio("答案类型", ["yes_no", "open"], format_func=lambda x: "仅 yes/no" if x == "yes_no" else "开放回答", key="batch_answer_type", horizontal=True)
batch_btn = st.button("开始批量评测")
if batch_btn:
    items_payload = []
    for f, q in batch_items:
        if not f or not (q or "").strip():
            st.warning("请为每题上传图片并填写问题")
            st.stop()
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
        items_payload.append({"question": q.strip(), "image_base64": img_b64})
    with st.spinner("提交中..."):
        try:
            r = requests.post(API_BATCH_URL, json={"items": items_payload, "model_id": current_model_id, "answer_type": batch_answer_type}, timeout=10)
            r.raise_for_status()
            data = r.json()
            task_id = data.get("task_id")
            st.session_state["last_batch_task_id"] = task_id
            st.success(f"已提交，任务 ID：`{task_id}`。请点击下方「查看任务结果」轮询进度。")
        except requests.RequestException as e:
            st.error(f"提交失败：{e}")

# 查看任务结果（轮询）
if "last_batch_task_id" in st.session_state:
    st.caption("查看刚提交的批量任务结果：")
    view_btn = st.button("查看任务结果")
    if view_btn:
        tid = st.session_state["last_batch_task_id"]
        try:
            tr = requests.get(f"{API_TASK_URL}/{tid}", timeout=10)
            tr.raise_for_status()
            task_data = tr.json()
            status = task_data.get("status", "")
            st.write(f"**状态**：{status}")
            if status == "completed":
                for rec in task_data.get("records") or []:
                    ans = rec.get("final_answer", "")
                    st.write(f"Q: {(rec.get('question') or '')[:80]}… → **{ans}**")
            elif status == "processing":
                st.info("仍在处理中，请稍后再点「查看任务结果」。")
        except requests.RequestException as e:
            st.warning(f"查询失败：{e}")

#======历史记录======
st.divider()
st.subheader("历史评测记录")
history_limit = st.selectbox("显示条数", [5, 10, 20, 50], index=1, key="history_limit")
if st.button("刷新历史"):
    st.rerun()
try:
    resp = requests.get(API_HISTORY_URL, params={"limit": history_limit}, timeout=10)
    resp.raise_for_status()
    history = resp.json()
    tasks = history.get("tasks") or []
    if not tasks:
        st.info("暂无历史记录，完成一次评测后会出现在这里。")
    else:
        for t in tasks:
            started = t.get("started_at") or ""
            if len(started) > 19:
                started = started[:19]
            with st.expander(f"任务 {t.get('task_id', '')[:8]}… | {t.get('status', '')} | {started}"):
                st.caption(f"状态: {t.get('status')} | 模型: {t.get('model_name') or '-'} | 耗时: {t.get('total_duration_sec') or '-'} 秒")
                for r in t.get("records") or []:
                    ans = r.get("final_answer", "")
                    q = (r.get("question") or "")[:60]
                    if len(r.get("question") or "") > 60:
                        q += "…"
                    if ans == "yes":
                        st.success(f"Q: {q} → {ans}")
                    elif ans == "no":
                        st.info(f"Q: {q} → {ans}")
                    elif ans == "refused":
                        st.error(f"Q: {q} → {ans}（拒答）")
                    else:
                        # 开放回答（数字或短句），直接展示答案
                        st.success(f"Q: {q} → {ans}")
                    ev = r.get("evidence") or ""
                    st.caption("证据: " + (ev[:200] + "…" if len(ev) > 200 else ev))
except requests.RequestException as e:
    st.warning(f"获取历史失败（请确认后端已启动）: {e}")
