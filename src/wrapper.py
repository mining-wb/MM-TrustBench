import os
import base64
import requests
from dotenv import load_dotenv

# 从项目根目录的 .env 里读 API_KEY、API_URL、MODEL_NAME
load_dotenv()

#======配置区======
# 请求超时秒数，不设的话服务端卡住会一直等
REQUEST_TIMEOUT = 60
# 视觉接口里图片的 detail：low 省 token，high 更细
IMAGE_DETAIL = "low"


#======模型调用层======
class ModelWrapper:
    """
    封装视觉模型的 HTTP 调用。
    读 .env 里的 Key 和 URL，用 requests.post 发请求；图片读本地文件转 base64 塞进消息。
    """

    def __init__(self) -> None:
        # 从环境变量拿 Key、接口地址、模型名（.env 里是 MODEL_NAME）
        self.api_key = os.getenv("API_KEY")
        self.api_url = os.getenv("API_URL")
        self.model = os.getenv("MODEL_NAME", "Pro/Qwen/Qwen2.5-VL-7B-Instruct")
        # 没 Key 没法调，直接报错
        if not self.api_key:
            raise ValueError("未找到 API_KEY，请在 .env 中配置")

    def predict(self, image_path: str, question: str) -> str:
        """
        传入图片路径和问题，请求视觉模型，返回模型回复的文本。
        图片会按 base64 塞进 content，符合硅基流动视觉接口格式。
        请求失败或解析异常时返回 "Error"，不抛异常，避免整服务挂掉。
        """
        # 1. 读本地图片，转 base64，拼成 data:image/xxx;base64,xxx
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
        # 按后缀猜 mime，常见 jpg/png
        ext = os.path.splitext(image_path)[1].lower()
        mime = "image/png" if ext == ".png" else "image/jpeg"
        image_url = f"data:{mime};base64,{img_b64}"

        # 2. 请求头：json + Bearer 鉴权
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        # 3. 请求体：视觉接口要求 content 为数组，先图后文
        user_content = [
            {"type": "image_url", "image_url": {"url": image_url, "detail": IMAGE_DETAIL}},
            {"type": "text", "text": question},
        ]
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": user_content},
            ],
            "stream": False,
        }

        try:
            # 4. 发 POST，必须带 timeout，否则服务端卡死会假死
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            # 5. 从返回 JSON 里抠出 content
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return content
        except Exception as e:
            # 401/429/超时/解析错等，打日志，返回固定字符串，不崩进程
            print(f"Error calling model API: {e}")
            return "Error"


#======自测======
# 只有直接运行本文件时才跑，避免被 import 时执行
if __name__ == "__main__":
    wrapper = ModelWrapper()
    # 假路径和测试问题，验证接口能通
    result = wrapper.predict(
        image_path="data\images\COCO_val2014_000000210789.jpg",
        question="这张图里有几个人？",
    )
    print(result)
