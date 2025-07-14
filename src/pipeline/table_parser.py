"""表格解析模块 - 基于RapidTable
使用RapidOCR和RapidTable进行高效表格识别
"""

from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import tempfile
import os
from PIL import Image

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from ..config.settings import TableParserConfig
from ..models.document import TableRegion, TableData, BoundingBox

# 尝试导入RapidOCR和RapidTable
try:
    from rapidocr import RapidOCR
    from rapid_table import ModelType, RapidTable, RapidTableInput
    rapid_available = True
    # RapidTable表格解析功能可用
except ImportError:
    rapid_available = False
    logger.warning("无法导入RapidTable，请安装: pip install rapidocr-pytorch rapid-table torch torchvision")

# 尝试导入LLM工具
try:
    from ..utils.llm import parse_table_with_llm
    llm_available = True
    # LLM表格解析功能可用
except ImportError:
    llm_available = False
    logger.warning("无法导入LLM工具，不使用大模型解析表格")


class TableParser:
    """基于RapidTable的表格解析器"""

    def __init__(self, config: TableParserConfig):
        """初始化表格解析器"""
        self.config = config
        self.ocr_engine = None
        self.table_engine = None
        self.parser_type = "none"
        
        # 支持使用大模型
        self.use_llm = getattr(self.config, 'use_llm', False)
        self.llm_api_key = getattr(self.config, 'llm_api_key', None)
        self.llm_fallback = getattr(self.config, 'llm_fallback', True)  # 当其他方法失败时是否使用LLM
        self.llm_priority = getattr(self.config, 'llm_priority', False)  # 是否优先使用LLM
        
        # 监控统计信息
        self.parse_statistics = {
            'total_parsed': 0,
            'successful_parsed': 0,
            'failed_parsed': 0,
            'llm_fallback_used': 0,
            'rapid_table_used': 0,
            'empty_results': 0,
            'parse_errors': 0,
            'total_parse_time': 0.0,
            'avg_parse_time': 0.0
        }
        
        # 如果设置了优先使用LLM但LLM不可用，打印警告
        if self.use_llm and not llm_available:
            logger.warning("配置了使用LLM但LLM模块不可用，将使用其他方法解析表格")
        
        # 初始化解析器
        self._init_parser()
        # 表格解析器初始化完成

    def _init_parser(self) -> None:
        """初始化RapidTable解析器"""
        try:
            # 如果优先使用LLM且LLM可用，则不初始化RapidTable
            if self.use_llm and llm_available and self.llm_priority:
                # 优先使用LLM解析表格，不初始化RapidTable
                self.parser_type = "llm"
                return
            
            # 检查RapidTable是否可用
            if not rapid_available:
                if self.use_llm and llm_available:
                    logger.warning("RapidTable不可用，将使用LLM解析表格")
                    self.parser_type = "llm"
                else:
                    logger.error("RapidTable不可用且无LLM备选，表格将不会被解析")
                    self.parser_type = "none"
                return
            
            # 初始化RapidOCR引擎
            self.ocr_engine = RapidOCR()
            # RapidOCR引擎初始化成功
            
            # 初始化RapidTable引擎
            use_gpu = getattr(self.config, 'use_gpu', True)
            gpu_id = getattr(self.config, 'gpu_id', 0)
            model_type_str = getattr(self.config, 'model_type', 'SLANETPLUS')
            
            # 根据配置选择模型类型
            if model_type_str.upper() == 'UNITABLE':
                model_type = ModelType.UNITABLE
            else:
                model_type = ModelType.SLANETPLUS
            
            if use_gpu:
                # 使用GPU配置 - PyTorch后端
                input_args = RapidTableInput(
                    model_type=model_type,
                    engine_cfg={
                        "providers": ["CUDAExecutionProvider", "CPUExecutionProvider"],
                        "provider_options": [
                            {"device_id": gpu_id},
                            {}
                        ]
                    }
                )
                # 使用GPU配置初始化RapidTable (PyTorch后端)
            else:
                # 使用CPU配置 - PyTorch后端
                input_args = RapidTableInput(
                    model_type=model_type,
                    engine_cfg={
                        "providers": ["CPUExecutionProvider"]
                    }
                )
                # 使用CPU配置初始化RapidTable (PyTorch后端)
            
            self.table_engine = RapidTable(input_args)
            self.parser_type = "rapid_table"
            # RapidTable引擎初始化成功
            
        except ImportError as e:
            if self.use_llm and llm_available:
                logger.warning(f"RapidTable导入失败，将使用LLM解析表格: {e}")
                self.parser_type = "llm"
            else:
                logger.error(f"RapidTable导入失败且无LLM备选: {e}")
                self.parser_type = "none"
        except Exception as e:
            logger.error(f"RapidTable初始化失败: {str(e)}")
            if self.use_llm and llm_available:
                logger.warning("RapidTable初始化失败，将使用LLM解析表格")
                self.parser_type = "llm"
            else:
                self.parser_type = "none"

    def parse(self, table_region: TableRegion) -> TableRegion:
        """解析表格区域，返回包含解析结果的TableRegion对象"""
        import time
        start_time = time.time()
        
        try:
            # 更新统计信息
            self.parse_statistics['total_parsed'] += 1
            
            # 如果没有解析器可用且不使用LLM，直接返回原始区域
            if self.parser_type == "none" and not (self.use_llm and llm_available):
                logger.warning(f"无可用的表格解析器 - 页面: {table_region.page_number}, 区域: {table_region.bbox}")
                self.parse_statistics['failed_parsed'] += 1
                return table_region

            # 解析表格并将结果添加到table_region对象
            table_data_list = self._parse_table(table_region)
            
            # 确保table_content属性存在并赋值
            if table_data_list:
                table_region.table_content = table_data_list
                self.parse_statistics['successful_parsed'] += 1
                
                # 同时设置content属性，用于兼容旧代码
                if not hasattr(table_region, 'content') or not table_region.content:
                    # 生成简单的表格文本表示
                    table_texts = []
                    for table_data in table_data_list:
                        if table_data.headers:
                            table_texts.append(" | ".join(table_data.headers))
                        for row in table_data.rows:
                            table_texts.append(" | ".join(row))
                    table_region.content = "\n".join(table_texts)
                    
                # 表格解析成功
            else:
                self.parse_statistics['empty_results'] += 1
                logger.warning(f"表格解析返回空结果 - 页面: {table_region.page_number}, 区域: {table_region.bbox}")
            
            return table_region

        except Exception as e:
            self.parse_statistics['parse_errors'] += 1
            self.parse_statistics['failed_parsed'] += 1
            logger.error(f"表格解析失败 - 页面: {getattr(table_region, 'page_number', 'unknown')}, 错误: {str(e)}")
            # 确保返回的对象至少有空的table_content属性
            if not hasattr(table_region, 'table_content'):
                table_region.table_content = []
            return table_region
        finally:
            # 更新解析时间统计
            parse_time = time.time() - start_time
            self.parse_statistics['total_parse_time'] += parse_time
            if self.parse_statistics['total_parsed'] > 0:
                self.parse_statistics['avg_parse_time'] = self.parse_statistics['total_parse_time'] / self.parse_statistics['total_parsed']

    def _parse_table(self, table_region: TableRegion) -> List[TableData]:
        """解析表格，支持不同的解析器类型"""
        try:
            # 如果优先使用LLM，先尝试LLM解析
            if self.parser_type == "llm" or (self.use_llm and llm_available and self.llm_priority):
                # 使用LLM进行表格解析
                result = self._parse_with_llm(table_region)
                if result and (len(result) > 0):
                    return result
                
                # 如果LLM解析失败且只使用LLM，则返回空结果
                if self.parser_type == "llm":
                    logger.warning("LLM表格解析失败，无备选解析器")
                    return []
                # 否则继续尝试RapidTable
                # LLM解析失败，尝试RapidTable
            
            # 使用RapidTable解析器
            if self.parser_type == "rapid_table":
                self.parse_statistics['rapid_table_used'] += 1
                result = self._parse_with_rapid_table(table_region)
            else:
                logger.warning("无可用的表格解析器")
                result = []
                
            # 如果RapidTable解析失败，且可以尝试LLM作为后备，则尝试LLM
            if (not result or len(result) == 0) and self.use_llm and llm_available and self.llm_fallback:
                # RapidTable解析失败，尝试使用LLM作为后备
                self.parse_statistics['llm_fallback_used'] += 1
                result = self._parse_with_llm(table_region)
                
            return result
            
        except Exception as e:
            logger.error(f"表格解析失败: {str(e)}")
            # 如果启用了LLM作为后备，即使出错也尝试使用LLM
            if self.use_llm and llm_available and self.llm_fallback:
                try:
                    # 常规解析出错，尝试使用LLM作为后备
                    return self._parse_with_llm(table_region)
                except Exception as llm_e:
                    logger.error(f"LLM后备解析也失败: {str(llm_e)}")
                    
            return []
    
    def get_parse_statistics(self) -> Dict[str, Any]:
        """获取表格解析统计信息"""
        stats = self.parse_statistics.copy()
        
        # 计算成功率
        if stats['total_parsed'] > 0:
            stats['success_rate'] = stats['successful_parsed'] / stats['total_parsed']
            stats['failure_rate'] = stats['failed_parsed'] / stats['total_parsed']
            stats['empty_rate'] = stats['empty_results'] / stats['total_parsed']
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0
            stats['empty_rate'] = 0.0
        
        # 添加解析器使用情况
        stats['parser_type'] = self.parser_type
        stats['llm_available'] = llm_available and self.use_llm
        stats['rapid_table_available'] = rapid_available
        
        return stats
    
    def reset_statistics(self) -> None:
        """重置解析统计信息"""
        self.parse_statistics = {
            'total_parsed': 0,
            'successful_parsed': 0,
            'failed_parsed': 0,
            'llm_fallback_used': 0,
            'rapid_table_used': 0,
            'empty_results': 0,
            'parse_errors': 0,
            'total_parse_time': 0.0,
            'avg_parse_time': 0.0
        }
        # 表格解析统计信息已重置
    
    def log_statistics(self) -> None:
        """记录当前统计信息到日志"""
        stats = self.get_parse_statistics()
        # 表格解析统计信息输出
    
    def _parse_with_llm(self, table_region: TableRegion) -> List[TableData]:
        """使用大模型解析表格"""
        if not llm_available:
            logger.warning("LLM模块不可用，无法使用LLM解析表格")
            return []
            
        try:
            # 提取表格图像
            table_image = self._extract_table_image(table_region)
            if table_image is None:
                return []
                
            # 保存到临时文件
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                    table_image.save(tmp_file.name, 'PNG')
                    temp_path = tmp_file.name
                    
                # 调用LLM解析
                headers, rows = parse_table_with_llm(temp_path, self.llm_api_key)
                
                # 如果解析结果为空，返回空列表
                if not headers and not rows:
                    logger.warning("LLM解析结果为空")
                    return []
                    
                # 构建TableData对象
                # 确保bbox是tuple格式，符合TableData的要求
                if isinstance(table_region.bbox, tuple):
                    bbox_tuple = table_region.bbox
                else:
                    # 将BoundingBox对象转换为tuple
                    bbox_tuple = (table_region.bbox.x1, table_region.bbox.y1, 
                                table_region.bbox.x2, table_region.bbox.y2)
                
                table_data = TableData(
                    headers=headers,
                    rows=rows,
                    bbox=bbox_tuple,
                    confidence=0.95,  # LLM置信度，使用默认值
                    caption=None
                )
                
                return [table_data]
                
            finally:
                # 清理临时文件
                if temp_path and os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"表格解析异常: {str(e)}")
            return []
            
    def _parse_with_rapid_table(self, table_region: TableRegion) -> List[TableData]:
        """使用RapidTable解析表格"""
        try:
            # 提取表格图像
            table_image = self._extract_table_image(table_region)
            if table_image is None:
                return []

            # 保存到临时文件
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                    table_image.save(tmp_file.name, 'PNG')
                    temp_path = tmp_file.name

                # 使用RapidOCR进行OCR识别
                ori_ocr_res = self.ocr_engine(temp_path)
                if not ori_ocr_res or not hasattr(ori_ocr_res, 'boxes'):
                    return []
                
                # 安全检查OCR结果 - 避免NumPy数组的ambiguous truth value错误
                boxes_valid = hasattr(ori_ocr_res, 'boxes') and ori_ocr_res.boxes is not None and len(ori_ocr_res.boxes) > 0
                txts_valid = hasattr(ori_ocr_res, 'txts') and ori_ocr_res.txts is not None and len(ori_ocr_res.txts) > 0
                scores_valid = hasattr(ori_ocr_res, 'scores') and ori_ocr_res.scores is not None and len(ori_ocr_res.scores) > 0
                
                if not (boxes_valid and txts_valid and scores_valid):
                    return []
                
                # 准备OCR结果
                ocr_results = [ori_ocr_res.boxes, ori_ocr_res.txts, ori_ocr_res.scores]
                
                # 使用RapidTable进行表格解析
                results = self.table_engine(temp_path, ocr_results=ocr_results)
                
                if not results:
                    return []
                
                # 解析RapidTable结果
                tables = []
                
                # 检查结果是否有表格数据（使用正确的属性名pred_html）
                if hasattr(results, 'pred_html') and results.pred_html:
                    # 解析HTML表格
                    headers, rows = self._parse_html(results.pred_html)
                    
                    if headers or rows:
                        # 确保bbox是tuple格式，符合TableData的要求
                        if isinstance(table_region.bbox, tuple):
                            bbox_tuple = table_region.bbox
                        else:
                            # 将BoundingBox对象转换为tuple
                            bbox_tuple = (table_region.bbox.x1, table_region.bbox.y1, 
                                        table_region.bbox.x2, table_region.bbox.y2)
                        
                        # 获取置信度
                        confidence = getattr(results, 'confidence', 0.95)
                        
                        table_data = TableData(
                            headers=headers,
                            rows=rows,
                            bbox=bbox_tuple,
                            confidence=confidence,
                            caption=None
                        )
                        tables.append(table_data)
                
                return tables

            finally:
                if temp_path and os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            logger.error(f"RapidTable表格解析错误: {str(e)}")
            return []

    def _parse_html(self, html_content: str) -> Tuple[List[str], List[List[str]]]:
        """简化的HTML表格解析"""
        try:
            # 使用正则表达式直接解析HTML表格
            import re
            
            # 提取所有tr标签内容
            tr_pattern = r'<tr[^>]*>(.*?)</tr>'
            tr_matches = re.findall(tr_pattern, html_content, re.DOTALL | re.IGNORECASE)
            
            if not tr_matches:
                return [], []
            
            matrix = []
            for tr_content in tr_matches:
                # 提取td或th标签内容
                cell_pattern = r'<t[hd][^>]*>(.*?)</t[hd]>'
                cells = re.findall(cell_pattern, tr_content, re.DOTALL | re.IGNORECASE)
                
                if cells:
                    # 清理单元格内容
                    clean_cells = []
                    for cell in cells:
                        # 移除HTML标签
                        clean_text = re.sub(r'<[^>]+>', '', cell)
                        # 处理HTML实体
                        clean_text = clean_text.replace('&nbsp;', ' ')
                        clean_text = clean_text.replace('&amp;', '&')
                        clean_text = clean_text.replace('&lt;', '<')
                        clean_text = clean_text.replace('&gt;', '>')
                        # 清理多余空白
                        clean_text = ' '.join(clean_text.split())
                        clean_cells.append(clean_text)
                    
                    if clean_cells:
                        matrix.append(clean_cells)
            
            if not matrix:
                return [], []
            
            # 处理表格结构
            headers = matrix[0] if matrix else []
            rows = matrix[1:] if len(matrix) > 1 else []
            
            # 过滤空行
            rows = [row for row in rows if any(cell.strip() for cell in row)]
            
            return headers, rows
            
        except Exception as e:
            logger.error(f"HTML解析失败: {str(e)}")
            return [], []

    def _extract_table_image(self, table_region: TableRegion) -> Optional[Image.Image]:
        """提取表格区域图像"""
        try:
            page_image = None
            if hasattr(table_region, 'page_image') and table_region.page_image:
                page_image = table_region.page_image
            elif hasattr(table_region, 'page_path') and table_region.page_path:
                page_image = Image.open(table_region.page_path)
            else:
                return None

            # 裁剪表格区域
            bbox = table_region.bbox
            x1, y1, x2, y2 = int(bbox.x1), int(bbox.y1), int(bbox.x2), int(bbox.y2)

            # 确保坐标有效
            width, height = page_image.size
            x1 = max(0, min(x1, width))
            y1 = max(0, min(y1, height))
            x2 = max(x1, min(x2, width))
            y2 = max(y1, min(y2, height))

            if x2 > x1 and y2 > y1:
                return page_image.crop((x1, y1, x2, y2))
            else:
                logger.error(f"无效坐标: ({x1},{y1},{x2},{y2})")
                return None

        except Exception as e:
            logger.error(f"图像提取失败: {str(e)}")
            return None

    def get_supported_formats(self) -> List[str]:
        """获取支持的表格格式"""
        return ['html']

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        model_type_str = getattr(self.config, 'model_type', 'SLANETPLUS')
        return {
            'name': 'RapidTable',
            'version': 'latest',
            'type': 'table_recognition',
            'ocr_engine': 'RapidOCR',
            'table_engine': model_type_str,
            'parser_type': self.parser_type,
            'use_gpu': getattr(self.config, 'use_gpu', True),
            'gpu_id': getattr(self.config, 'gpu_id', 0),
            'available': self.table_engine is not None and self.ocr_engine is not None
        }
