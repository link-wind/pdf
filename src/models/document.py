"""
文档数据模型
定义文档结构和各种内容类型
"""

from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from PIL import Image


class DocumentType(Enum):
    """文档类型枚举"""
    SCIENTIFIC = "scientific"  # 科技文献
    DEV_DOC = "dev_doc"       # 开发文档  
    GENERAL = "general"       # 通用文档


class RegionType(Enum):
    """区域类型枚举"""
    TEXT = "Text"
    TITLE = "Title"
    TABLE = "Table"
    FORMULA = "Formula"
    EQUATION = "Equation"
    IMAGE = "Image"
    FIGURE = "Figure"
    HEADER = "Header"
    FOOTER = "Footer"
    CAPTION = "Caption"
    TABLE_CAPTION = "Table caption"
    FIGURE_CAPTION = "Figure caption"
    FOOTNOTE = "Footnote"


class DocumentLayoutType(Enum):
    """文档版式类型"""
    SINGLE_COLUMN = "single_column"  # 单栏
    DOUBLE_COLUMN = "double_column"  # 双栏
    GENERAL = "general"              # 通用文档
    CAPTION = "Caption"
    FIGURE_CAPTION = "Figure caption"
    TABLE_CAPTION = "Table caption"
    REFERENCE = "Reference"
    LIST = "List"
    TOC = "Toc"
    
    # 教材场景特有类型
    CATALOGUE = "Catalogue"
    FOOTNOTE = "Footnote"
    CHAPTER_TITLE = "Chapter title"
    SUBSECTION_TITLE = "Subsection title"
    SECTION_TITLE = "Section title"
    SUBHEAD = "Subhead"
    PARAGRAPH = "Paragraph"
    UNORDERED_LIST = "Unordered list"
    ORDERED_LIST = "Ordered list"
    CODE = "Code"
    CODE_CAPTION = "Code caption"
    PAGE_NUMBER = "Page number"
    INDEX = "Index"
    HEADLINE = "Headline"
    OTHER_TITLE = "Other title"
    
    @property
    def value(self) -> str:
        """返回枚举值"""
        return self._value_


@dataclass
class BoundingBox:
    """边界框数据类"""
    x1: float
    y1: float
    x2: float
    y2: float
    
    @property
    def width(self) -> float:
        return self.x2 - self.x1
    
    @property
    def height(self) -> float:
        return self.y2 - self.y1
    
    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)
    
    @property
    def center_x(self) -> float:
        """边界框中心x坐标"""
        return (self.x1 + self.x2) / 2
    
    @property
    def center_y(self) -> float:
        """边界框中心y坐标"""
        return (self.y1 + self.y2) / 2
    
    @property
    def area(self) -> float:
        """边界框面积"""
        return self.width * self.height
    
    def to_tuple(self) -> Tuple[float, float, float, float]:
        return (self.x1, self.y1, self.x2, self.y2)


@dataclass
class TextData:
    """文本数据"""
    content: str
    confidence: float
    language: Optional[str] = None
    font_size: Optional[float] = None
    font_family: Optional[str] = None
    is_bold: bool = False
    is_italic: bool = False


@dataclass
class TableData:
    """表格数据"""
    headers: List[str]
    rows: List[List[str]]
    bbox: Tuple[float, float, float, float]
    confidence: float
    caption: Optional[str] = None
    
    @property
    def row_count(self) -> int:
        return len(self.rows)
    
    @property
    def col_count(self) -> int:
        return len(self.headers) if self.headers else 0


@dataclass
class FormulaData:
    """公式数据"""
    latex: str
    confidence: float
    rendered_image: Optional[Image.Image] = None
    mathml: Optional[str] = None
    
    
@dataclass
class ImageData:
    """图像数据"""
    image: Image.Image
    caption: Optional[str] = None
    image_type: Optional[str] = None  # chart, diagram, photo, etc.
    extracted_text: Optional[str] = None
    confidence: float = 1.0


@dataclass  
class Region:
    """基础区域类"""
    region_type: RegionType
    bbox: BoundingBox 
    confidence: float
    page_number: int = 0
    reading_order: int = 0
    content: str = ""
    image_path: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    

@dataclass
class TextRegion(Region):
    """文本区域"""
    text_content: List[TextData] = field(default_factory=list)
    
    def __post_init__(self):
        # 只有当region_type为None或未指定时，才设置为TEXT
        if not hasattr(self, 'region_type') or self.region_type is None:
            self.region_type = RegionType.TEXT


@dataclass
class TableRegion(Region):
    """表格区域"""
    table_content: Optional[List[TableData]] = None
    page_image: Optional[Image.Image] = None
    page_path: Optional[str] = None
    
    def __post_init__(self):
        self.region_type = RegionType.TABLE
        if self.table_content is None:
            self.table_content = []
    
    def __len__(self):
        """实现__len__方法，返回表格内容列表的长度"""
        if self.table_content is None:
            return 0
        return len(self.table_content)


@dataclass
class FormulaRegion(Region):
    """公式区域"""  
    formula_content: Optional[List[FormulaData]] = None
    page_image: Optional[Image.Image] = None
    page_path: Optional[str] = None
    
    def __post_init__(self):
        self.region_type = RegionType.FORMULA


@dataclass
class ImageRegion(Region):
    """图像区域"""
    image_content: Optional[List[ImageData]] = None
    
    def __post_init__(self):
        self.region_type = RegionType.IMAGE


@dataclass
class Page:
    """页面数据类"""
    page_number: int
    image_path: str
    regions: List[Region] = field(default_factory=list)
    width: Optional[float] = None
    height: Optional[float] = None
    
    def add_region(self, region: Region) -> None:
        """添加区域"""
        self.regions.append(region)
    
    @property
    def region_count(self) -> int:
        """区域数量"""
        return len(self.regions)


@dataclass
class PageLayout:
    """页面版式"""
    page_number: int
    width: float = 2550.0  # 默认A4纸宽度像素值
    height: float = 3300.0  # 默认A4纸高度像素值
    column_count: int = 1
    image_path: str = ""  # 添加image_path字段
    layout_type: DocumentLayoutType = DocumentLayoutType.GENERAL  # 版式类型
    text_regions: List[TextRegion] = None
    table_regions: List[TableRegion] = None
    formula_regions: List[FormulaRegion] = None
    image_regions: List[ImageRegion] = None
    
    def __post_init__(self):
        if self.text_regions is None:
            self.text_regions = []
        if self.table_regions is None:
            self.table_regions = []
        if self.formula_regions is None:
            self.formula_regions = []
        if self.image_regions is None:
            self.image_regions = []
    
    def add_region(self, region: 'Region') -> None:
        """添加区域到相应的列表中"""
        if isinstance(region, TextRegion):
            self.text_regions.append(region)
        elif isinstance(region, TableRegion):
            self.table_regions.append(region)
        elif isinstance(region, FormulaRegion):
            self.formula_regions.append(region)
        elif isinstance(region, ImageRegion):
            self.image_regions.append(region)
        else:
            # 默认添加到文本区域
            if hasattr(region, 'region_type'):
                if region.region_type == RegionType.TEXT:
                    self.text_regions.append(region)
                elif region.region_type == RegionType.TABLE:
                    self.table_regions.append(region)
                elif region.region_type == RegionType.FORMULA:
                    self.formula_regions.append(region)
                elif region.region_type == RegionType.IMAGE:
                    self.image_regions.append(region)
                else:
                    self.text_regions.append(region)
    
    @property
    def all_regions(self) -> List['Region']:
        """获取所有区域"""
        regions = []
        regions.extend(self.text_regions)
        regions.extend(self.table_regions)
        regions.extend(self.formula_regions)
        regions.extend(self.image_regions)
        
        # 安全的排序，避免reading_order相同时的问题
        try:
            return sorted(regions, key=lambda r: (getattr(r, 'reading_order', 0), r.bbox.y1, r.bbox.x1))
        except Exception:
            # 如果排序失败，直接返回未排序的列表
            return regions
    
    @property
    def regions(self) -> List['Region']:
        """获取所有区域的别名，与all_regions相同"""
        return self.all_regions


@dataclass
class Document:
    """文档对象"""
    source_path: Optional[Path] = None
    doc_type: Optional[DocumentType] = None
    pages: List[Page] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time: Optional[float] = None
    markdown_content: Optional[str] = None
    
    @property
    def page_count(self) -> int:
        return len(self.pages)
    
    @property
    def total_regions(self) -> int:
        return sum(len(page.regions) for page in self.pages)
    
    def get_regions_by_type(self, region_type: RegionType) -> List[Region]:
        """按类型获取所有区域"""
        regions = []
        for page in self.pages:
            for region in page.regions:
                if region.region_type == region_type:
                    regions.append(region)
        return regions
    
    def get_page(self, page_number: int) -> Optional[Page]:
        """获取指定页面"""
        for page in self.pages:
            if page.page_number == page_number:
                return page
        return None
