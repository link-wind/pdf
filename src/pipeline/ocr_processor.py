"""
OCR处理器 - 使用PaddleOCR进行光学字符识别
"""

import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

try:
    from paddleocr import PaddleOCR
    HAS_PADDLEOCR = True
except ImportError:
    PaddleOCR = None
    HAS_PADDLEOCR = False

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
        """初始化OCR处理器"""
        self.config = config
        self.language = getattr(config, 'language', 'ch')
        self.use_gpu = getattr(config, 'use_gpu', True)
        self.confidence_threshold = getattr(config, 'confidence_threshold', 0.8)
        self.det_db_thresh = getattr(config, 'det_db_thresh', 0.3)
        self.det_db_box_thresh = getattr(config, 'det_db_box_thresh', 0.6)
        self.ocr_version = getattr(config, 'ocr_version', 'PP-OCRv5')
        
        # 初始化OCR引擎
        self.ocr_engine = None
        self._init_ocr_engine()
    
    def _init_ocr_engine(self) -> None:
        """初始化OCR引擎"""
        try:
            if not HAS_PADDLEOCR:
                logger.error("PaddleOCR未安装，请使用pip install paddleocr")
                return
            
            # 使用最新的PaddleOCR配置参数
            self.ocr_engine = PaddleOCR(
                lang=self.language,
                det_db_thresh=self.det_db_thresh,
                det_db_box_thresh=self.det_db_box_thresh,
                ocr_version=self.ocr_version,
                device="gpu" if self.use_gpu else "cpu",
                use_doc_orientation_classify=False,  # 不使用文档方向分类模型
                use_doc_unwarping=False,  # 不使用文本图像矫正模型
                use_textline_orientation=False,  # 不使用文本行方向分类模型
            )
            
            logger.info(f"PaddleOCR引擎已初始化: 语言={self.language}, 版本={self.ocr_version}, 设备={'GPU' if self.use_gpu else 'CPU'}")
            
        except Exception as e:
            logger.error(f"OCR引擎初始化失败: {e}")
            self.ocr_engine = None
    
    def process_region(self, region: Region, image: np.ndarray) -> Dict[str, Any]:
        """处理单个区域的OCR识别"""
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
            result = self.ocr_engine.predict(cropped_image)
            
            # 解析结果
            text_content, text_blocks = self._parse_result(result, region.bbox)
            
            return {
                'content': text_content,
                'text_blocks': text_blocks,
                'confidence': self._calculate_confidence(result)
            }
            
        except Exception as e:
            logger.error(f"OCR处理失败: {e}")
            return {'content': '', 'text_blocks': []}
    
    def _crop_region(self, image: np.ndarray, bbox: BoundingBox) -> np.ndarray:
        """裁剪图像区域"""
        try:
            h, w = image.shape[:2]
            x1 = max(0, min(bbox.x1, w-1))
            y1 = max(0, min(bbox.y1, h-1))
            x2 = max(x1+1, min(bbox.x2, w))
            y2 = max(y1+1, min(bbox.y2, h))
            
            return image[y1:y2, x1:x2]
            
        except Exception as e:
            logger.error(f"图像裁剪失败: {e}")
            return image
    
    def _parse_result(self, result: List, region_bbox=None) -> Tuple[str, List[TextElement]]:
        """解析OCR结果"""
        text_lines = []
        text_blocks = []
        
        try:
            # 处理新版API结果格式
            if isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict):
                for item in result:
                    if 'rec_texts' in item and 'rec_scores' in item:
                        for i, (text, score, poly) in enumerate(zip(item['rec_texts'], 
                                                                   item['rec_scores'], 
                                                                   item['rec_polys'])):
                            if score >= self.confidence_threshold and text.strip():
                                text_lines.append(text)
                                
                                # 计算边界框
                                xs = [point[0] for point in poly]
                                ys = [point[1] for point in poly]
                                
                                # 转换坐标
                                if region_bbox:
                                    x1 = int(region_bbox.x1 + min(xs))
                                    y1 = int(region_bbox.y1 + min(ys))
                                    x2 = int(region_bbox.x1 + max(xs))
                                    y2 = int(region_bbox.y1 + max(ys))
                                else:
                                    x1 = int(min(xs))
                                    y1 = int(min(ys))
                                    x2 = int(max(xs))
                                    y2 = int(max(ys))
                                
                                text_blocks.append(TextElement(
                                    text=text,
                                    bbox=BoundingBox(x1, y1, x2, y2),
                                    confidence=float(score)
                                ))
            
            # 处理旧版API结果格式
            elif result and isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
                for line in result[0]:
                    if len(line) >= 2 and len(line[1]) >= 2:
                        box_coords = line[0]
                        text = line[1][0]
                        confidence = line[1][1]
                        
                        if confidence >= self.confidence_threshold and text.strip():
                            text_lines.append(text)
                            
                            # 计算边界框
                            xs = [point[0] for point in box_coords]
                            ys = [point[1] for point in box_coords]
                            
                            # 转换坐标
                            if region_bbox:
                                x1 = int(region_bbox.x1 + min(xs))
                                y1 = int(region_bbox.y1 + min(ys))
                                x2 = int(region_bbox.x1 + max(xs))
                                y2 = int(region_bbox.y1 + max(ys))
                            else:
                                x1 = int(min(xs))
                                y1 = int(min(ys))
                                x2 = int(max(xs))
                                y2 = int(max(ys))
                            
                            text_blocks.append(TextElement(
                                text=text,
                                bbox=BoundingBox(x1, y1, x2, y2),
                                confidence=confidence
                            ))
            
            content = '\n'.join(text_lines)
            return content, text_blocks
            
        except Exception as e:
            logger.error(f"OCR结果解析失败: {e}")
            return '', []
    
    def _calculate_confidence(self, result: List) -> float:
        """计算平均置信度"""
        try:
            confidences = []
            
            # 处理新版API结果
            if isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict):
                for item in result:
                    if 'rec_scores' in item:
                        confidences.extend([float(score) for score in item['rec_scores'] if score > 0])
            
            # 处理旧版API结果
            elif result and isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
                for line in result[0]:
                    if len(line) >= 2 and len(line[1]) >= 2:
                        confidences.append(line[1][1])
            
            return sum(confidences) / len(confidences) if confidences else 0.0
            
        except Exception as e:
            logger.error(f"计算置信度失败: {e}")
            return 0.0
    
    def process_image(self, image_path: str) -> Dict[str, Any]:
        """处理整张图像的OCR识别"""
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
            result = self.ocr_engine.predict(image)
            
            # 解析结果
            text_content, text_blocks = self._parse_result(result)
            
            return {
                'content': text_content,
                'text_blocks': text_blocks,
                'confidence': self._calculate_confidence(result)
            }
            
        except Exception as e:
            logger.error(f"图像OCR处理失败: {e}")
            return {'content': '', 'text_blocks': []}
    
    def get_engine_info(self) -> Dict[str, Any]:
        """获取OCR引擎信息"""
        return {
            'language': self.language,
            'confidence_threshold': self.confidence_threshold,
            'ocr_version': self.ocr_version,
            'device': 'GPU' if self.use_gpu else 'CPU',
            'engine_loaded': self.ocr_engine is not None
        }
