"""
阅读顺序分析器 - 基于LayoutLMv3模型

参考MinerU的LayoutReader实现，优化了模型管理、数据预处理和冲突解决机制
"""

import os
import time
import warnings
from collections import defaultdict
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    import torch
    from transformers import LayoutLMv3ForTokenClassification
    HAS_TRANSFORMERS = True
except ImportError:
    logger.warning("transformers库未安装，无法使用LayoutLMv3模型")
    HAS_TRANSFORMERS = False

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

# LayoutLMv3模型相关常量
MAX_LEN = 510           # 最大序列长度
MAX_REGIONS = 200       # 实际处理限制（更保守）
CLS_TOKEN_ID = 0        # 分类开始标记
UNK_TOKEN_ID = 3        # 未知标记
EOS_TOKEN_ID = 2        # 序列结束标记


class ModelSingleton:
    """单例模式管理LayoutLMv3模型，避免重复加载"""
    _instance = None
    _models = {}
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_model(self, model_path: str, device: str = "auto"):
        """获取或创建模型实例"""
        cache_key = f"{model_path}_{device}"
        if cache_key not in self._models:
            self._models[cache_key] = self._init_model(model_path, device)
        return self._models[cache_key]
    
    def _init_model(self, model_path: str, device: str):
        """初始化LayoutLMv3模型"""
        if not HAS_TRANSFORMERS:
            raise RuntimeError("transformers库未安装")
        
        # 设备检测
        if device == "auto":
            device_name = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            device_name = device
        
        device_obj = torch.device(device_name)
        
        # 检测bfloat16支持
        bf16_support = False
        if device_name.startswith("cuda"):
            bf16_support = torch.cuda.is_bf16_supported()
        elif device_name.startswith("mps"):
            bf16_support = True
        
        try:
            logger.info(f"加载LayoutLMv3模型: {model_path}")
            
            # 检查本地模型
            if os.path.exists(model_path) and os.path.isdir(model_path):
                model = LayoutLMv3ForTokenClassification.from_pretrained(model_path)
                logger.info(f"从本地加载模型: {model_path}")
            else:
                # 从HuggingFace加载
                logger.warning(f"本地模型不存在: {model_path}，从HuggingFace加载")
                model = LayoutLMv3ForTokenClassification.from_pretrained("hantian/layoutreader")
            
            # 配置设备和精度
            model.to(device_obj).eval()
            if bf16_support:
                model = model.bfloat16()
                logger.info(f"模型已配置为bfloat16精度，设备: {device_name}")
            else:
                logger.info(f"模型使用默认精度，设备: {device_name}")
            
            return model
            
        except Exception as e:
            logger.error(f"模型初始化失败: {e}")
            raise RuntimeError(f"LayoutLMv3模型加载失败: {e}")


def coordinate_normalization(boxes: List[List[int]], page_w: float, page_h: float) -> List[List[int]]:
    """
    坐标标准化到1000x1000尺寸
    
    Args:
        boxes: 原始边界框列表 [[x1,y1,x2,y2], ...]
        page_w: 页面宽度
        page_h: 页面高度
    
    Returns:
        List[List[int]]: 标准化后的边界框
    """
    x_scale = 1000.0 / page_w
    y_scale = 1000.0 / page_h
    
    normalized_boxes = []
    for left, top, right, bottom in boxes:
        # 边界检查和修正
        left = max(0, min(left, page_w))
        right = max(0, min(right, page_w))
        top = max(0, min(top, page_h))
        bottom = max(0, min(bottom, page_h))
        
        # 坐标缩放
        left = round(left * x_scale)
        top = round(top * y_scale)
        right = round(right * x_scale)
        bottom = round(bottom * y_scale)
        
        # 确保坐标在有效范围内
        left = max(0, min(1000, left))
        top = max(0, min(1000, top))
        right = max(left, min(1000, right))
        bottom = max(top, min(1000, bottom))
        
        # 验证坐标有效性
        assert (
            1000 >= right >= left >= 0 and 1000 >= bottom >= top >= 0
        ), f'Invalid box coordinates: [{left}, {top}, {right}, {bottom}]'
        
        normalized_boxes.append([left, top, right, bottom])
    
    return normalized_boxes


def boxes2inputs(boxes: List[List[int]]) -> Dict[str, torch.Tensor]:
    """
    将边界框列表转换为模型输入格式
    
    Args:
        boxes: 标准化后的边界框列表 [[x1,y1,x2,y2], ...]
    
    Returns:
        Dict: 模型输入字典，包含 bbox, input_ids, attention_mask
    """
    # 添加 CLS 和 EOS 的虚拟边界框
    bbox = [[0, 0, 0, 0]] + boxes + [[0, 0, 0, 0]]
    
    # 构建输入序列：[CLS] + [UNK]*len(boxes) + [EOS]
    input_ids = [CLS_TOKEN_ID] + [UNK_TOKEN_ID] * len(boxes) + [EOS_TOKEN_ID]
    
    # 注意力掩码：所有位置都是有效的
    attention_mask = [1] + [1] * len(boxes) + [1]
    
    return {
        "bbox": torch.tensor([bbox]),
        "attention_mask": torch.tensor([attention_mask]),
        "input_ids": torch.tensor([input_ids]),
    }


def prepare_inputs(
    inputs: Dict[str, torch.Tensor], 
    model: LayoutLMv3ForTokenClassification
) -> Dict[str, torch.Tensor]:
    """
    将输入张量转移到模型设备并调整精度
    
    Args:
        inputs: 输入字典
        model: LayoutLMv3模型实例
    
    Returns:
        Dict: 准备好的输入字典
    """
    ret = {}
    for k, v in inputs.items():
        v = v.to(model.device)
        if torch.is_floating_point(v):
            v = v.to(model.dtype)
        ret[k] = v
    return ret


def parse_logits(logits: torch.Tensor, length: int) -> List[int]:
    """
    解析模型输出的logits为阅读顺序，处理排序冲突
    
    关键思想：
    1. 模型输出是一个 [seq_len, seq_len] 的矩阵
    2. logits[i][j] 表示第 i 个区域被排在第 j 位的概率
    3. 需要为每个区域分配唯一的排序位置
    
    Args:
        logits: 模型输出的logits，形状为 [seq_len, seq_len]
        length: 实际输入的区域数量
    
    Returns:
        List[int]: 每个区域的阅读顺序索引
    """
    # 1. 提取有效部分（排除CLS和EOS标记）
    logits = logits[1 : length + 1, :length]
    
    # 2. 对每行logits进行排序，得到候选顺序列表
    # orders[i] 是第 i 个区域的排序候选列表，按概率降序排列
    orders = logits.argsort(descending=False).tolist()
    
    # 3. 初始选择：每个位置选择概率最高的顺序
    ret = [o.pop() for o in orders]
    
    # 4. 迭代解决冲突
    max_iterations = length * 2  # 防止无限循环
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        # 统计每个顺序位置被分配给了哪些区域
        order_to_idxes = defaultdict(list)
        for idx, order in enumerate(ret):
            order_to_idxes[order].append(idx)
        
        # 找出有冲突的顺序位置（被多个区域选择）
        conflicted_orders = {k: v for k, v in order_to_idxes.items() if len(v) > 1}
        
        if not conflicted_orders:
            break  # 没有冲突，退出循环
        
        # 解决每个冲突
        for order, idxes in conflicted_orders.items():
            # 找到该顺序位置下各区域的原始logit值
            idxes_to_logit = {}
            for idx in idxes:
                idxes_to_logit[idx] = logits[idx, order]
            
            # 按logit值降序排序
            idxes_to_logit = sorted(
                idxes_to_logit.items(), key=lambda x: x[1], reverse=True
            )
            
            # 保留logit最高的区域使用当前顺序位置
            # 其他区域选择各自的次优顺序位置
            for idx, _ in idxes_to_logit[1:]:
                if orders[idx]:  # 确保还有候选位置
                    ret[idx] = orders[idx].pop()
                else:
                    # 如果没有更多候选，使用一个唯一的位置
                    used_positions = set(ret)
                    for pos in range(length):
                        if pos not in used_positions:
                            ret[idx] = pos
                            break
    
    if iteration >= max_iterations:
        logger.warning(f"解析logits时达到最大迭代次数 {max_iterations}，可能存在未解决的冲突")
    
    return ret


def do_predict(boxes: List[List[int]], model: LayoutLMv3ForTokenClassification) -> List[int]:
    """
    使用 LayoutLMv3 模型预测阅读顺序
    
    Args:
        boxes: 标准化后的边界框列表
        model: LayoutLMv3 模型实例
    
    Returns:
        List[int]: 阅读顺序索引列表
    """
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")
        
        # 1. 转换输入格式
        inputs = boxes2inputs(boxes)
        
        # 2. 准备模型输入（设备和精度转换）
        inputs = prepare_inputs(inputs, model)
        
        # 3. 模型推理
        with torch.no_grad():
            logits = model(**inputs).logits.cpu().squeeze(0)
    
    # 4. 解析输出得到排序结果
    return parse_logits(logits, len(boxes))


class ReadingOrderAnalyzer:
    """阅读顺序分析器 - 基于LayoutLMv3，采用MinerU的最佳实践"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化阅读顺序分析器
        
        Args:
            config: 配置字典
        """
        self.config = config
        
        # LayoutLMv3配置
        self.layout_reader_model_path = getattr(config, 'layout_reader_model_path', 'hantian/layoutreader')
        self.device = getattr(config, 'device', 'auto')
        
        # 获取模型实例（单例模式）
        self.model_manager = ModelSingleton()
        
        # 验证模型可用性
        if not HAS_TRANSFORMERS:
            raise RuntimeError("transformers库未安装，无法使用LayoutLMv3模型")
        
        try:
            # 尝试加载模型以验证配置
            _ = self.model_manager.get_model(self.layout_reader_model_path, self.device)
            logger.info("阅读顺序分析器初始化完成，使用LayoutLMv3模型")
        except Exception as e:
            logger.error(f"初始化LayoutLMv3预测器失败: {e}")
            raise RuntimeError(f"LayoutLMv3模型加载失败: {e}")
    
    def analyze_reading_order(self, document: Document) -> None:
        """分析整个文档的阅读顺序
        
        Args:
            document: 文档对象，将直接修改其页面区域的顺序
        """
        try:
            logger.info("开始使用LayoutLMv3分析阅读顺序...")
            
            # 为每个页面分析阅读顺序
            for page_num, page in enumerate(document.pages):
                try:
                    logger.debug(f"分析页面 {page_num + 1} 的阅读顺序")
                    self._analyze_page_reading_order(page)
                    
                except Exception as page_error:
                    logger.warning(f"页面 {page_num + 1} 阅读顺序分析失败: {page_error}")
                    # 设置默认顺序
                    self._set_default_reading_order(page)
                    continue
            
            logger.info("阅读顺序分析完成")
            
        except Exception as e:
            logger.error(f"阅读顺序分析失败: {e}")
            # 为所有页面设置默认的阅读顺序
            for page in document.pages:
                self._set_default_reading_order(page)
    
    def _analyze_page_reading_order(self, page: Page) -> None:
        """分析单页的阅读顺序
        
        Args:
            page: 页面对象
        """
        # 获取页面的所有区域
        regions = self._get_page_regions(page)
        
        if not regions:
            logger.debug("页面没有区域")
            return
        
        if len(regions) == 1:
            # 只有一个区域，直接设置顺序
            regions[0].reading_order = 1
            return
        
        # 检查区域数量限制
        if len(regions) > MAX_REGIONS:
            logger.warning(f"页面区域数量 {len(regions)} 超过限制 {MAX_REGIONS}，使用默认排序")
            self._set_default_reading_order(page)
            return
        
        # 使用LayoutLMv3进行阅读顺序预测
        ordered_regions = self._layoutlmv3_order(regions, page)
        
        # 更新页面区域顺序
        self._update_page_regions(page, ordered_regions)
    
    def _get_page_regions(self, page: Page) -> List[Region]:
        """获取页面的所有区域，除了Abandon类型的区域
        
        现在所有非Abandon的区域都会在layout_analyzer中被创建，包括Figure、Caption等，
        因此这里直接返回所有区域即可。
        """
        regions = []
        if hasattr(page, 'regions') and page.regions:
            regions = list(page.regions)
        elif hasattr(page, 'all_regions') and page.all_regions:
            regions = list(page.all_regions)
        
        logger.debug(f"获取到 {len(regions)} 个区域用于阅读顺序分析")
        return regions
    
    def _layoutlmv3_order(self, regions: List[Region], page: Page) -> List[Region]:
        """使用LayoutLMv3进行阅读顺序分析
        
        Args:
            regions: 区域列表
            page: 页面对象
            
        Returns:
            List[Region]: 重排序后的区域列表
        """
        logger.debug(f"使用LayoutLMv3分析 {len(regions)} 个区域的阅读顺序")
        
        # 提取bbox
        boxes = []
        region_info = []  # 用于调试
        
        for i, region in enumerate(regions):
            if hasattr(region, 'bbox') and region.bbox:
                bbox = region.bbox
                # 转换为[left, top, right, bottom]格式
                box = [
                    int(bbox.x1), int(bbox.y1), 
                    int(bbox.x2), int(bbox.y2)
                ]
                boxes.append(box)
                
                # 记录调试信息
                content_preview = (region.content[:50] + '...') if hasattr(region, 'content') and region.content and len(region.content) > 50 else getattr(region, 'content', '[无内容]')
                region_info.append({
                    'index': i,
                    'type': region.region_type.value if hasattr(region.region_type, 'value') else str(region.region_type),
                    'bbox': box,
                    'content_preview': content_preview
                })
            else:
                # 如果没有bbox，使用默认值
                boxes.append([0, 0, 100, 100])
                region_info.append({
                    'index': i,
                    'type': 'Unknown',
                    'bbox': [0, 0, 100, 100],
                    'content_preview': '[无bbox]'
                })
        
        # 输出调试信息
        logger.debug("输入区域信息:")
        for info in region_info:
            logger.debug(f"  区域{info['index']}: {info['type']} {info['bbox']} - {info['content_preview']}")
        
        # 获取页面尺寸
        page_width = getattr(page, 'width', 1000)
        page_height = getattr(page, 'height', 1000)
        logger.debug(f"页面尺寸: {page_width} x {page_height}")
        
        try:
            # 1. 坐标标准化
            normalized_boxes = coordinate_normalization(boxes, page_width, page_height)
            
            # 2. 获取模型
            model = self.model_manager.get_model(self.layout_reader_model_path, self.device)
            
            # 3. 模型推理
            start_time = time.time()
            predicted_orders = do_predict(normalized_boxes, model)
            elapsed = time.time() - start_time
            
            logger.debug(f"LayoutLMv3预测完成，耗时: {elapsed:.3f}s")
            logger.debug(f"预测的原始顺序: {predicted_orders}")
            
            # 4. 重新解释预测顺序：predicted_orders是按位置排序的区域索引列表
            # predicted_orders[i] 表示第i+1位应该是哪个区域
            ordered_regions = []
            for position, region_idx in enumerate(predicted_orders):
                if region_idx < len(regions):
                    regions[region_idx].reading_order = position + 1
                    ordered_regions.append(regions[region_idx])
            
            # 5. 如果有遗漏的区域，按原始顺序添加到最后
            for i, region in enumerate(regions):
                if not hasattr(region, 'reading_order') or region.reading_order is None:
                    region.reading_order = len(ordered_regions) + 1
                    ordered_regions.append(region)
            
            # 6. 输出最终排序结果
            logger.debug("最终阅读顺序:")
            for i, region in enumerate(ordered_regions):
                content_preview = (region.content[:30] + '...') if hasattr(region, 'content') and region.content and len(region.content) > 30 else getattr(region, 'content', '[无内容]')
                logger.debug(f"  {i+1}: {region.region_type.value if hasattr(region.region_type, 'value') else str(region.region_type)} - {content_preview}")
            
            return ordered_regions
            
        except Exception as e:
            logger.error(f"LayoutLMv3分析失败: {e}")
            # 返回原始顺序
            for i, region in enumerate(regions):
                region.reading_order = i + 1
            return regions
    
    def _update_page_regions(self, page: Page, ordered_regions: List[Region]) -> None:
        """更新页面区域顺序"""
        try:
            # 检查是否是PageLayout对象（有分类列表）
            if hasattr(page, 'text_regions') and hasattr(page, 'table_regions'):
                # PageLayout对象，清理并重新分类
                logger.debug("PageLayout对象，重新分类区域")
                page.text_regions.clear()
                page.table_regions.clear()
                page.formula_regions.clear()
                page.image_regions.clear()
                
                # 一次性添加所有区域
                for region in ordered_regions:
                    page.add_region(region)
            else:
                # 尝试直接赋值（Page对象）
                if hasattr(page, 'regions') and hasattr(page.regions, 'clear'):
                    page.regions.clear()
                    page.regions.extend(ordered_regions)
                elif hasattr(page, 'regions') and not isinstance(page.regions, property):
                    page.regions = ordered_regions
        except Exception as update_error:
            logger.debug(f"更新页面区域失败，但区域顺序已设置: {update_error}")
            # 即使更新失败，reading_order已经设置，不影响后续处理
    
    def _set_default_reading_order(self, page: Page) -> None:
        """设置默认的阅读顺序（简单的从上到下，从左到右）"""
        try:
            regions = self._get_page_regions(page)
            
            # 简单的几何排序：先按y坐标，再按x坐标
            def get_sort_key(region):
                if hasattr(region, 'bbox') and region.bbox:
                    return (region.bbox.y1, region.bbox.x1)
                return (0, 0)
            
            sorted_regions = sorted(regions, key=get_sort_key)
            
            for i, region in enumerate(sorted_regions):
                region.reading_order = i + 1
                
            logger.debug(f"设置默认阅读顺序，共 {len(sorted_regions)} 个区域")
            
        except Exception as e:
            logger.error(f"设置默认阅读顺序失败: {e}")
    
    def get_algorithm_info(self) -> Dict[str, Any]:
        """获取算法信息
        
        Returns:
            Dict[str, Any]: 算法信息
        """
        try:
            model = self.model_manager.get_model(self.layout_reader_model_path, self.device)
            model_available = model is not None
        except:
            model_available = False
            
        return {
            'algorithm': 'layoutlmv3',
            'layout_reader_model_path': self.layout_reader_model_path,
            'device': self.device,
            'max_regions': MAX_REGIONS,
            'layoutlmv3_available': model_available,
            'transformers_available': HAS_TRANSFORMERS
        }
