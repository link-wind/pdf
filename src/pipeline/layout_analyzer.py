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

from ..models.document import Region, RegionType, BoundingBox, TableRegion, FormulaRegion, ImageRegion, TextRegion


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
            
            # 确定设备
            device = 'cuda' if self.use_gpu and torch.cuda.is_available() else 'cpu'
            
            # 加载模型并设置设备
            self.model = YOLOv10(str(model_path))
            
            # 如果有设备设置方法，尝试设置
            if hasattr(self.model, 'to'):
                self.model = self.model.to(device)
            
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
            
            # 解析结果并直接返回，不进行任何后处理
            regions = self._parse_results(results, image.shape)
            
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
                    try:
                        region_type = RegionType(label)
                    except ValueError:
                        logger.warning(f"未知的区域类型: {label}，将使用 PLAINTEXT")
                        region_type = RegionType.PLAINTEXT
                    
                    # 跳过需要舍弃的内容
                    if region_type is None:
                        logger.debug(f"跳过舍弃内容: {label}")
                        continue
                    
                    # 创建边界框并适当扩展区域
                    x1, y1, x2, y2 = map(int, box)
                    
                    # 计算扩展边距
                    region_width = x2 - x1
                    region_height = y2 - y1
                    
                    # 根据区域类型设置不同的扩展比例
                    if label == 'Title':
                        # 标题区域：适度扩展，特别是垂直方向
                        expand_x = max(25, int(region_width * 0.18))  # 水平扩展5%
                        expand_y = max(35, int(region_height * 0.30))  # 垂直扩展15%
                    elif label in ['IsolateFormula', 'FormulaCaption']:
                        # 公式区域：需要更多上下文
                        expand_x = max(5, int(region_width * 0.05))  # 水平扩展8%
                        expand_y = max(1, int(region_height * 0.02))  # 垂直扩展20%
                    elif label in ['Table', 'TableCaption', 'TableFootnote']:
                        # 表格区域：保守扩展
                        expand_x = max(5, int(region_width * 0.03))  # 水平扩展3%
                        expand_y = max(5, int(region_height * 0.02))  # 垂直扩展8%
                    elif label in ['Figure', 'FigureCaption']:
                        # 图片区域：轻微扩展
                        expand_x = max(4, int(region_width * 0.04))  # 水平扩展4%
                        expand_y = max(6, int(region_height * 0.10))  # 垂直扩展10%
                    else:
                        # 默认文本区域：平衡扩展
                        expand_x = max(1, int(region_width * 0.01))  # 水平扩展6%
                        expand_y = max(1, int(region_height * 0.01))  # 垂直扩展12%
                    
                    # 应用扩展并确保不超出图像边界
                    image_height, image_width = image_shape[:2]
                    x1_expanded = max(0, x1 - expand_x)
                    y1_expanded = max(0, y1 - expand_y)
                    x2_expanded = min(image_width, x2 + expand_x)
                    y2_expanded = min(image_height, y2 + expand_y)
                    
                    bbox = BoundingBox(x1_expanded, y1_expanded, x2_expanded, y2_expanded)
                    
                    logger.debug(f"区域扩展: {label} 原始({x1},{y1},{x2},{y2}) -> 扩展({x1_expanded},{y1_expanded},{x2_expanded},{y2_expanded})")
                    
                    # 根据区域类型决定是否创建占位符内容
                    content = ""
                    if region_type in [RegionType.FIGURE]:
                        # 图片区域不生成占位符内容
                        content = ""
                    elif region_type == RegionType.PLAINTEXT:
                        # 文本区域将通过OCR填充内容
                        content = ""
                    elif region_type == RegionType.TABLE:
                        # 表格区域将通过表格解析器填充内容
                        content = ""
                    elif region_type == RegionType.ISOLATE_FORMULA:
                        # 公式区域将通过公式解析器填充内容
                        content = ""
                    elif region_type == RegionType.TITLE:
                        # 标题区域将通过OCR填充内容
                        content = ""
                    else:
                        # 其他区域使用占位符
                        content = f"[{label}]"
                    
                    # 创建通用参数
                    common_params = {
                        'bbox': bbox,
                        'confidence': float(conf),
                        'page_number': 0,  # 将在后续设置
                        'reading_order': len(regions),
                        'content': content,
                        'metadata': {'original_label': label, 'class_id': class_id}
                    }
                    
                    # 根据区域类型创建相应的区域对象
                    if region_type == RegionType.TABLE:
                        # 创建表格区域
                        region = TableRegion(
                            region_type=region_type,
                            table_content=[],  # 初始化为空列表
                            **common_params
                        )
                    elif region_type == RegionType.ISOLATE_FORMULA:
                        # 创建公式区域
                        region = FormulaRegion(
                            region_type=region_type,
                            formula_content=[],  # 初始化为空列表
                            **common_params
                        )
                    elif region_type == RegionType.FIGURE:
                        # 创建图像区域
                        region = ImageRegion(
                            region_type=region_type,
                            image_content=[],  # 初始化为空列表
                            **common_params
                        )
                    elif region_type in [RegionType.PLAINTEXT, RegionType.TITLE, RegionType.FIGURE_CAPTION, RegionType.TABLE_CAPTION, RegionType.FORMULA_CAPTION]:
                        # 创建文本区域
                        region = TextRegion(
                            region_type=region_type,
                            text_content=[],  # 初始化为空列表
                            **common_params
                        )
                    else:
                        # 创建通用区域
                        region = Region(
                            region_type=region_type,
                            **common_params
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
