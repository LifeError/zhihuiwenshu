# syntax=docker/dockerfile:1

# ============================================================
# 基础镜像
# 默认 CPU 运行，GPU 构建时加 --build-arg USE_GPU=true
# ============================================================
FROM python:3.12-slim

ARG USE_GPU=false

WORKDIR /app

# -------------------- 系统依赖 --------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# -------------------- 安装 uv --------------------
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# -------------------- 安装 Python 依赖 --------------------
# 先复制依赖文件，利用 Docker 缓存层
COPY pyproject.toml uv.lock ./

# CPU 默认：临时替换 PyTorch 索引为 CPU 源
# GPU 构建：--build-arg USE_GPU=true 即保留 CUDA 索引
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$USE_GPU" = "false" ]; then \
        sed -i 's|https://download.pytorch.org/whl/cu126|https://download.pytorch.org/whl/cpu|g' pyproject.toml; \
    fi && \
    uv sync --frozen --no-dev

# -------------------- 复制应用代码 --------------------
COPY . .

# -------------------- 运行时配置 --------------------
# CPU 默认值（GPU 部署时通过 docker-compose 覆盖）
ENV BGE_DEVICE=cpu
ENV BGE_RERANKER_DEVICE=cpu
ENV BGE_FP16=0
ENV BGE_RERANKER_FP16=0

# 模型目录挂载点
ENV BGE_M3_PATH=/models/bge-m3
ENV BGE_RERANKER_LARGE=/models/bge-reranker-large

# 让 uv 管理的 venv 在 PATH 中
ENV PATH="/app/.venv/bin:$PATH"

# 暴露端口
EXPOSE 8000 8001

# 默认启动命令（可在 docker-compose 中覆盖）
CMD ["uv", "run", "uvicorn", "app.query_process.api.query_server:app", "--host", "0.0.0.0", "--port", "8001"]
