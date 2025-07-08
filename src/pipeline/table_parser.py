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
from ..models.document import TableRegion, TableData


class TableParser:
    """基于PaddleOCR PPStructure的表格解析器"""

    def __init__(self, config: TableParserConfig):
        """初始化表格解析器"""
        self.config = config
        self.table_model = None
        self._init_parser()
        logger.info("表格解析器初始化完成")

    def _init_parser(self) -> None:
        """初始化PPStructure模型"""
        try:
            from paddleocr import PPStructure

            self.table_model = PPStructure(
                table=True,
                ocr=True,
                layout=False,
                show_log=False,
                lang='ch',
                use_gpu=True
            )
            logger.info("PPStructure模型初始化成功")

        except ImportError as e:
            logger.error("PaddleOCR未安装，请运行: pip install paddleocr")
            raise
        except Exception as e:
            logger.error(f"PPStructure初始化失败: {str(e)}")
            self.table_model = None

    def parse(self, table_region: TableRegion) -> List[TableData]:
        """解析表格区域"""
        try:
            if self.table_model is None:
                logger.warning("PPStructure模型未初始化")
                return []

            return self._parse_table(table_region)

        except Exception as e:
            logger.error(f"表格解析失败: {str(e)}")
            return []

    def _parse_table(self, table_region: TableRegion) -> List[TableData]:
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

            return TableData(
                headers=headers,
                rows=rows,
                bbox=table_region.bbox,
                confidence=0.95,
                caption=None
            )

        except Exception as e:
            logger.error(f"结果解析失败: {str(e)}")
            return None

    def _parse_html(self, html_content: str) -> Tuple[List[str], List[List[str]]]:
        """解析HTML表格内容，优化HTML到LaTeX转换"""
        try:
            # 使用BeautifulSoup解析HTML
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')
                table = soup.find('table')

                if not table:
                    return [], []

                # 提取表格矩阵，保留原始HTML格式信息
                matrix = []
                for tr in table.find_all('tr'):
                    row = []
                    for cell in tr.find_all(['td', 'th']):
                        text = self._extract_cell_content_with_formatting(cell)
                        row.append(text)
                    if row:
                        matrix.append(row)

                if not matrix:
                    return [], []

                logger.debug(f"解析表格矩阵: {len(matrix)}行")

                # 检查是否为单列表格且需要智能分割
                if len(matrix) > 0 and all(len(row) == 1 for row in matrix):
                    logger.info("检测到单列表格，启动智能分割")
                    headers, rows = self._smart_split_single_column_table(matrix)

                    if headers and rows:
                        logger.info(f"智能分割成功: {len(headers)}列, {len(rows)}行")
                        return headers, rows
                    else:
                        logger.warning("智能分割失败，使用原始格式")

                # 正常多列表格处理
                headers = matrix[0] if matrix else []
                rows = matrix[1:] if len(matrix) > 1 else []

                # 过滤空行但保留格式
                rows = [row for row in rows if any(cell.strip() for cell in row)]

                return headers, rows

            except ImportError:
                logger.warning("BeautifulSoup未安装，使用简单HTML解析")
                return self._simple_html_parse(html_content)
            except Exception as e:
                logger.error(f"BeautifulSoup解析失败: {str(e)}")
                return self._simple_html_parse(html_content)

        except Exception as e:
            logger.error(f"HTML解析失败: {str(e)}")
            return [], []

    def _extract_cell_content_with_formatting(self, cell) -> str:
        """提取单元格内容，保留原始文本"""
        try:
            text = cell.get_text(separator=' ', strip=True)
            return text
        except Exception as e:
            logger.debug(f"单元格内容提取失败: {e}")
            return cell.get_text(strip=True) if cell else ""

    def _smart_split_single_column_table(self, matrix: List[List[str]]) -> Tuple[List[str], List[List[str]]]:
        """智能分割单列表格"""
        try:
            if not matrix:
                return [], []

            logger.debug(f"开始智能分割单列表格，原始数据: {matrix}")

            # 分析表头内容
            header_text = matrix[0][0].strip()

            import re

            # 方法1: 基于语义和格式的智能分割
            pattern = r'([^\s]+(?:\([^)]+\))?(?:\{[^}]+\})?)'
            header_matches = re.findall(pattern, header_text)

            if len(header_matches) >= 3:
                headers = [match.strip() for match in header_matches]
                logger.info(f"基于模式匹配识别表头: {headers}")

                rows = []
                for row in matrix[1:]:
                    if not row or not row[0]:
                        continue

                    row_text = row[0].strip()
                    row_parts = self._split_data_row_optimized(row_text, len(headers))

                    if row_parts and len(row_parts) >= len(headers):
                        rows.append(row_parts[:len(headers)])
                        logger.debug(f"成功分割数据行: {row_parts[:len(headers)]}")

                if rows:
                    return headers, rows

            # 方法2: 基于多个空格的分割
            space_split = re.split(r'\s{2,}', header_text)
            if len(space_split) > 1:
                headers = [part.strip() for part in space_split if part.strip()]

                rows = []
                for row in matrix[1:]:
                    if row and row[0]:
                        row_parts = re.split(r'\s{2,}', row[0].strip())
                        row_parts = [part.strip() for part in row_parts if part.strip()]
                        if len(row_parts) >= len(headers):
                            rows.append(row_parts[:len(headers)])

                if rows:
                    logger.info(f"基于空格分割成功: {len(headers)}列")
                    return headers, rows

            # 方法3: 回退到简单分割
            return self._fallback_split_optimized(matrix)

        except Exception as e:
            logger.error(f"智能分割失败: {str(e)}")
            return self._fallback_split_optimized(matrix)

    def _split_data_row_optimized(self, row_text: str, expected_cols: int) -> List[str]:
        """优化的数据行分割"""
        try:
            import re

            patterns = [
                r'([A-Za-z]+(?:\s+[A-Za-z]+)*)',
                r'(-?\d+\.?\d*\s*\~\s*-?\d+\.?\d*)',
                r'(-?\d+\.?\d*)',
                r'(\([^)]+\))',
                r'(\{[^}]+\})',
            ]

            parts = []
            remaining_text = row_text.strip()
            max_iterations = expected_cols * 2
            iteration_count = 0

            while remaining_text and len(parts) < expected_cols and iteration_count < max_iterations:
                iteration_count += 1
                found = False
                for pattern in patterns:
                    match = re.search(pattern, remaining_text)
                    if match:
                        matched_text = match.group(1)
                        parts.append(matched_text.strip())
                        remaining_text = remaining_text[:match.start()] + remaining_text[match.end():]
                        remaining_text = remaining_text.strip()
                        found = True
                        break

                if not found:
                    words = remaining_text.split()
                    if words:
                        parts.append(words[0])
                        remaining_text = ' '.join(words[1:])
                    else:
                        break

            if remaining_text and len(parts) < expected_cols:
                parts.append(remaining_text)

            while len(parts) < expected_cols:
                parts.append("")

            return parts[:expected_cols]

        except Exception as e:
            logger.debug(f"优化数据行分割失败: {e}")
            simple_parts = row_text.split()
            if len(simple_parts) >= expected_cols:
                return simple_parts[:expected_cols]
            else:
                simple_parts.extend([""] * (expected_cols - len(simple_parts)))
                return simple_parts

    def _fallback_split_optimized(self, matrix: List[List[str]]) -> Tuple[List[str], List[List[str]]]:
        """优化的后备分割方案"""
        try:
            if not matrix:
                return [], []

            header_parts = [part for part in matrix[0][0].split()]

            rows = []
            for row in matrix[1:]:
                if row and row[0]:
                    row_parts = [part for part in row[0].split()]
                    if row_parts:
                        rows.append(row_parts)

            return header_parts, rows

        except Exception as e:
            logger.error(f"优化后备分割失败: {e}")
            return [matrix[0][0]] if matrix else [], [[row[0]] for row in matrix[1:] if row and row[0]]

    def _simple_html_parse(self, html_content: str) -> Tuple[List[str], List[List[str]]]:
        """简单HTML解析，当BeautifulSoup不可用时使用"""
        try:
            import re

            tr_pattern = r'<tr[^>]*>(.*?)</tr>'
            rows_html = re.findall(tr_pattern, html_content, re.DOTALL | re.IGNORECASE)

            if not rows_html:
                return [], []

            matrix = []
            for row_html in rows_html:
                cell_pattern = r'<t[hd][^>]*>(.*?)</t[hd]>'
                cells = re.findall(cell_pattern, row_html, re.DOTALL | re.IGNORECASE)

                clean_cells = []
                for cell in cells:
                    clean_text = re.sub(r'<[^>]+>', '', cell)
                    clean_text = clean_text.replace('&nbsp;', ' ').replace('&amp;', '&')
                    clean_text = clean_text.replace('&lt;', '<').replace('&gt;', '>')
                    clean_cells.append(clean_text.strip())

                if clean_cells:
                    matrix.append(clean_cells)

            if not matrix:
                return [], []

            headers = matrix[0] if matrix else []
            rows = matrix[1:] if len(matrix) > 1 else []

            return headers, rows

        except Exception as e:
            logger.error(f"简单HTML解析失败: {str(e)}")
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
