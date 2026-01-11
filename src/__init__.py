# -*- coding: utf-8 -*-
"""
AShare-Sentinel - A股热度分析工具

一个用于分析A股市场短线热度的量化工具
"""

__version__ = "0.2.0"
__author__ = "AShare-Sentinel Team"

# 确保可以正确导入子模块
import sys
from pathlib import Path

# 将项目根目录添加到Python路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
