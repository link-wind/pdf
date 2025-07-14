"""Pix2Text解析器 - 基于pix2text库的文本和公式识别"""

import os
import cv2
import numpy as np
import torch
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path

try:
    from pix2text import Pix2Text
    HAS_PIX2TEXT = True
except ImportError:
    Pix2Text = None
    HAS_PIX2TEXT = False

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
            def __init__(self, text: str, bbox: BoundingBox, confidence: float = 1.0, element_type: str = "text"):
                self.text = text
                self.bbox = bbox
                self.confidence = confidence
                self.element_type = element_type
        
        class Region:
            def __init__(self, region_id: str = "", bbox: BoundingBox = None, **kwargs):
                self.region_id = region_id
                self.bbox = bbox or BoundingBox(0, 0, 0, 0)
                for k, v in kwargs.items():
                    setattr(self, k, v)


class Pix2TextProcessor:
    """Pix2Text处理器 - 简化版本"""
    
    def __init__(self, config: Optional[Union['Pix2TextProcessorConfig', Dict[str, Any]]] = None, 
                 total_configs: Optional[Dict[str, Any]] = None, **kwargs):
        """初始化Pix2Text处理器
        
        Args:
            config: Pix2Text处理器配置对象或字典
            total_configs: Pix2Text引擎配置（向后兼容）
            **kwargs: 其他参数（向后兼容）
        """
        # 处理配置对象
        if config is not None:
            if hasattr(config, '__dict__') and hasattr(config, 'to_total_configs'):
                processor_config = config
            else:
                # 如果是字典，创建简单的配置对象
                class SimpleConfig:
                    def __init__(self, **kwargs):
                        for k, v in kwargs.items():
                            setattr(self, k, v)
                        # 设置默认值
                        if not hasattr(self, 'use_gpu'):
                            self.use_gpu = torch.cuda.is_available()
                        if not hasattr(self, 'device'):
                            self.device = 'gpu' if self.use_gpu else 'cpu'
                        if not hasattr(self, 'enabled'):
                            self.enabled = True
                        if not hasattr(self, 'layout'):
                            self.layout = {'scores_thresh': 0.45}
                        if not hasattr(self, 'text_formula'):
                            import os
                            self.text_formula = {
                                'languages': ('en', 'ch_sim'),
                            }
                    
                    def to_total_configs(self):
                        return {
                            'layout': self.layout,
                            'text_formula': self.text_formula
                        }
                
                processor_config = SimpleConfig(**config)
        else:
            # 创建默认配置对象
            class SimpleConfig:
                def __init__(self):
                    self.use_gpu = torch.cuda.is_available()
                    self.device = 'gpu' if self.use_gpu else 'cpu'
                    self.enabled = True
                    self.layout = {'scores_thresh': 0.45}
                    import os
                    self.text_formula = {
                        'languages': ('en', 'ch_sim'),
                    }
                
                def to_total_configs(self):
                    return {
                        'layout': self.layout,
                        'text_formula': self.text_formula
                    }
            
            processor_config = SimpleConfig()
        
        # 从配置对象获取参数
        self.use_gpu = getattr(processor_config, 'use_gpu', torch.cuda.is_available())
        self.device = getattr(processor_config, 'device', 'gpu' if self.use_gpu else 'cpu')
        self.enabled = getattr(processor_config, 'enabled', True)
        
        # 处理total_configs - 优先使用配置对象的格式
        if total_configs is None:
            # 使用配置对象的to_total_configs方法
            if hasattr(processor_config, 'to_total_configs'):
                self.config = processor_config.to_total_configs()
            else:
                # 向后兼容：从配置对象属性构建
                import os
                self.config = {
                    'layout': getattr(processor_config, 'layout', {'scores_thresh': 0.45}),
                    'text_formula': getattr(processor_config, 'text_formula', {
                        'languages': ('en', 'ch_sim')
                    })
                }
        else:
            self.config = total_configs
        
        # 初始化Pix2Text引擎
        self.p2t_engine = None
        if self.enabled:
            self._init_p2t_engine()
    
    @classmethod
    def from_config(cls, config: Union['Pix2TextProcessorConfig', Dict[str, Any]]) -> 'Pix2TextProcessor':
        """从配置对象创建Pix2TextProcessor实例
        
        Args:
            config: Pix2Text处理器配置对象或字典
            
        Returns:
            Pix2TextProcessor: 处理器实例
        """
        return cls(config=config)
    


    def _init_p2t_engine(self) -> None:
        """初始化Pix2Text引擎"""
        try:
            if not HAS_PIX2TEXT:
                logger.error("Pix2Text未安装，请使用pip install pix2text")
                return

            # 使用配置字典直接初始化
            total_configs = self.config.copy()
            
            # 添加设备配置
            if 'device' not in total_configs:
                total_configs['device'] = self.device
            
            # 配置ONNX Runtime执行提供程序（禁用TensorRT）
            if 'text_formula' in total_configs:
                text_formula_config = total_configs['text_formula']
                
                # 扩展模型路径（支持 ~ 符号）
                import os
                if 'text' in text_formula_config and 'rec_model_fp' in text_formula_config['text']:
                    text_formula_config['text']['rec_model_fp'] = os.path.expanduser(text_formula_config['text']['rec_model_fp'])
                
                # 如果配置中指定了ONNX提供程序，则应用
                if 'onnx_providers' in text_formula_config:
                    providers = text_formula_config['onnx_providers']
                    logger.info(f"使用指定的ONNX执行提供程序: {providers}")
                    
                    # 设置环境变量来配置ONNX Runtime
                    import os
                    os.environ['ORT_TENSORRT_UNAVAILABLE'] = '1'  # 禁用TensorRT
                    
                    # 将providers配置传递给text_formula
                    if 'text' not in text_formula_config:
                        text_formula_config['text'] = {}
                    
                    # 为text组件设置ONNX providers
                    text_formula_config['text']['onnx_providers'] = providers
                
                # 如果明确禁用TensorRT
                if text_formula_config.get('disable_tensorrt', False):
                    import os
                    os.environ['ORT_TENSORRT_UNAVAILABLE'] = '1'
                    logger.info("已禁用TensorRT执行提供程序")

            # 添加调试信息
            logger.info(f"Pix2Text配置: {total_configs}")
            
            self.p2t_engine = Pix2Text.from_config(total_configs=total_configs)

            logger.info(f"Pix2Text引擎已初始化: 设备={self.device}")

        except Exception as e:
            logger.error(f"Pix2Text引擎初始化失败: {e}")
            self.p2t_engine = None
    
    def process_region(self, region: Region, image: np.ndarray) -> str:
        """处理单个区域的文本和公式识别，并返回纯文本字符串"""
        if self.p2t_engine is None:
            logger.warning("Pix2Text引擎未初始化")
            return ""
        
        try:
            # 如果是PIL Image，转换为numpy数组
            if hasattr(image, 'mode'):
                image = np.array(image)

            # 裁剪区域
            cropped_image = self._crop_region(image, region.bbox)
            
            # 将Numpy数组转换为PIL.Image对象
            from PIL import Image
            # OpenCV读取的图像是BGR格式，需要转换为RGB
            if cropped_image.shape[2] == 3:  # 彩色图像
                pil_image = Image.fromarray(cv2.cvtColor(cropped_image, cv2.COLOR_BGR2RGB))
            else:  # 灰度图像
                pil_image = Image.fromarray(cropped_image)

            # 进行识别并直接返回结果
            results = self.p2t_engine.recognize_text_formula(pil_image, return_text=True)
            
            # 根据文档，当 return_text=True 时，直接返回一个字符串
            if isinstance(results, str):
                return results
            # 兼容可能返回列表的情况
            elif isinstance(results, list):
                return "\n".join([res.get('text', '') for res in results])
            else:
                logger.warning(f"Pix2Text返回了未知类型的结果: {type(results)}")
                return ""
            
        except Exception as e:
            logger.error(f"Pix2Text处理失败: {e}")
            return ""
    

    
    def _crop_region(self, image: np.ndarray, bbox: BoundingBox) -> np.ndarray:
        """裁剪图像区域"""
        try:
            h, w = image.shape[:2]
            
            # 添加适当的边距
            padding = 20
            x1 = max(0, bbox.x1 - padding)
            y1 = max(0, bbox.y1 - padding)
            x2 = min(w, bbox.x2 + padding)
            y2 = min(h, bbox.y2 + padding)
            
            # 确保坐标有效
            x1 = max(0, min(x1, w-1))
            y1 = max(0, min(y1, h-1))
            x2 = max(x1+1, min(x2, w))
            y2 = max(y1+1, min(y2, h))
            
            cropped = image[y1:y2, x1:x2]
            
            # 确保裁剪区域不为空
            if cropped.size == 0:
                logger.warning(f"裁剪区域为空: {bbox}")
                return image
            
            return cropped
            
        except Exception as e:
            logger.error(f"裁剪区域失败: {e}")
            return image