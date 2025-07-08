"""数据模型模块
定义文档结构、各种内容类型和统一的模型管理
"""

# 导出文档数据模型
from .document import (
    Document, PageLayout, Page, Region, TextRegion, TableRegion, FormulaRegion, ImageRegion,
    DocumentLayoutType, RegionType, DocumentType, BoundingBox, TextData, TableData, FormulaData, ImageData
)

# 导出主要接口
__all__ = [
    "Document",
    "PageLayout", 
    "Page",
    "Region",
    "TextRegion",
    "TableRegion", 
    "FormulaRegion",
    "ImageRegion",
    "DocumentLayoutType",
    "RegionType",
    "DocumentType",
    "BoundingBox",
    "TextData",
    "TableData",
    "FormulaData",
    "ImageData"
]