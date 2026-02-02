import os
import json
import time
import requests

#======配置区======
#POPE是一个COCO的子数据集，存储着对应COCO图片的题库，用于大模型幻觉测试
#这里用的国内镜像站
POPE_JSON_URL = "https://raw.githubusercontent.com/RUCAIBox/POPE/main/output/coco/coco_pope_random.json"

#COCO图片官方图床，分图片库与官方标注文件，每张图都会带一个数据标注
#比如"Image_001": ["person", "car", "dog"]  // 官方认证：这张图里有这些东西
COCO_IMAGE_BASE_URL = "http://images.cocodataset.org/val2014/"

#本地路径配置
# os.path.join 是为了自动适配 Windows(\) 和 Mac(/) 的路径分隔符
DATA_DIR = "data"
IMG_DIR = os.path.join(DATA_DIR,"images")       #存图
ANNO_DIR = os.path.join(DATA_DIR,"annotations")     #存标注

#汇总图片本地路径 + 问题 + 标准答案
#JSONL 的全称是 JSON Lines（按行分布的 JSON）。没有 [ 和 ]，没有行尾逗号。每一行都是一个独立的、合法的 JSON 对象。
OUTPUT_JSONL = os.path.join(ANNO_DIR,"mini_pope.jsonl")



#======工具函数区======
def ensure_dir(path):
    """
    创建文件夹，如果不存在的话。
    """
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory:{path}")

def download_file(url,save_path):
    """
    通用下载函数。
    相当于封装了一个简单的 HttpClient。
    """
    # 1. 断点续传简化版：如果文件有了，就不下了
    if os.path.exists(save_path):
        print(f"File allready exsists:{save_path}")
        return True
    
    try:
        # 2. 发起请求
        # stream=True 是关键！表示像水管一样一点点流数据，而不是把整个水库(文件)倒进内存
        response = requests.get(url,stream=True)
        # 检查 HTTP 状态码
        if response.status_code == 200:
            # 'wb' = Write Binary (二进制写入)，图片必须要用这个模式
            # with open(...) 是上下文管理器，打开文件，代码块结束自动关闭文件
            with open(save_path,'wb')as f:
                # 每次只下载 1KB (1024 字节)，避免内存溢出
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            print(f"Downloaded:{save_path}")
            return True
        else:
            print(f"Failed to download.Status code:{response.status_code}")
            return False
    except Exception as e:
        #捕获所有异常
        print(f"Error downloading {url}:{e}")
        return False
    
# ======主逻辑区======
def main():
    # 1. 准备目录
    # 调用工具函数，先把 data/images 和 data/annotations 建好
    ensure_dir(IMG_DIR)
    ensure_dir(ANNO_DIR)

    # 2. 下载 POPE 原始考卷 (JSON) (题库)
    raw_json_path = os.path.join(ANNO_DIR, "pope_raw.json")
    print(">>> Step 1: Downloading POPE metadata...")
    
    # 下载，若失败，报错
    if not download_file(POPE_JSON_URL, raw_json_path):
        print("Error: 无法下载 JSON，请检查网络")
        return

    # 3. 读取并解析 图片标注JSON (只取原始考卷的前 50 条)
    print(">>> Step 2: Parsing data...")
    try:
        with open(raw_json_path, 'r', encoding='utf-8') as f:
            # data_list = json.load(f)      //我以为pope官方数据集是一个大json对象，实际上它是以json为尾缀的jsonl，不能读一整个
            data_list = []
            for line in f:
                if line.strip(): # strip是清洗函数，去除首尾空格，防止读到空行报错
                    data_list.append(json.loads(line))
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return
    
    # [Python 特性] 切片操作:50
    # 只取前 50 个考题
    mini_data = data_list[:50]
    print(f"Loaded {len(mini_data)} items from POPE.")

    # 4. 循环下载每道题对应的图片
    print("\n>>> Step 3: Downloading images...")
    
    valid_items = [] # 用来存那些成功下载了图片的数据
    
    # [Python 特性] enumerate
    # 同时拿到 索引(i) 和 元素(item)，省得写 int i=0; i++
    for i, item in enumerate(mini_data):
        image_name = item['image'] # 读取标注json对象(考题)的图片名
        
        # 拼下载链接 (去 COCO 官网找图)
        img_url = COCO_IMAGE_BASE_URL + image_name
        # 拼本地保存路径
        save_path = os.path.join(IMG_DIR, image_name)
        
        print(f"[{i+1}/50] Processing: {image_name}")
        
        # 调用工具函数下载
        if download_file(img_url, save_path):
            # 关键点：把本地路径记录进考题，方便后面给大模型看
            item['local_path'] = save_path
            valid_items.append(item)
        
        # 礼貌性延时，防止请求太快被封 IP
        time.sleep(0.2)

    # 5. 生成最终的“50题试卷” (mini_pope.jsonl)
    print(f"\n>>> Step 4: Saving mini dataset to {OUTPUT_JSONL}...")
    with open(OUTPUT_JSONL, 'w', encoding='utf-8') as f:
        for item in valid_items:
            # json.dumps 把json标注转成字符串，所有行的字符串组成jsonl文件
            # ensure_ascii=False 保证如果有中文不乱码
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print("\n Data preparation complete!")
    print(f"Images: {IMG_DIR}")
    print(f"Annotations: {OUTPUT_JSONL}")

# [Python 特性] 程序入口保护
# 只有直接运行这个脚本时，才会执行 main()
# 相当于 Java 的 public static void main
if __name__ == "__main__":
    main()