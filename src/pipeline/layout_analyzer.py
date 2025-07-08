"""
DocLayout YOLO版式分析器
使用doclayout_yolo模型进行PDF文档版式分析和元素检测
"""

import cv2
import numpy as np
import torch
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path
from dataclasses import dataclass
import time

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    from doclayout_yolo import YOLOv10
except ImportError:
    logger.error("doclayout_yolo not installed. Please install: pip install doclayout_yolo")
    YOLOv10 = None

try:
    from ..models.document import Region, RegionType, BoundingBox
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    try:
        from src.models.document import Region, RegionType, BoundingBox
    except ImportError:
        # 如果还是失败，创建简单的替代类
        from typing import NamedTuple
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
        
        class BoundingBox(NamedTuple):
            x1: int
            y1: int
            x2: int
            y2: int
            
            @property
            def width(self):
                return self.x2 - self.x1
                
            @property
            def height(self):
                return self.y2 - self.y1
        
        class Region:
            def __init__(self, region_id: str, region_type: RegionType, bbox: BoundingBox, confidence: float = 1.0):
                self.region_id = region_id
                self.region_type = region_type
                self.bbox = bbox
                self.confidence = confidence


@dataclass
class LayoutElement:
    """版式元素类"""
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    label: str
    confidence: float
    region_type: RegionType


class LayoutAnalyzer:
    """DocLayout YOLO版式分析器"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化版式分析器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.model_path = getattr(config, 'model_path', 'doclayout.pt')
        self.model_type = getattr(config, 'model_type', 'doclayout')
        self.confidence_threshold = getattr(config, 'confidence_threshold', 0.4)
        self.iou_threshold = getattr(config, 'iou_threshold', 0.45)
        self.use_gpu = getattr(config, 'use_gpu', False)
        self.input_size = getattr(config, 'input_size', 1280)
        self.max_det = getattr(config, 'max_det', 300)
        
        # 后处理配置
        self.min_region_area = getattr(config, 'min_region_area', 50.0)
        self.merge_nearby_regions = getattr(config, 'merge_nearby_regions', True)
        self.sort_by_reading_order = getattr(config, 'sort_by_reading_order', True)
        
        # 初始化模型
        self.model = None
        self._init_model()
        
        # 类别映射 - 根据DocLayout YOLO模型的实际输出
        self.class_names = [
            'Title',        # 0: 标题
            'PlainText',    # 1: 普通文本
            'Abandon',      # 2: 页眉页脚等舍弃内容
            'Figure',       # 3: 图片
            'FigureCaption', # 4: 图片标题
            'Table',        # 5: 表格
            'TableCaption', # 6: 表格标题
            'TableFootnote', # 7: 表格脚注
            'IsolateFormula', # 8: 行间公式
            'FormulaCaption'  # 9: 公式标号
        ]
        
        logger.info("版式分析器初始化完成")
    
    def _init_model(self) -> None:
        """初始化YOLO模型"""
        try:
            if YOLOv10 is None:
                raise ImportError("doclayout_yolo not available")
            
            # 检查模型文件是否存在
            model_path = Path(self.model_path)
            if not model_path.exists():
                logger.warning(f"模型文件不存在: {self.model_path}")
                return
            
            # 加载模型
            device = 'cuda' if self.use_gpu and torch.cuda.is_available() else 'cpu'
            self.model = YOLOv10(str(model_path))
            
            logger.info(f"YOLO模型已加载: {self.model_path}")
            logger.info(f"使用设备: {device}")
            
        except Exception as e:
            logger.error(f"模型初始化失败: {e}")
            self.model = None
    
    def analyze_layout(self, image_input, page_num: int = 0) -> List[Region]:
        """分析页面版式
        
        Args:
            image_input: 图像文件路径(str)或PIL Image对象
            page_num: 页码
            
        Returns:
            List[Region]: 检测到的区域列表
        """
        if self.model is None:
            logger.warning("模型未初始化，返回空结果")
            return []
        
        try:
            # 读取图像
            if isinstance(image_input, str):
                # 从路径读取
                image = cv2.imread(image_input)
                if image is None:
                    logger.error(f"无法读取图像: {image_input}")
                    return []
            else:
                # PIL Image对象，转换为numpy数组
                import numpy as np
                image = np.array(image_input)
                # PIL Image是RGB格式，需要转换为BGR格式（OpenCV格式）
                if len(image.shape) == 3 and image.shape[2] == 3:
                    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            
            # 推理
            results = self.model(
                image,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                imgsz=self.input_size,
                max_det=self.max_det
            )
            
            # 解析结果
            regions = self._parse_results(results, image.shape)
            
            # 后处理
            regions = self._post_process_regions(regions)
            
            logger.debug(f"页面 {page_num} 检测到 {len(regions)} 个区域")
            return regions
            
        except Exception as e:
            logger.error(f"版式分析失败: {e}")
            return []
    
    def _parse_results(self, results, image_shape) -> List[Region]:
        """解析YOLO检测结果
        
        Args:
            results: YOLO检测结果
            image_shape: 图像形状 (H, W, C)
            
        Returns:
            List[Region]: 区域列表
        """
        regions = []
        
        try:
            # YOLO结果可能是列表格式，取第一个结果
            if isinstance(results, list) and len(results) > 0:
                result = results[0]
            else:
                result = results
            
            # 获取检测框
            if hasattr(result, 'boxes') and result.boxes is not None:
                boxes = result.boxes.xyxy.cpu().numpy()  # (x1, y1, x2, y2)
                confidences = result.boxes.conf.cpu().numpy()
                classes = result.boxes.cls.cpu().numpy()
                
                logger.debug(f"YOLO检测到 {len(boxes)} 个原始区域")
                
                for i, (box, conf, cls) in enumerate(zip(boxes, confidences, classes)):
                    # 获取类别名称
                    class_id = int(cls)
                    if class_id < len(self.class_names):
                        label = self.class_names[class_id]
                    else:
                        label = f"Unknown_{class_id}"
                    
                    logger.debug(f"检测到元素: {label} (置信度: {conf:.3f})")
                    
                    # 映射到RegionType
                    region_type = self._map_to_region_type(label)
                    
                    # 跳过需要舍弃的内容
                    if region_type is None:
                        logger.debug(f"跳过舍弃内容: {label}")
                        continue
                    
                    # 创建边界框
                    x1, y1, x2, y2 = map(int, box)
                    bbox = BoundingBox(x1, y1, x2, y2)
                    
                    # 创建区域
                    region = Region(
                        region_type=region_type,
                        bbox=bbox,
                        confidence=float(conf),
                        page_number=0,  # 将在后续设置
                        reading_order=len(regions),
                        content=f"[{label}]",  # 占位内容
                        metadata={'original_label': label, 'class_id': class_id}
                    )
                    
                    regions.append(region)
            else:
                logger.warning("YOLO结果中没有检测框信息")
            
            return regions
            
        except Exception as e:
            logger.error(f"解析检测结果失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _map_to_region_type(self, label: str) -> RegionType:
        """将类别标签映射到RegionType
        
        Args:
            label: 类别标签
            
        Returns:
            RegionType: 区域类型
        """
        mapping = {
            'Title': RegionType.TITLE,              # 0: 标题
            'PlainText': RegionType.TEXT,           # 1: 普通文本
            'Abandon': None,                        # 2: 页眉页脚等舍弃内容 - 跳过
            'Figure': None,                         # 3: 图片 - 跳过
            'FigureCaption': None,                  # 4: 图片标题 - 跳过
            'Table': RegionType.TABLE,              # 5: 表格
            'TableCaption': RegionType.TEXT,        # 6: 表格标题作为文本处理
            'TableFootnote': None,                  # 7: 表格脚注 - 跳过
            'IsolateFormula': RegionType.FORMULA,   # 8: 行间公式
            'FormulaCaption': None                  # 9: 公式标号 - 跳过
        }
        
        return mapping.get(label, RegionType.TEXT)
    
    def _post_process_regions(self, regions: List[Region]) -> List[Region]:
        """后处理检测区域
        
        Args:
            regions: 原始区域列表
            
        Returns:
            List[Region]: 处理后的区域列表
        """
        # 过滤小区域
        filtered_regions = []
        for region in regions:
            area = region.bbox.width * region.bbox.height
            if area >= self.min_region_area:
                filtered_regions.append(region)
        
        # 合并相邻区域（如果启用）
        if self.merge_nearby_regions:
            filtered_regions = self._merge_nearby_regions(filtered_regions)
        
        # 按阅读顺序排序（如果启用）
        if self.sort_by_reading_order:
            filtered_regions = self._sort_by_reading_order(filtered_regions)
        
        return filtered_regions
    
    def _merge_nearby_regions(self, regions: List[Region]) -> List[Region]:
        """合并相邻的同类型区域
        
        Args:
            regions: 区域列表
            
        Returns:
            List[Region]: 合并后的区域列表
        """
        # 简单实现：暂时不合并，直接返回
        return regions
    
    def _sort_by_reading_order(self, regions: List[Region]) -> List[Region]:
        """按阅读顺序排序区域
        
        Args:
            regions: 区域列表
            
        Returns:
            List[Region]: 排序后的区域列表
        """
        # 简单的从上到下、从左到右排序
        return sorted(regions, key=lambda r: (r.bbox.y1, r.bbox.x1))
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息
        
        Returns:
            Dict[str, Any]: 模型信息
        """
        return {
            'model_path': self.model_path,
            'model_type': self.model_type,
            'confidence_threshold': self.confidence_threshold,
            'iou_threshold': self.iou_threshold,
            'use_gpu': self.use_gpu,
            'input_size': self.input_size,
            'max_det': self.max_det,
            'model_loaded': self.model is not None,
            'class_names': self.class_names
        }
