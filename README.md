# RAG 知识库系统

基于 LangGraph 构建的企业级 RAG（检索增强生成）知识库系统，支持 PDF/Markdown 文档导入、向量检索、混合搜索和智能问答。

## 架构概览

```
┌──────────────────────────────────────────────────┐
│                    客户端                          │
│          import.html  │  chat.html                │
└─────────────┬────────┴──────┬───────────────────┘
              │               │
    ┌─────────▼─────┐  ┌──────▼──────────┐
    │ Import Service │  │ Query Service   │
    │   (port 8000)  │  │   (port 8001)   │
    └───────┬───────┘  └──────┬──────────┘
            │                 │
    ┌───────▼─────────────────▼───────┐
    │          LangGraph 引擎           │
    │  StateGraph + 条件边 + 节点编排    │
    └───────┬─────────────────┬───────┘
            │                 │
    ┌───────▼──────┐  ┌───────▼──────────────┐
    │ 导入流程 (7节点)│  │ 查询流程 (6节点)         │
    │ ① 入口校验     │  │ ① 意图识别&问题改写     │
    │ ② PDF→MD     │  │ ② 多路召回（并行）       │
    │ ③ 图片处理     │  │   · 向量检索             │
    │ ④ 文档切分     │  │   · HyDE 检索            │
    │ ⑤ 实体识别     │  │   · 联网搜索(MCP)         │
    │ ⑥ BGE向量化   │  │ ③ RRF 融合排序          │
    │ ⑦ Milvus入库  │  │ ④ BGE-Reranker 重排序   │
    └──────────────┘  │ ⑤ 答案生成&流式输出      │
                      └──────────────────────────┘
```

## 技术栈

| 组件 | 技术选型 |
|------|---------|
| Web 框架 | FastAPI + Uvicorn |
| 工作流引擎 | LangGraph（StateGraph，条件路由） |
| 向量数据库 | Milvus（稠密 HNSW + 稀疏倒排索引） |
| 嵌入模型 | BGE-M3（本地部署，稠密+稀疏双向量） |
| 重排序模型 | BGE-Reranker-Large（本地部署） |
| LLM | Qwen 系列（DashScope API） |
| 对话存储 | MongoDB |
| 文件存储 | MinIO（MD 图片上传 + 匿名读取） |
| 图数据库 | Neo4j（预留，客户端已就绪） |
| PDF 解析 | MinerU API |
| 流式输出 | SSE（Server-Sent Events） |
| 日志 | Loguru（控制台 + 文件双输出） |
| 模型下载 | ModelScope（离线模式可选） |

## 项目结构

```
rag_project/
├── app/
│   ├── clients/              # 外部服务客户端
│   │   ├── milvus_utils.py       # Milvus：混合搜索、批量查询
│   │   ├── minio_utils.py        # MinIO：文件上传、桶管理
│   │   ├── mongo_history_utils.py # MongoDB：对话历史CRUD
│   │   └── neo4j_utils.py        # Neo4j：图数据库连接
│   ├── conf/                 # 配置类（读取 .env）
│   │   ├── embedding_config.py   # BGE-M3 模型配置
│   │   ├── reranker_config.py    # BGE-Reranker 模型配置
│   │   ├── milvus_config.py      # Milvus 连接配置
│   │   ├── minio_config.py       # MinIO 连接配置
│   │   ├── lm_config.py          # LLM 配置
│   │   ├── mineru_config.py      # MinerU 配置
│   │   └── bailian_mcp_config.py # 百炼 MCP 配置
│   ├── core/                 # 核心工具
│   │   ├── logger.py             # Loguru 日志（自动轮转、清理）
│   │   └── load_prompt.py        # Prompt 模板加载
│   ├── import_process/       # 导入服务
│   │   ├── api/import_server.py  # FastAPI 应用（端口 8000）
│   │   ├── page/import.html      # 导入管理前端页面
│   │   └── agent/
│   │       ├── main_graph.py     # LangGraph 流程编排（7 节点）
│   │       ├── state.py          # 状态定义
│   │       └── nodes/            # 7 个处理节点
│   ├── query_process/        # 查询服务
│   │   ├── api/query_server.py   # FastAPI 应用（端口 8001）
│   │   ├── page/chat.html        # 对话前端页面
│   │   ├── sse/                  # SSE 流式组件
│   │   └── agent/
│   │       ├── main_graph.py     # LangGraph 流程编排（6 节点）
│   │       ├── state.py          # 状态定义
│   │       └── nodes/            # 6 个处理节点
│   ├── lm/                   # 语言模型工具
│   │   ├── embedding_utils.py    # BGE-M3 嵌入（单例、批量）
│   │   ├── reranker_utils.py     # BGE-Reranker 重排序
│   │   └── lm_utils.py           # LLM 调用工具
│   ├── utils/                # 通用工具
│   │   ├── path_util.py          # 项目根目录推导
│   │   ├── task_utils.py         # 任务状态管理
│   │   ├── sse_utils.py          # SSE 队列与推送
│   │   ├── rate_limit_utils.py   # 速率限制
│   │   └── format_utils.py       # 格式化输出
│   ├── tool/                 # 模型下载脚本
│   └── test/                 # 单元测试
├── prompts/                  # Prompt 模板文件
├── output/                   # 运行时输出目录（gitignore）
├── logs/                     # 日志目录（gitignore）
├── Dockerfile                # 应用容器镜像
├── docker-compose.yml        # 应用服务编排
├── .env.example              # 环境变量模板
├── pyproject.toml            # 项目依赖（uv）
└── main.py                   # 项目入口占位
```

## 快速开始

### 前置条件

项目依赖以下基础设施，需提前部署：

- **Milvus** — 向量数据库（推荐 v2.6+，需启用稀疏向量支持）
- **MongoDB** — 对话历史存储
- **MinIO** — Markdown 图片对象存储
- **Neo4j** — 知识图谱（可选，当前预留）
- **BGE-M3** 模型文件 — 嵌入模型
- **BGE-Reranker-Large** 模型文件 — 重排序模型
- **DashScope API Key** — LLM 推理（Qwen 系列）
- **MinerU API Token** — PDF 解析

> ⚠️ **重要：Milvus Standalone 自带 MinIO 端口冲突**
>
> Milvus Standalone 容器内置了一个 MinIO 实例（用于存储向量索引和日志），默认占用 **9000** 端口。如果你的环境中已有独立的 MinIO 服务，会导致端口冲突。两种解决方案：
>
> **方案一（推荐）：修改独立 MinIO 的端口**
>
> 在独立 MinIO 的部署配置中将端口改为其他值（如 `9001`），然后在 `.env` 中设置：
> ```
> MINIO_ENDPOINT=你的IP:9001
> ```
>
> **方案二：直接使用 Milvus 自带的 MinIO**
>
> Milvus 内置的 MinIO（端口 9000，认证信息在 Milvus 日志中或 `minioadmin:minioadmin`）完全可以替代独立 MinIO。部署完 Milvus Standalone 后，直接在 `.env` 中使用其地址：
> ```
> MINIO_ENDPOINT=你的IP:9000
> MINIO_ACCESS_KEY=minioadmin
> MINIO_SECRET_KEY=minioadmin
> ```

### 本地运行

```bash
# 1. 克隆项目
git clone <repo-url>
cd rag_project

# 2. 创建虚拟环境 & 安装依赖
uv sync

# 3. 复制 .env.example 并填入实际配置
cp .env.example .env
# 编辑 .env，填写各服务地址、密钥、模型路径

# 4. 下载模型（可选，也可让程序首次运行时自动下载）
python app/tool/download_bgem3.py
python app/tool/download_reranker.py

# 5. 启动导入服务（端口 8000）
uv run uvicorn app.import_process.api.import_server:app --host 0.0.0.0 --port 8000

# 6. 启动查询服务（端口 8001）
uv run uvicorn app.query_process.api.query_server:app --host 0.0.0.0 --port 8001
```

### Docker 部署

```bash
# 1. 准备 .env（从 .env.example 复制并填入实际值）
cp .env.example .env

# 2. 确保宿主机上已有模型文件，填入 .env 中的路径
BGE_M3_PATH=/path/to/your/models/bge-m3
BGE_RERANKER_LARGE=/path/to/your/models/bge-reranker-large

# 3. CPU 启动（默认）
docker compose up -d

# 4. GPU 启动
#    编辑 .env: BGE_DEVICE=cuda:0  BGE_FP16=1
#    取消 docker-compose.yml 中 deploy.resources 注释
docker compose build --build-arg USE_GPU=true
docker compose up -d
```

服务启动后：
- 导入管理页：`http://localhost:8000/import`
- 查询对话页：`http://localhost:8001/chat.html`
- API 文档：`http://localhost:8000/docs` | `http://localhost:8001/docs`

## API 接口

### Import Service (`:8000`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/import` | 导入管理页面 |
| POST | `/upload` | 上传文件（PDF/MD），异步触发导入流程 |
| GET | `/status/{task_id}` | 查询导入任务进度 |
| GET | `/health` | 健康检查 |

### Query Service (`:8001`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/chat.html` | 对话页面 |
| GET | `/health` | 健康检查 |
| POST | `/query` | 发起提问（支持同步/流式） |
| GET | `/stream/{session_id}` | SSE 流式接收答案 |
| GET | `/history/{session_id}` | 查询历史对话 |
| DELETE | `/history/{session_id}` | 清空历史对话 |

## 导入流程详解

```
PDF/MD 文件上传
    │
    ▼
① entry       — 文件格式校验，自动识别 PDF/MD
    │
    ▼
② pdf_to_md   — 调用 MinerU API 将 PDF 转 Markdown
    │
    ▼
③ md_img      — 提取 MD 中的图片 → 上传 MinIO → 替换为公网 URL
    │
    ▼
④ doc_split   — 智能切分（超长截断 + 短块合并），备份 chunks.json
    │
    ▼
⑤ item_name   — LLM 识别文档对应的产品/实体名称
    │
    ▼
⑥ bge_embed   — BGE-M3 生成稠密+稀疏向量（批量，商品名前置）
    │
    ▼
⑦ import_milvus — 建集合 → 删旧数据（幂等）→ 插入 Milvus
```

## 查询流程详解

```
用户提问
    │
    ▼
① item_name_confirm  — 提取产品名 + 改写问题 + 确认候选
    │   ├── 无法确认 → 提示用户补充信息
    │   └── 已确认 ↓
    │
    ▼ (三路并行)
②a search_embedding  — 稠密+稀疏混合检索（Milvus hybrid_search）
②b search_hyde      — HyDE 假设性答案 → 检索
②c web_search_mcp   — DashScope MCP 联网搜索
    │
    ▼
③ rrf               — RRF 倒数排名融合，合并三路结果
    │
    ▼
④ rerank            — BGE-Reranker-Large 精排，取 Top-K
    │
    ▼
⑤ answer_output     — 组装 Prompt → LLM 生成 → SSE 流式输出 + MongoDB 存储
```

## 环境变量

完整配置见 [`.env.example`](.env.example)，核心变量：

| 分类 | 变量 | 说明 |
|------|------|------|
| LLM | `OPENAI_API_KEY` | DashScope API Key |
| LLM | `OPENAI_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| LLM | `LLM_DEFAULT_MODEL` | 默认模型，如 `qwen-flash` |
| 模型 | `BGE_M3_PATH` | BGE-M3 模型本地路径 |
| 模型 | `BGE_RERANKER_LARGE` | BGE-Reranker 模型本地路径 |
| 设备 | `BGE_DEVICE` | `cpu`（默认）/ `cuda:0` |
| 设备 | `BGE_FP16` | 半精度开关，CPU 设为 `0` |
| Milvus | `MILVUS_URL` | Milvus 连接地址 |
| Milvus | `CHUNKS_COLLECTION` | 切片集合名（默认 `kb_chunks`） |
| MongoDB | `MONGO_URL` | MongoDB 连接串 |
| MinIO | `MINIO_ENDPOINT` | MinIO 地址（注意端口冲突） |
| MinerU | `MINERU_API_TOKEN` | PDF 解析 API Token |
| MinerU | `MINERU_BASE_URL` | `https://mineru.net/api/v4` |
| 日志 | `LOG_CONSOLE_LEVEL` | 控制台日志级别（默认 `INFO`） |
| 日志 | `LOG_FILE_RETENTION` | 日志保留天数（默认 `7 days`） |

## 模型下载

```bash
# BGE-M3（嵌入模型，~2.2GB）
python app/tool/download_bgem3.py

# BGE-Reranker-Large（重排序模型，~1.3GB）
python app/tool/download_reranker.py
```

模型默认下载到 ModelScope 缓存目录，也可通过 `.env` 指定：
```
BGE_M3_PATH=/data/models/bge-m3
BGE_RERANKER_LARGE=/data/models/bge-reranker-large
```

## Docker 镜像构建

```bash
# CPU（默认）
docker build -t rag-project .

# GPU
docker build --build-arg USE_GPU=true -t rag-project:gpu .
```

GPU 部署还需在 `docker-compose.yml` 中取消 `deploy.resources` 注释。
