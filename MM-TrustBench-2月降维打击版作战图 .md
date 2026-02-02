# 🚀 MM-TrustBench：2月「降维打击」版作战图（后端工程化版）

> 本文档为**独立作战图**：目标锁定 **「Python 后端开发」**，把「大模型评测」作为业务背景，项目性质从 **「算法评测脚本」** 升级为 **「Web 后端服务系统」**。投递 **Python 后端工程师 / AI 应用开发 / 服务端开发** 时更有说服力。原完整学习计划已备份，可作后期扩展参考。

---

## 📌 战略目标

**用 3 周时间，从 Python 零基础做出一个带 RESTful API 与可视化界面的大模型评测**服务**，以此冲击 3 月份的 AI 应用/开发及 Python 后端实习岗位。**

- **找工作（3 月）：** 卖点是「能用 **FastAPI** 开发大模型评测**后端服务**，懂 RESTful API、数据校验、数据库与前后端分离」。
- **复试（12 月）：** 当前代码是骨架，后期填消融实验、对抗攻击即可成论文。

---

## 🔄 核心调整逻辑：从「写脚本」到「写服务」

| 原计划 | 新计划 |
|--------|--------|
| 写一个 Python 脚本 (`.py`)，终端打印结果或用 Streamlit 直接渲染 | 开发一个 **RESTful API 服务** |
| 更像数据分析师的工作 | **后端**：**FastAPI** 封装接口，处理 HTTP 请求、数据校验、异步并发 |
| 数据存 JSON 文件 | **数据库**：**SQLite** 存储评测历史和结果，展示 CRUD（增删改查） |
| Streamlit 直接 import 业务代码 | **前端**：Streamlit 作为「客户端」**调用你的后端 API** |

**结果：** 证明你懂 **前后端分离**、**API 设计**、**数据库交互** —— 这就是标准的后端开发能力。

---

## 🛠️ 1. 技术栈清单（后端开发特供）

| 类别 | 选择 | **求职含金量 (Backend)** |
|------|------|---------------------------|
| **Web 框架** | **FastAPI**（必学） | 取代简单脚本；Python 后端最火框架，高性能与异步 |
| **数据校验** | **Pydantic** | 定义请求/响应 Schema，保证数据安全，后端核心技能 |
| **数据库** | **SQLite** + **SQLModel**（或 SQLAlchemy） | 证明懂数据库设计与 ORM，而不只是读写文件 |
| **编程语言** | Python 3.10 + **Async/Await** | 展示异步协程（高并发基础），C++/Java 转 Python 的优势点 |
| **前端展示** | **Streamlit** | 保留，但角色变为「调用 API 的客户端」 |
| **模型调用** | API（DeepSeek / OpenAI / Gemini） | 业务侧：不本地部署，HTTP 调用即可 |

**环境建议：** VS Code + Python 3.10 + Anaconda（或 venv），虚拟环境内装包，避免和系统 Python 冲突。

---

## 📅 2. 周计划进度表（后端侧重版）

### 第一周（2.2 - 2.9）：Python 基础与业务逻辑（MVP）

**目标：** 克服语法障碍，完成核心**业务逻辑**（即「评测」功能）。这是后端要封装的业务内核。

**关键动作：**

1. **安装环境**
   - 安装 VS Code、Python 3.10、Anaconda（或 `python -m venv venv`）。
   - 新建项目目录，例如：
     ```
     MM-TrustBench/
       data/
         images/          # 放测试图
         annotations/     # 放 qa.jsonl
       src/
         wrapper.py       # 模型调用
         trust_pipeline.py # 证据+自检（业务内核）
       main.py            # 本地入口，跑通业务
       requirements.txt
     ```

2. **数据准备（不自己做标注）**
   - 去 HuggingFace 下载 **POPE** 验证集，只取 **50 条** 数据。
   - 写脚本用 `with open(..., encoding='utf-8')` 读 JSON/JSONL，打印前 3 条。

3. **申请 API Key**
   - DeepSeek 或 OpenAI 或 Gemini，任选其一，拿到 Key。

4. **实现 `wrapper.py` 与 `trust_pipeline.py`**
   - **类** `ModelWrapper`：`predict(image_path: str, question: str) -> str`，内部 `requests.post` 调 API。
   - **类** `TrustPipeline`：构造「证据+自检」格式的 prompt → 调 wrapper → 正则解析 Answer/Evidence/Self-check → 若 Unsupported 则拒答。
   - **新增重点（后端规范）：** 必须用 **Class** 封装，不要写成一坨流水账；严格使用 **Type Hints**（如 `def process(items: List[dict]) -> dict:`）。

**里程碑：**  
✅ 在本地通过 `python main.py` **跑通评测逻辑**（传一张图+一个问题，终端能打印出：原始回答 / 证据 / 自检结果 / 最终答案或拒答）。

**最小交付物：**
- ✅ `src/wrapper.py`、`src/trust_pipeline.py` 可运行
- ✅ `data/annotations/` 下有 50 条 JSONL
- ✅ `requirements.txt` 含 `requests` 等

---

### 第二周（2.10 - 2.16）：FastAPI 服务化（重中之重）

**目标：** **把脚本升级为 Web 服务**。这是转型后端开发的关键一周。

**关键动作：**

1. **引入 FastAPI 与 Pydantic**
   ```python
   from fastapi import FastAPI
   from pydantic import BaseModel

   app = FastAPI()

   class EvalRequest(BaseModel):
       image_url: str   # 或 base64，按你设计
       question: str

   @app.post("/api/v1/evaluate")   # 定义 RESTful 接口
   async def evaluate(request: EvalRequest):
       # 调用第一周写的业务逻辑
       result = trust_pipeline.process(request.image_url, request.question)
       return {"status": "success", "data": result}
   ```

2. **学习 Swagger UI**
   - 启动服务后访问 **`/docs`**，FastAPI 自动生成 API 文档。
   - 在 Swagger 里发一条请求、拿到结果；**截图文档**，证明你懂 API 规范。

3. **异步调用（加分）**
   - 把耗时的 LLM 调用放到 `async def` 或线程池里，避免阻塞主线程；面试时可说「用 async 处理耗时请求」。

**里程碑：**  
✅ 启动服务后，能通过**网页版 Swagger 文档**发送请求并拿到评测结果。

**最小交付物：**
- ✅ `src/api.py` 或 `main.py` 提供 `POST /api/v1/evaluate`
- ✅ `requirements.txt` 含 `fastapi`、`uvicorn`、`pydantic`
- ✅ `/docs` 可访问并成功调通一次

---

### 第三周（2.17 - 2.23）：数据库与全栈联调

**目标：** 加入数据库，完成**前后端分离**架构。

**关键动作：**

1. **数据库设计（SQLite）**
   - 设计一张表 **`EvaluationHistory`**，字段示例：`id`, `time`, `question`, `answer`, `evidence`, `is_refused`。
   - 使用 **SQLModel** 或 **SQLAlchemy** 定义模型，建表。

2. **持久化**
   - 每次在 `/api/v1/evaluate` 评测完成后，把结果**写入数据库**（INSERT）。
   - 可选：再提供一个 `GET /api/v1/history` 查询最近 N 条记录。这是后端最基本的 **CRUD** 能力。

3. **前端改写（Streamlit 作为客户端）**
   - **不再**在 Streamlit 里 `import trust_pipeline` 直接调逻辑。
   - 改为用 **`requests.post("http://localhost:8000/api/v1/evaluate", json=...)`** 调用你的 FastAPI 后端。
   - 界面：左侧上传图+输入问题，右侧展示 API 返回的结果（原始回答 / 证据 / 自检 / 最终答案）。

4. **注入演示（加分项）**
   - 找 5 张带恶意指令的图，在界面上展示系统能防御住；面试时说「做了 Prompt 注入防御演示」。

**里程碑：**  
✅ 一个完整的**迷你全栈系统**：请求进 API → 业务逻辑 → 结果入库 → 接口返回；Streamlit 仅负责调用 API 与展示。

**最小交付物：**
- ✅ SQLite 表存在，评测结果能写入并可查
- ✅ Streamlit 通过 HTTP 调后端，不直接 import 业务代码
- ✅ 至少 5 个注入案例能演示防御

---

### 第四周（2.24 - 2.28）：工程化包装与简历

**目标：** 像成熟的后端项目一样发布。

**关键动作：**

1. **README 升级**
   - 必须画出**架构图**：**Client（Streamlit）→ API（FastAPI）→ Service（trust_pipeline）→ Database（SQLite）**。
   - 写清：如何启动后端（如 `uvicorn src.api:app`）、如何启动前端（`streamlit run app.py`）、如何配置 API Key。

2. **简历关键词替换**
   - **原：** Python 脚本、数据处理。
   - **新：** **RESTful API 设计**、**FastAPI 框架**、**Pydantic 数据校验**、**ORM（SQLAlchemy/SQLModel）**、**异步编程（Asyncio）**、**前后端分离架构**、**SQLite 持久化**。

3. **投递**
   - 重点投：**Python 后端工程师**、**AI 应用开发**、**服务端开发**、Shopee、华为等。
   - 面试时强调：**Web 后端服务**、**API 设计**、**数据库 CRUD**、**前后端分离**。

**里程碑：**  
✅ 简历已更新并投出；README 与架构图可随时发给面试官；仓库置顶 MM-TrustBench。

---

## 💡 3. 给你的 3 个「锦囊」（遇到困难看这里）

1. **别造轮子**  
   数据不要自己标，去下载现成的 **POPE 验证集**；代码写不出来直接问 Cursor/ChatGPT：「用 Python 实现一个 HTTP POST 请求调用 DeepSeek 视觉接口」或「用 FastAPI 写一个 POST 接口接收 JSON」。

2. **别纠结语法**  
   Python 不用分号，用**缩进**。报错时 90% 是缩进不对或类型不匹配。装个 **Indent-rainbow** 插件；函数参数和返回值习惯性加上 **Type Hints**（`def f(data: dict) -> str`），方便排查。

3. **别追求完美**  
   **50 条数据够了，5 个注入案例够了。** 我们要的是 **「流程跑通」**，不是「发顶会论文」。先跑通后端 API + 数据库 + 前端调用，再优化。

---

## 📋 4. 自检清单（每周末勾一勾）

| 周 | 必达 | 可选 |
|----|------|------|
| 第一周 | [ ] 虚拟环境能激活；[ ] 能读 50 条 JSONL；[ ] `wrapper.py` + `trust_pipeline.py` 能跑通；[ ] 全程 Class + Type Hints | [ ] 写 `requirements.txt` |
| 第二周 | [ ] FastAPI 提供 `POST /api/v1/evaluate`；[ ] Pydantic 定义请求体；[ ] `/docs` 能发请求拿结果；[ ] 尝试 `async def` | [ ] 截图 Swagger 文档 |
| 第三周 | [ ] SQLite 表 `EvaluationHistory` 存在；[ ] 评测结果写入数据库；[ ] Streamlit 用 `requests.post` 调后端；[ ] 有 5 个注入演示 | [ ] `GET /api/v1/history` 查询历史 |
| 第四周 | [ ] README 含架构图（Client→API→Service→DB）；[ ] 简历关键词：RESTful API、FastAPI、ORM、Asyncio、前后端分离；[ ] 已投递目标公司 | [ ] 架构图 + Demo 动图 |

---

## 💬 5. 为什么这样改更适合找「Python 后端」？

1. **面试官问：** 「你做过 Web 开发吗？」
   - **原计划：** 「没，我写过脚本。」（减分）
   - **新计划：** 「做过。我用 **FastAPI** 开发过大模型评测服务的后端，设计了 RESTful 接口，用 **Pydantic** 做数据校验，并实现了评测结果的 **SQLite 持久化存储**。」（满分）

2. **面试官问：** 「你懂高并发吗？」
   - **原计划：** （沉默）
   - **新计划：** 「虽然项目流量不大，但我用了 Python 的 **async/await** 异步特性来处理耗时的 LLM API 请求，避免阻塞主线程。」（及格以上）

3. **面试官问：** 「你懂数据库吗？」
   - **原计划：** 「读写过 JSON 文件。」（像数据分析师）
   - **新计划：** 「我用了 **ORM**（SQLModel/SQLAlchemy）设计数据模型，实现了评测记录的增删改查。」（像后端工程师）

**总结：** 这套方案**工作量大约增加 20%**（主要是学 FastAPI 和 SQL），但**求职匹配度提升约 200%**。按这个走，你就是正儿八经的 **Python 后端实习生**。

---

## 🎯 6. 一句话定位（面试用）

- **项目是什么：** 一个面向视觉语言模型的**大模型评测 Web 后端服务**，提供 RESTful API，支持证据提取与自检机制降低幻觉，评测结果持久化到 SQLite，前端用 Streamlit 调用 API 做可视化。
- **你做了什么：** 用 **FastAPI** 开发后端、**Pydantic** 做数据校验、**SQLite + ORM** 做持久化、**Streamlit** 作为客户端调用 API，实现**前后端分离**的迷你全栈系统。
- **含金量在哪：** 展示的是 **Web 后端开发能力**（API 设计、数据校验、数据库 CRUD、异步处理）+ **业务理解**（大模型评测与可信输出），不是单纯写脚本。

---

*文档结束。按周执行，遇卡点先看锦囊。第一周先把环境装好，把 `wrapper.py` 和 `trust_pipeline.py` 跑通！*
