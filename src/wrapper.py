import os
import json
import requests
from dotenv import load_dotenv

# 从项目根目录的 .env 里读 API_KEY 和 API_URL
load_dotenv()

#======配置区======
# 请求超时秒数，不设的话服务端卡住会一直等
REQUEST_TIMEOUT = 30


#======模型调用层======
class ModelWrapper:
    """
    封装视觉模型的 HTTP 调用。
    读 .env 里的 Key 和 URL，用 requests.post 发请求，解析返回的 content。
    """

    def __init__(self) -> None:
        # 从环境变量拿 Key、接口地址、模型名
        self.api_key = os.getenv("API_KEY")
        self.api_url = os.getenv("API_URL")
        # 模型名放 .env，不写则用默认，换模型不用改代码
        self.model = os.getenv("MODEL", "deepseek-ai/DeepSeek-V3")
        # 没 Key 没法调，直接报错
        if not self.api_key:
            raise ValueError("未找到 API_KEY，请在 .env 中配置")

    def predict(self, image_path: str, question: str) -> str:
        """
        传入图片路径和问题，请求模型，返回模型回复的文本。
        请求失败或解析异常时返回 "Error"，不抛异常，避免整服务挂掉。
        """
        # 1. 请求头：json + Bearer 鉴权
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        # 2. 请求体：按文档把图片路径和问题塞进 user 消息
        user_content = f"图片路径：{image_path}\n问题：{question}"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": user_content},
            ],
            "stream": False,
        }

        try:
            # 3. 发 POST，必须带 timeout，否则服务端卡死会假死
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            # 4. 从返回 JSON 里抠出 content
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
        image_path="data/images/COCO_val2014_000000000042.jpg",
        question="这张图里有几个人？",
    )
    print(result)
