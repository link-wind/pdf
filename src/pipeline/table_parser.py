"""
表格解析模块 - 简化版
仅使用PaddleOCR PPStructure进行表格识别
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


class TableParser:
    """基于PaddleOCR PPStructure的表格解析器"""

    def __init__(self, config: TableParserConfig):
        """初始化表格解析器"""
        self.config = config
        self.table_model = None
        self.parser_type = "none"
        self._init_parser()
        logger.info("表格解析器初始化完成")

    def _init_parser(self) -> None:
        """初始化表格解析器"""
        try:
            # 尝试导入PPStructureV3
            try:
                from paddleocr import PPStructureV3
                
                # 初始化PPStructureV3 - 不使用任何参数，使用默认配置
                self.table_model = PPStructureV3()
                logger.info("PPStructureV3模型初始化成功")
                self.parser_type = "ppstructure_v3"
                
            except (ImportError, AttributeError):
                # 尝试导入旧版本的PPStructure
            try:
                from paddleocr import PPStructure
                    
                    # 初始化PPStructure
                self.table_model = PPStructure(
                    table=True,
                    ocr=True,
                    layout=False,
                    lang='ch',
                        use_gpu=getattr(self.config, 'use_gpu', True)
                )
                logger.info("PPStructure模型初始化成功")
                self.parser_type = "ppstructure"
                    
                except (ImportError, AttributeError):
                # 如果PPStructure不可用，使用基础的PaddleOCR
                logger.warning("PPStructure不可用，使用基础OCR方式解析表格")
                from paddleocr import PaddleOCR
                self.table_model = PaddleOCR(
                    use_angle_cls=True,
                    lang='ch',
                        use_gpu=getattr(self.config, 'use_gpu', True)
                )
                self.parser_type = "basic_ocr"
                logger.info("使用基础OCR模式进行表格解析")

        except ImportError as e:
            logger.error(f"PaddleOCR未安装，请运行: pip install paddleocr, 错误: {e}")
            self.table_model = None
            self.parser_type = "none"
        except Exception as e:
            logger.error(f"表格解析器初始化失败: {str(e)}")
            self.table_model = None
            self.parser_type = "none"

    def parse(self, table_region: TableRegion) -> TableRegion:
        """解析表格区域，返回包含解析结果的TableRegion对象"""
        try:
            if self.table_model is None:
                logger.warning("PPStructure模型未初始化")
                return table_region  # 返回原始表格区域

            # 解析表格并将结果添加到table_region对象
            table_data_list = self._parse_table(table_region)
            
            # 确保table_content属性存在并赋值
            if table_data_list:
                table_region.table_content = table_data_list
                
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
            
            return table_region

        except Exception as e:
            logger.error(f"表格解析失败: {str(e)}")
            # 确保返回的对象至少有空的table_content属性
            if not hasattr(table_region, 'table_content'):
                table_region.table_content = []
            return table_region

    def _parse_table(self, table_region: TableRegion) -> List[TableData]:
        """解析表格，支持不同的解析器类型"""
        try:
            if self.parser_type == "ppstructure_v3":
                return self._parse_with_ppstructure_v3(table_region)
            elif self.parser_type == "ppstructure":
                return self._parse_with_ppstructure(table_region)
            elif self.parser_type == "basic_ocr":
                return self._parse_with_basic_ocr(table_region)
            else:
                logger.warning("表格解析器不可用，返回空结果")
                return []

        except Exception as e:
            logger.error(f"表格解析失败: {str(e)}")
            return []
            
    def _parse_with_ppstructure_v3(self, table_region: TableRegion) -> List[TableData]:
        """使用PPStructureV3解析表格"""
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

                # PPStructureV3识别
                output = self.table_model.predict(input=temp_path)
                
                # 解析结果
                tables = []
                for res in output:
                    # 检查是否为表格类型
                    if hasattr(res, 'type') and res.type == 'table':
                        # 从结果中提取表格数据
                        if hasattr(res, 'html'):
                            headers, rows = self._parse_html(res.html)
                            
                            if headers or rows:
                                # 确保使用正确的BoundingBox对象
                                if isinstance(table_region.bbox, tuple):
                                    bbox = BoundingBox(
                                        x1=table_region.bbox[0],
                                        y1=table_region.bbox[1],
                                        x2=table_region.bbox[2],
                                        y2=table_region.bbox[3]
                                    )
                                else:
                                    bbox = table_region.bbox
                                
                                table_data = TableData(
                                    headers=headers,
                                    rows=rows,
                                    bbox=bbox,
                                    confidence=0.95,  # PPStructureV3不提供置信度，使用默认值
                                    caption=None
                                )
                                tables.append(table_data)
                                logger.debug(f"解析到表格: {len(headers)}列表头, {len(rows)}行数据")
                
                return tables

            finally:
                if temp_path and os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            logger.error(f"PPStructureV3表格解析错误: {str(e)}")
            return []

    def _parse_with_ppstructure(self, table_region: TableRegion) -> List[TableData]:
        """使用PPStructure解析表格"""
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

                # PPStructure识别
                result = self.table_model(temp_path)

                # 解析结果
                tables = []
                if result and isinstance(result, list):
                    for item in result:
                        table_data = self._parse_result(item, table_region)
                        if table_data:
                            tables.append(table_data)

                return tables

            finally:
                if temp_path and os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            logger.error(f"表格解析错误: {str(e)}")
            return []

    def _parse_result(self, result_item: Dict, table_region: TableRegion) -> Optional[TableData]:
        """解析PPStructure结果"""
        try:
            if not isinstance(result_item, dict) or result_item.get('type') != 'table':
                return None

            res_data = result_item.get('res', {})
            if not res_data or 'html' not in res_data:
                return None

            # 解析HTML表格
            headers, rows = self._parse_html(res_data['html'])

            if not headers and not rows:
                return None

            # 确保使用正确的BoundingBox对象
            if isinstance(table_region.bbox, tuple):
                bbox = BoundingBox(
                    x1=table_region.bbox[0],
                    y1=table_region.bbox[1],
                    x2=table_region.bbox[2],
                    y2=table_region.bbox[3]
                )
            else:
                bbox = table_region.bbox

            return TableData(
                headers=headers,
                rows=rows,
                bbox=bbox,
                confidence=0.95,
                caption=None
            )

        except Exception as e:
            logger.error(f"结果解析失败: {str(e)}")
            return None

    def _parse_html(self, html_content: str) -> Tuple[List[str], List[List[str]]]:
        """简化的HTML表格解析"""
        try:
            logger.debug(f"解析HTML表格内容: {html_content[:200]}...")
            
            # 使用正则表达式直接解析HTML表格
            import re
            
            # 提取所有tr标签内容
            tr_pattern = r'<tr[^>]*>(.*?)</tr>'
            tr_matches = re.findall(tr_pattern, html_content, re.DOTALL | re.IGNORECASE)
            
            if not tr_matches:
                logger.warning("未找到表格行")
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
                logger.warning("解析后表格为空")
                return [], []
            
            logger.debug(f"解析得到表格矩阵: {matrix}")
            
            # 处理表格结构
            headers = matrix[0] if matrix else []
            rows = matrix[1:] if len(matrix) > 1 else []
            
            # 过滤空行
            rows = [row for row in rows if any(cell.strip() for cell in row)]
            
            logger.info(f"表格解析完成: {len(headers)}列表头, {len(rows)}行数据")
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
                logger.warning("无法获取页面图像")
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
        return {
            'name': 'PPStructure',
            'version': '2.7+',
            'type': 'table_recognition',
            'available': self.table_model is not None
        }

    def _parse_with_basic_ocr(self, table_region: TableRegion) -> List[TableData]:
        """使用基础OCR解析表格（降级方案）"""
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

                # 基础OCR识别
                result = self.table_model.ocr(temp_path, cls=True)

                # 将OCR结果转换为简单的表格数据
                text_lines = []
                if result and result[0]:
                    # 按Y坐标排序，形成行
                    for line in result[0]:
                        if len(line) >= 2:
                            box = line[0]
                            text_info = line[1]
                            if len(text_info) >= 2:
                                text = text_info[0]
                                confidence = text_info[1]
                                if confidence >= self.config.confidence_threshold:
                                    # 获取Y坐标用于排序
                                    y_coord = min([point[1] for point in box])
                                    text_lines.append((y_coord, text))
                    
                    # 按Y坐标排序
                    text_lines.sort(key=lambda x: x[0])
                    
                # 如果有文本行，创建简单的表格结构
                if text_lines:
                    # 提取所有文本
                    texts = [text for _, text in text_lines]
                    
                    # 确保使用正确的BoundingBox对象
                    if isinstance(table_region.bbox, tuple):
                        bbox = BoundingBox(
                            x1=table_region.bbox[0],
                            y1=table_region.bbox[1],
                            x2=table_region.bbox[2],
                            y2=table_region.bbox[3]
                        )
                    else:
                        bbox = table_region.bbox
                    
                    # 创建一个简单的单列表格
                    headers = ["内容"]
                    rows = [[text] for text in texts]
                    
                    table_data = TableData(
                        headers=headers,
                        rows=rows,
                        bbox=bbox,
                        confidence=0.8,
                        caption=None
                    )

                    return [table_data]
                
                return []

            finally:
                if temp_path and os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            logger.error(f"基础OCR表格解析失败: {str(e)}")
            return []
