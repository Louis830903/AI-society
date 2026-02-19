# AI Society 后端 Dockerfile
# ===========================
# 构建方式: docker build -t aisociety-backend .
# 运行方式: docker run -p 8000:8000 aisociety-backend

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Poetry
RUN pip install poetry

# 复制依赖文件
COPY pyproject.toml ./

# 配置 Poetry 不创建虚拟环境（容器内不需要）
RUN poetry config virtualenvs.create false

# 安装依赖
RUN poetry install --no-interaction --no-ansi --no-root

# 复制应用代码
COPY . .

# 安装应用
RUN poetry install --no-interaction --no-ansi

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
