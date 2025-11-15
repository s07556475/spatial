# Dockerfile 最终修正版：使用 Debian (slim) 基础镜像
# Debian 更适合科学计算库，能有效避免 Alpine 的兼容性问题
FROM python:3.11-slim-bookworm

# 安装必要的系统依赖和 GeoSpatial 依赖
# build-essential 相当于 build-base (提供 gcc, g++ 等)
# libgdal-dev, libgeos-dev, libproj-dev 是 GeoSpatial 依赖的开发包
# libatlas-base-dev 提供高性能线性代数库，帮助 NumPy 编译
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    libatlas-base-dev \
    # 清理APT缓存以减小镜像大小
    && rm -rf /var/lib/apt/lists/*

# 设置环境变量，确保 GeoPandas 的依赖 (Fiona/Rasterio) 能找到 GDAL
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装 Python 包
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 启动 Gunicorn (监听 Render 提供的 $PORT 环境变量)
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "app:app"]
