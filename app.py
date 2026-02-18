import base64
import requests
import streamlit as st

#======配置区======
# 后端 API 地址，本地跑 uvicorn 时用这个
API_EVALUATE_URL = "http://127.0.0.1:8000/api/v1/evaluate"

#======页面骨架======
st.set_page_config(page_title="MM-TrustBench", layout="wide")
st.title("MM-TrustBench：视觉大模型幻觉评测台")

uploaded_file = st.file_uploader("上传图片", type=["png", "jpg", "jpeg"])
question = st.text_input("输入问题", placeholder="例如：图里有几个人？")
run_btn = st.button("开始评测")

#======联调 + 展示======
if run_btn:
    if not uploaded_file or not question.strip():
        st.warning("请先上传图片并输入问题")
    else:
        # 图片转 base64
        img_bytes = uploaded_file.read()
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        payload = {"question": question.strip(), "image_base64": img_b64}

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
            if ans == "yes":
                st.success(f"最终答案：{ans}")
            elif ans == "no":
                st.info(f"最终答案：{ans}")
            else:
                st.error(f"最终答案：{ans}（拒答）")
            with st.expander("证据链 (Evidence)"):
                st.text(data.get("evidence", ""))
            with st.expander("自检过程 (Self-check)"):
                st.text(data.get("self_check", ""))
