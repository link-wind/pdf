"""
阅读顺序分析器

分析文档的阅读顺序，重新排列区域顺序
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    from ..models.document import Document, Page, Region, RegionType
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    try:
        from src.models.document import Document, Page, Region, RegionType
    except ImportError:
        # 创建简单的替代类
        from typing import List, Any
        from enum import Enum
        
        class RegionType(Enum):
            TEXT = "Text"
            TITLE = "Title"
            LIST = "List"
            TABLE = "Table"
            FIGURE = "Figure"
            CAPTION = "Caption"
            FORMULA = "Formula"
            HEADER = "Header"
            FOOTER = "Footer"
        
        class Region:
            def __init__(self, **kwargs):
                self.region_type = kwargs.get('region_type', RegionType.TEXT)
                self.bbox = kwargs.get('bbox')
                self.metadata = kwargs.get('metadata')
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        class Page:
            def __init__(self, **kwargs):
                self.regions: List[Region] = kwargs.get('regions', [])
                self.height = kwargs.get('height', 1000)
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        class Document:
            def __init__(self, **kwargs):
                self.pages: List[Page] = kwargs.get('pages', [])
                for k, v in kwargs.items():
                    setattr(self, k, v)


@dataclass
class ReadingOrderNode:
    """阅读顺序节点"""
    region: Region
    order_index: int
    column_index: int = 0
    reading_score: float = 0.0


class ReadingOrderAnalyzer:
    """阅读顺序分析器"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化阅读顺序分析器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.algorithm = getattr(config, 'algorithm', 'layoutreader')
        self.confidence_threshold = getattr(config, 'confidence_threshold', 0.6)
        self.column_detection = getattr(config, 'column_detection', True)
        self.fallback_to_spatial = getattr(config, 'fallback_to_spatial', True)
        self.merge_threshold = getattr(config, 'merge_threshold', 0.3)
        self.enable_cross_page_analysis = getattr(config, 'enable_cross_page_analysis', False)
        
        # LayoutReader相关配置
        self.use_layoutreader = getattr(config, 'use_layoutreader', True)
        self.layout_reader_model_path = getattr(config, 'layout_reader_model_path', 'hantian/layoutreader')
        self.max_sequence_length = getattr(config, 'max_sequence_length', 1024)
        self.num_reading_labels = getattr(config, 'num_reading_labels', 10)
        
        # 深度学习相关配置
        self.use_deep_learning_for_columns = getattr(config, 'use_deep_learning_for_columns', True)
        self.use_layoutlmv3 = getattr(config, 'use_layoutlmv3', True)
        
        logger.info("阅读顺序分析器初始化完成")
    
    def analyze_reading_order(self, document: Document) -> None:
        """分析整个文档的阅读顺序
        
        Args:
            document: 文档对象，将直接修改其页面区域的顺序
        """
        try:
            logger.info("开始分析阅读顺序...")
            
            # 简化的处理逻辑：为每个页面的区域设置阅读顺序
            for page_num, page in enumerate(document.pages):
                try:
                    logger.debug(f"分析页面 {page_num + 1} 的阅读顺序")
                    
                    # 获取页面的所有区域
                    regions = []
                    if hasattr(page, 'regions') and page.regions:
                        regions = list(page.regions)
                    elif hasattr(page, 'all_regions') and page.all_regions:
                        regions = list(page.all_regions)
                    
                    if not regions:
                        logger.debug(f"页面 {page_num + 1} 没有区域")
                        continue
                    
                    # 按照从上到下、从左到右的顺序排序
                    def sort_key(region):
                        # 标题类型优先级更高
                        type_priority = 0 if hasattr(region, 'region_type') and region.region_type == RegionType.TITLE else 1
                        
                        # 页眉页脚特殊处理
                        if hasattr(region, 'region_type'):
                            if region.region_type == RegionType.HEADER:
                                type_priority = -1  # 最高优先级
                            elif region.region_type == RegionType.FOOTER:
                                type_priority = 2   # 最低优先级
                        
                        y1 = region.bbox.y1 if hasattr(region, 'bbox') else 0
                        x1 = region.bbox.x1 if hasattr(region, 'bbox') else 0
                        
                        return (type_priority, y1, x1)
                    
                    # 排序并设置阅读顺序
                    sorted_regions = sorted(regions, key=sort_key)
                    for i, region in enumerate(sorted_regions):
                        region.reading_order = i + 1
                    
                    # 尝试更新页面区域（但不强制，避免只读属性问题）
                    try:
                        # 检查是否是PageLayout对象（有分类列表）
                        if hasattr(page, 'text_regions') and hasattr(page, 'table_regions'):
                            # PageLayout对象，清理并重新分类
                            logger.debug(f"PageLayout对象，重新分类区域")
                            page.text_regions.clear()
                            page.table_regions.clear()
                            page.formula_regions.clear()
                            page.image_regions.clear()
                            
                            for region in sorted_regions:
                                page.add_region(region)
                        else:
                            # 尝试直接赋值（Page对象）
                            if hasattr(page, 'regions') and hasattr(page.regions, 'clear'):
                                page.regions.clear()
                                page.regions.extend(sorted_regions)
                            elif hasattr(page, 'regions') and not isinstance(page.regions, property):
                                page.regions = sorted_regions
                    except Exception as update_error:
                        logger.debug(f"更新页面区域失败，但区域顺序已设置: {update_error}")
                        # 即使更新失败，reading_order已经设置，不影响后续处理
                
                except Exception as page_error:
                    logger.warning(f"页面 {page_num + 1} 阅读顺序分析失败: {page_error}")
                    # 为该页面的区域设置默认顺序
                    try:
                        regions = []
                        if hasattr(page, 'regions') and page.regions:
                            regions = list(page.regions)
                        elif hasattr(page, 'all_regions') and page.all_regions:
                            regions = list(page.all_regions)
                        
                        for i, region in enumerate(regions):
                            region.reading_order = i + 1
                    except Exception as fallback_error:
                        logger.error(f"设置默认阅读顺序失败: {fallback_error}")
                    continue
            
            logger.info("阅读顺序分析完成")
            
        except Exception as e:
            logger.error(f"阅读顺序分析失败: {e}")
            # 设置默认的阅读顺序
            try:
                for page in document.pages:
                    regions = []
                    if hasattr(page, 'regions') and page.regions:
                        regions = list(page.regions)
                    elif hasattr(page, 'all_regions') and page.all_regions:
                        regions = list(page.all_regions)
                    
                    for i, region in enumerate(regions):
                        region.reading_order = i + 1
            except Exception as fallback_error:
                logger.error(f"设置默认阅读顺序也失败: {fallback_error}")
    
    def _analyze_page_reading_order(self, page: Page) -> None:
        """分析单页的阅读顺序
        
        Args:
            page: 页面对象
        """
        try:
            if not page.regions:
                return
            
            # 根据配置选择算法
            if self.algorithm == 'layoutreader' and self.use_layoutreader:
                ordered_regions = self._layoutreader_order(page.regions)
            elif self.algorithm == 'spatial':
                ordered_regions = self._spatial_order(page.regions)
            else:
                # 默认使用空间排序
                ordered_regions = self._spatial_order(page.regions)
            
            # 更新页面区域顺序
            page.regions = ordered_regions
            
        except Exception as e:
            logger.error(f"页面阅读顺序分析失败: {e}")
            # 降级到空间排序
            if self.fallback_to_spatial:
                page.regions = self._spatial_order(page.regions)
    
    def _layoutreader_order(self, regions: List[Region]) -> List[Region]:
        """使用LayoutReader进行阅读顺序分析
        
        Args:
            regions: 区域列表
            
        Returns:
            List[Region]: 重排序后的区域列表
        """
        try:
            # 这里应该调用LayoutReader模型
            # 由于模型可能很大，这里实现一个简化版本
            logger.debug("使用LayoutReader算法（简化版本）")
            
            # 首先进行列检测
            if self.column_detection:
                columns = self._detect_columns(regions)
                ordered_regions = []
                
                for column in columns:
                    # 对每列内的区域进行排序
                    column_regions = self._spatial_order(column)
                    ordered_regions.extend(column_regions)
                
                return ordered_regions
            else:
                return self._spatial_order(regions)
            
        except Exception as e:
            logger.error(f"LayoutReader排序失败: {e}")
            return self._spatial_order(regions)
    
    def _spatial_order(self, regions: List[Region]) -> List[Region]:
        """基于空间位置的阅读顺序排序
        
        Args:
            regions: 区域列表
            
        Returns:
            List[Region]: 重排序后的区域列表
        """
        try:
            # 按照从上到下、从左到右的顺序排序
            # 首先按y坐标排序，然后按x坐标排序
            
            # 对于标题类型的区域，给予更高的优先级
            def sort_key(region: Region) -> Tuple[int, int, int]:
                # 标题类型优先级更高
                type_priority = 0 if region.region_type == RegionType.TITLE else 1
                
                # 页眉页脚特殊处理
                if region.region_type == RegionType.HEADER:
                    type_priority = -1  # 最高优先级
                elif region.region_type == RegionType.FOOTER:
                    type_priority = 2   # 最低优先级
                
                return (type_priority, region.bbox.y1, region.bbox.x1)
            
            return sorted(regions, key=sort_key)
            
        except Exception as e:
            logger.error(f"空间排序失败: {e}")
            return regions
    
    def _detect_columns(self, regions: List[Region]) -> List[List[Region]]:
        """检测文档的列结构
        
        Args:
            regions: 区域列表
            
        Returns:
            List[List[Region]]: 按列分组的区域列表
        """
        try:
            if not regions:
                return []
            
            # 简单的列检测算法
            # 基于文本区域的x坐标聚类
            text_regions = [r for r in regions if r.region_type in [
                RegionType.TEXT, RegionType.TITLE, RegionType.LIST
            ]]
            
            if len(text_regions) < 2:
                return [regions]
            
            # 提取x坐标中心点
            x_centers = [r.bbox.center_x for r in text_regions]
            
            # 简单的聚类：按x坐标排序，找到较大的间隔
            sorted_indices = sorted(range(len(x_centers)), key=lambda i: x_centers[i])
            
            columns = []
            current_column = []
            
            for i, idx in enumerate(sorted_indices):
                if i == 0:
                    current_column.append(text_regions[idx])
                else:
                    prev_x = x_centers[sorted_indices[i-1]]
                    curr_x = x_centers[idx]
                    
                    # 如果x坐标差距较大，认为是新的列
                    if curr_x - prev_x > 100:  # 阈值可以调整
                        if current_column:
                            columns.append(current_column)
                        current_column = [text_regions[idx]]
                    else:
                        current_column.append(text_regions[idx])
            
            if current_column:
                columns.append(current_column)
            
            # 将非文本区域分配到最近的列
            for region in regions:
                if region not in text_regions:
                    # 找到最近的列
                    min_distance = float('inf')
                    best_column = 0
                    
                    for i, column in enumerate(columns):
                        if column:
                            # 计算到列中心的距离
                            column_center_x = sum(r.bbox.center_x for r in column) / len(column)
                            distance = abs(region.bbox.center_x - column_center_x)
                            
                            if distance < min_distance:
                                min_distance = distance
                                best_column = i
                    
                    if best_column < len(columns):
                        columns[best_column].append(region)
            
            # 如果只检测到一列，返回所有区域
            if len(columns) <= 1:
                return [regions]
            
            return columns
            
        except Exception as e:
            logger.error(f"列检测失败: {e}")
            return [regions]
    
    def _analyze_cross_page_order(self, document: Document) -> None:
        """分析跨页的阅读顺序
        
        Args:
            document: 文档对象
        """
        try:
            logger.debug("分析跨页阅读顺序")
            
            # 简单实现：检查页脚页眉的连续性
            for i in range(len(document.pages) - 1):
                current_page = document.pages[i]
                next_page = document.pages[i + 1]
                
                # 检查是否有跨页的表格或列表
                self._check_cross_page_elements(current_page, next_page)
            
        except Exception as e:
            logger.error(f"跨页分析失败: {e}")
    
    def _check_cross_page_elements(self, current_page: Page, next_page: Page) -> None:
        """检查跨页元素
        
        Args:
            current_page: 当前页面
            next_page: 下一页面
        """
        try:
            # 检查当前页面底部和下一页面顶部的元素
            current_bottom_regions = [
                r for r in current_page.regions 
                if r.bbox.y2 > current_page.height * 0.8  # 底部20%区域
            ]
            
            next_top_regions = [
                r for r in next_page.regions 
                if r.bbox.y1 < next_page.height * 0.2  # 顶部20%区域
            ]
            
            # 简单实现：为跨页元素添加标记
            for region in current_bottom_regions:
                if region.region_type in [RegionType.TABLE, RegionType.LIST]:
                    region.metadata = region.metadata or {}
                    region.metadata['possibly_continues'] = True
            
            for region in next_top_regions:
                if region.region_type in [RegionType.TABLE, RegionType.LIST]:
                    region.metadata = region.metadata or {}
                    region.metadata['possibly_continuation'] = True
                    
        except Exception as e:
            logger.error(f"跨页元素检查失败: {e}")
    
    def get_algorithm_info(self) -> Dict[str, Any]:
        """获取算法信息
        
        Returns:
            Dict[str, Any]: 算法信息
        """
        return {
            'algorithm': self.algorithm,
            'confidence_threshold': self.confidence_threshold,
            'column_detection': self.column_detection,
            'fallback_to_spatial': self.fallback_to_spatial,
            'merge_threshold': self.merge_threshold,
            'enable_cross_page_analysis': self.enable_cross_page_analysis,
            'use_layoutreader': self.use_layoutreader,
            'layout_reader_model_path': self.layout_reader_model_path,
            'max_sequence_length': self.max_sequence_length,
            'num_reading_labels': self.num_reading_labels,
            'use_deep_learning_for_columns': self.use_deep_learning_for_columns,
            'use_layoutlmv3': self.use_layoutlmv3
        }
