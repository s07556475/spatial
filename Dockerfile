# Dockerfile 修正版 (请用此版本替换旧版本)
# 使用预装了 GeoSpatial 库的 Alpine Python 镜像
FROM python:3.11-alpine

# 安装必要的系统库和 GeoSpatial 依赖
# build-base 包含 gcc, g++, make 等构建工具
# gfortran, lapack-dev, openblas-dev 用于 numpy/scipy 的高性能计算
RUN apk update && \
    apk add --no-cache bash build-base gfortran lapack-dev openblas-dev && \
    # GeoSpatial 依赖
    apk add --no-cache geos-dev proj-dev gdal-dev

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装 Python 包
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 启动 Gunicorn (监听 Render 提供的 $PORT 环境变量)
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "app:app"]
