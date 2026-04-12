# 使用uv官方镜像作为基础（已预装Python 3.12和uv）
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# 设置工作目录
WORKDIR /workspace

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_NO_SYNC=1

# 安装项目依赖所需的系统工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    curl \
    wget \
    jq \
    tree \
    vim \
    net-tools \
    iputils-ping \
    traceroute \
    netcat-openbsd \
    procps \
    # Office文档处理依赖
    libreoffice \
    poppler-utils \
    fonts-dejavu \
    fonts-liberation \
    # 图形和字体依赖
    libgl1 \
    libglib2.0-0 \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件到容器
COPY . /workspace/

# 创建虚拟环境并使用uv安装项目依赖（基于uv.lock）
RUN uv venv /workspace/.venv
ENV PATH="/workspace/.venv/bin:$PATH"

# 同步所有依赖
RUN uv sync

# 先安装构建工具
RUN uv pip install setuptools wheel && uv pip install agentscope-runtime --upgrade && uv pip install agentscope --upgrade

# 新增一些依赖
RUN uv pip install --system \
    pypdf pypdf2 pdf2image pdfplumber python-docx python-pptx \
    openpyxl xlrd \
    PyMuPDF \
    camelot-py[ghostscript] \
    pdfminer.six \
    odfpy Pillow pillow \
    imageio \
    imageio-ffmpeg \
    reportlab \
    # 2. 核心数据科学与可视化
    pandas numpy scipy scikit-learn matplotlib seaborn \
    plotly dash \
    jupyter ipython dask numba sympy \
    bokeh holoviews panel \
    yfinance akshare statsmodels ta-lib quantlib-python
# 重命名rm命令，使其不可用
RUN mv /bin/rm /bin/rm.disabled

# 设置容器默认命令
CMD ["/bin/bash"]
