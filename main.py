# -*- coding: utf-8 -*-
"""
应用入口点
启动 src 包下的应用
"""
import sys
from pathlib import Path

# 添加 src 目录到 Python 路径（确保可以导入 src 下的模块）
src_path = Path(__file__).parent / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# 导入并启动应用
from src.app.app import app

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=3000, debug=False)
