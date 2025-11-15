# 使用预装了 GeoSpatial 库的 Alpine Python 镜像
FROM python:3.11-alpine

# 安装必要的构建工具 (这是 Docker 内允许的，因为我们有 root 权限)
RUN apk update && \
    apk add --no-cache bash gcc musl-dev gfortran lapack-dev openblas-dev && \
    apk add --no-cache geos-dev proj-dev gdal-dev

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装 Python 包
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口 (Flask/Gunicorn 监听的端口)
EXPOSE 10000

# 启动 Gunicorn (这是最标准的启动命令)
# 注意：在 Docker 中，通常不需要复杂的路径，因为 gunicorn 在 PATH 中。
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
