#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF Pipeline 系统 - 核心模块

优化后的模块架构：
- 基于抽象基类的可扩展设计
- 组件化、可插拔的处理器架构  
- 统一的接口和错误处理
- 高度可复用的工具库
"""

from .config import Config, load_config
from .pipeline.pdf_pipeline import PDFPipeline
from .models import Document, Page, Region

# 版本信息
__version__ = "1.0.0"
__author__ = "PDF Pipeline Team"

# 导出主要接口
__all__ = [
    "__version__",
    "__author__",
    "Config",
    "load_config",
    "PDFPipeline",
    "Document",
    "Page", 
    "Region"
]
