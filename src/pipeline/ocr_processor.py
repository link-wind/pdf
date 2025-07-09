"""
OCR处理器

使用PaddleOCR进行光学字符识别
"""

import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging

try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR = None
    logging.warning("PaddleOCR not installed, OCR功能将不可用")

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    from ..models.document import Region, TextElement, BoundingBox
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    try:
        from src.models.document import Region, TextElement, BoundingBox
    except ImportError:
        # 创建简单的替代类
        from typing import NamedTuple
        
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
        
        class TextElement:
            def __init__(self, text: str, bbox: BoundingBox, confidence: float = 1.0):
                self.text = text
                self.bbox = bbox
                self.confidence = confidence
        
        class Region:
            def __init__(self, region_id: str = "", bbox: BoundingBox = None, **kwargs):
                self.region_id = region_id
                self.bbox = bbox or BoundingBox(0, 0, 0, 0)
                for k, v in kwargs.items():
                    setattr(self, k, v)


class OCRProcessor:
    """OCR处理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化OCR处理器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.engine = getattr(config, 'engine', 'paddleocr')
        self.language = getattr(config, 'language', 'ch')
        self.use_gpu = getattr(config, 'use_gpu', False)
        self.confidence_threshold = getattr(config, 'confidence_threshold', 0.9)
        self.det_db_thresh = getattr(config, 'det_db_thresh', 0.3)
        self.det_db_box_thresh = getattr(config, 'det_db_box_thresh', 0.6)
        
        # 初始化OCR引擎
        self.ocr_engine = None
        self._init_ocr_engine()
        
        logger.info("OCR处理器初始化完成")
    
    def _init_ocr_engine(self) -> None:
        """初始化OCR引擎"""
        try:
            if PaddleOCR is None:
                logger.error("PaddleOCR not available")
                return
            
            # 如果启用GPU，设置PaddlePaddle使用GPU
            if self.use_gpu:
                import os
                os.environ['CUDA_VISIBLE_DEVICES'] = '0'  # 使用第一块GPU
                logger.info("设置CUDA_VISIBLE_DEVICES=0")
                
                # 设置PaddlePaddle使用GPU
                try:
                    import paddle
                    if paddle.is_compiled_with_cuda():
                        paddle.set_device('gpu:0')
                        logger.info("PaddlePaddle设置为GPU模式")
                    else:
                        logger.warning("CUDA不可用，将使用CPU模式")
                        paddle.set_device('cpu')
                except Exception as e:
                    logger.warning(f"设置GPU模式失败: {e}，将使用CPU模式")
            else:
                # 显式设置为CPU模式
                try:
                    import paddle
                    paddle.set_device('cpu')
                    logger.info("PaddlePaddle设置为CPU模式")
                except Exception as e:
                    logger.warning(f"设置CPU模式失败: {e}")
            
            # 尝试多种初始化方式
            init_success = False
            
            # 方式1：使用最基本的参数
            try:
                self.ocr_engine = PaddleOCR(lang=self.language)
                init_success = True
                logger.info("使用基本参数初始化成功")
            except Exception as e:
                logger.warning(f"基本参数初始化失败: {e}")
            
            # 方式2：如果基本参数失败，尝试带角度分类
            if not init_success:
                try:
                    self.ocr_engine = PaddleOCR(use_angle_cls=True, lang=self.language)
                    init_success = True
                    logger.info("使用use_angle_cls参数初始化成功")
                except Exception as e:
                    logger.warning(f"use_angle_cls参数初始化失败: {e}")
            
            # 方式3：尝试新的参数名
            if not init_success:
                try:
                    self.ocr_engine = PaddleOCR(use_textline_orientation=True, lang=self.language)
                    init_success = True
                    logger.info("使用use_textline_orientation参数初始化成功")
                except Exception as e:
                    logger.warning(f"use_textline_orientation参数初始化失败: {e}")
            
            if not init_success:
                self.ocr_engine = None
                logger.error("所有初始化方式都失败")
                return
            
            # 检查实际使用的设备
            try:
                import paddle
                device = paddle.get_device()
                logger.info(f"PaddleOCR引擎已初始化: {self.language} (设备: {device})")
            except:
                logger.info(f"PaddleOCR引擎已初始化: {self.language}")
            
        except Exception as e:
            logger.error(f"OCR引擎初始化失败: {e}")
            self.ocr_engine = None
    
    def process_region(self, region: Region, image: np.ndarray) -> Dict[str, Any]:
        """处理单个区域的OCR识别
        
        Args:
            region: 要处理的区域
            image: 页面图像（PIL Image或numpy数组）
            
        Returns:
            Dict[str, Any]: OCR结果
        """
        if self.ocr_engine is None:
            logger.warning("OCR引擎未初始化")
            return {'content': '', 'text_blocks': []}
        
        try:
            # 如果是PIL Image，转换为numpy数组
            if hasattr(image, 'mode'):
                image = np.array(image)
            
            # 裁剪区域
            cropped_image = self._crop_region(image, region.bbox)
            
            # 进行OCR识别
            result = self.ocr_engine.ocr(cropped_image, cls=True)
            
            # 解析结果
            text_content, text_blocks = self._parse_ocr_result(result, region.bbox)
            
            return {
                'content': text_content,
                'text_blocks': text_blocks,
                'confidence': self._calculate_average_confidence(result)
            }
            
        except Exception as e:
            logger.error(f"OCR处理失败: {e}")
            return {'content': '', 'text_blocks': []}
    
    def _crop_region(self, image: np.ndarray, bbox: BoundingBox) -> np.ndarray:
        """裁剪图像区域
        
        Args:
            image: 原始图像
            bbox: 边界框
            
        Returns:
            np.ndarray: 裁剪后的图像
        """
        try:
            x1, y1, x2, y2 = bbox.x1, bbox.y1, bbox.x2, bbox.y2
            
            # 确保坐标在有效范围内
            h, w = image.shape[:2]
            x1 = max(0, min(x1, w-1))
            y1 = max(0, min(y1, h-1))
            x2 = max(x1+1, min(x2, w))
            y2 = max(y1+1, min(y2, h))
            
            return image[y1:y2, x1:x2]
            
        except Exception as e:
            logger.error(f"图像裁剪失败: {e}")
            return image
    
    def _parse_ocr_result(self, result: List, region_bbox: BoundingBox) -> Tuple[str, List[TextElement]]:
        """解析OCR结果
        
        Args:
            result: PaddleOCR结果
            region_bbox: 区域边界框
            
        Returns:
            Tuple[str, List[TextElement]]: 文本内容和文本块列表
        """
        text_lines = []
        text_blocks = []
        
        try:
            if result and result[0]:
                for line in result[0]:
                    if len(line) >= 2:
                        # 获取文本框坐标
                        box_coords = line[0]
                        text_info = line[1]
                        
                        if len(text_info) >= 2:
                            text = text_info[0]
                            confidence = text_info[1]
                            
                            # 过滤低置信度文本
                            if confidence >= self.confidence_threshold:
                                text_lines.append(text)
                                
                                # 创建文本元素
                                # 将相对坐标转换为绝对坐标
                                abs_coords = self._relative_to_absolute_coords(
                                    box_coords, region_bbox
                                )
                                
                                text_element = TextElement(
                                    text=text,
                                    bbox=BoundingBox(*abs_coords),
                                    confidence=confidence
                                )
                                text_blocks.append(text_element)
            
            # 合并文本行
            content = '\n'.join(text_lines)
            
            return content, text_blocks
            
        except Exception as e:
            logger.error(f"OCR结果解析失败: {e}")
            return '', []
    
    def _relative_to_absolute_coords(self, box_coords: List, region_bbox: BoundingBox) -> Tuple[int, int, int, int]:
        """将相对坐标转换为绝对坐标
        
        Args:
            box_coords: 相对于裁剪区域的坐标 - PaddleOCR返回四个点
            region_bbox: 区域边界框
            
        Returns:
            Tuple[int, int, int, int]: 绝对坐标 (x1, y1, x2, y2)
        """
        try:
            # PaddleOCR返回的是四个点的坐标
            xs = [point[0] for point in box_coords]
            ys = [point[1] for point in box_coords]
            
            rel_x1, rel_y1 = min(xs), min(ys)
            rel_x2, rel_y2 = max(xs), max(ys)
            
            # 转换为绝对坐标
            abs_x1 = int(region_bbox.x1 + rel_x1)
            abs_y1 = int(region_bbox.y1 + rel_y1)
            abs_x2 = int(region_bbox.x1 + rel_x2)
            abs_y2 = int(region_bbox.y1 + rel_y2)
            
            return abs_x1, abs_y1, abs_x2, abs_y2
            
        except Exception as e:
            logger.error(f"坐标转换失败: {e}")
            return region_bbox.x1, region_bbox.y1, region_bbox.x2, region_bbox.y2
    
    def _calculate_average_confidence(self, result: List) -> float:
        """计算平均置信度
        
        Args:
            result: OCR结果
            
        Returns:
            float: 平均置信度
        """
        try:
            confidences = []
            if result and result[0]:
                for line in result[0]:
                    if len(line) >= 2 and len(line[1]) >= 2:
                        confidence = line[1][1]
                        confidences.append(confidence)
            
            return sum(confidences) / len(confidences) if confidences else 0.0
            
        except Exception as e:
            logger.error(f"计算置信度失败: {e}")
            return 0.0
    
    def process_image(self, image_path: str) -> Dict[str, Any]:
        """处理整张图像的OCR识别
        
        Args:
            image_path: 图像路径
            
        Returns:
            Dict[str, Any]: OCR结果
        """
        if self.ocr_engine is None:
            logger.warning("OCR引擎未初始化")
            return {'content': '', 'text_blocks': []}
        
        try:
            # 读取图像
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"无法读取图像: {image_path}")
                return {'content': '', 'text_blocks': []}
            
            # 进行OCR识别
            result = self.ocr_engine.ocr(image, cls=True)
            
            # 解析结果
            text_content, text_blocks = self._parse_full_image_result(result)
            
            return {
                'content': text_content,
                'text_blocks': text_blocks,
                'confidence': self._calculate_average_confidence(result)
            }
            
        except Exception as e:
            logger.error(f"图像OCR处理失败: {e}")
            return {'content': '', 'text_blocks': []}
    
    def _parse_full_image_result(self, result: List) -> Tuple[str, List[TextElement]]:
        """解析完整图像的OCR结果
        
        Args:
            result: PaddleOCR结果
            
        Returns:
            Tuple[str, List[TextElement]]: 文本内容和文本块列表
        """
        text_lines = []
        text_blocks = []
        
        try:
            if result and result[0]:
                for line in result[0]:
                    if len(line) >= 2:
                        box_coords = line[0]
                        text_info = line[1]
                        
                        if len(text_info) >= 2:
                            text = text_info[0]
                            confidence = text_info[1]
                            
                            if confidence >= self.confidence_threshold:
                                text_lines.append(text)
                                
                                # 计算边界框
                                xs = [point[0] for point in box_coords]
                                ys = [point[1] for point in box_coords]
                                
                                bbox = BoundingBox(
                                    int(min(xs)), int(min(ys)),
                                    int(max(xs)), int(max(ys))
                                )
                                
                                text_element = TextElement(
                                    text=text,
                                    bbox=bbox,
                                    confidence=confidence
                                )
                                text_blocks.append(text_element)
            
            content = '\n'.join(text_lines)
            return content, text_blocks
            
        except Exception as e:
            logger.error(f"完整图像OCR结果解析失败: {e}")
            return '', []
    
    def get_engine_info(self) -> Dict[str, Any]:
        """获取OCR引擎信息
        
        Returns:
            Dict[str, Any]: 引擎信息
        """
        return {
            'engine': self.engine,
            'language': self.language,
            'use_gpu': self.use_gpu,
            'confidence_threshold': self.confidence_threshold,
            'det_db_thresh': self.det_db_thresh,
            'det_db_box_thresh': self.det_db_box_thresh,
            'engine_loaded': self.ocr_engine is not None
        }
