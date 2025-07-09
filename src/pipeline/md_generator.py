"""
Markdown生成模块
将解析后的文档内容转换为Markdown格式
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import re

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from ..config.settings import MarkdownGeneratorConfig
from ..models.document import (
    Document, PageLayout, Region, RegionType, 
    TextRegion, TableRegion, FormulaRegion, ImageRegion
)


class MarkdownGenerator:
    """Markdown生成器
    
    负责将解析后的文档结构转换为Markdown格式文本，
    支持多种文档类型和自定义格式配置。
    """
    
    def __init__(self, config: MarkdownGeneratorConfig):
        """初始化Markdown生成器
        
        Args:
            config: Markdown生成器配置对象
        """
        self.config = config
        logger.info("Markdown生成器初始化完成")
    
    def generate(self, document: Document) -> str:
        """生成Markdown文档
        
        采用Pipeline模式，按顺序处理文档的各个部分：
        1. 逐页内容生成
        2. 格式化和优化
        
        Args:
            document: 解析后的文档对象
            
        Returns:
            str: Markdown格式的文档内容
        """
        try:
            logger.info("开始生成Markdown文档")
            
            markdown_parts = []
            
            # 不再生成文档头部信息
            
            # 逐页生成内容
            for page in document.pages:
                page_content = self._generate_page_content(page)
                if page_content:
                    markdown_parts.append(page_content)
            
            # 合并所有部分
            line_break = "\n\n" if self.config.line_break_style == "double" else "\n"
            markdown_content = line_break.join(markdown_parts)
            
            # 后处理优化
            markdown_content = self._post_process_markdown(markdown_content)
            
            logger.info("Markdown文档生成完成")
            return markdown_content
            
        except Exception as e:
            logger.error(f"Markdown生成失败: {str(e)}")
            return ""
    
    def _generate_header(self, document: Document) -> str:
        """生成文档头部信息
        
        包含文档标题、元数据和统计信息
        
        Args:
            document: 文档对象
            
        Returns:
            str: 格式化的头部内容
        """
        header_parts = []
        
        try:
            # 文档标题
            source_name = document.source_path.stem
            header_parts.append(f"# {source_name}")
            header_parts.append("")
            
            # 元数据表格
            if document.metadata:
                header_parts.append("## 文档信息")
                header_parts.append("")
                
                # 使用表格格式展示元数据
                header_parts.append("| 属性 | 值 |")
                header_parts.append("|------|-----|")
                
                for key, value in document.metadata.items():
                    if key and value is not None:
                        # 清理值中的特殊字符
                        clean_value = str(value).replace("|", "\\|").replace("\n", " ")
                        header_parts.append(f"| {key} | {clean_value} |")
                
                header_parts.append("")
            
            # 统计信息
            header_parts.append("## 文档统计")
            header_parts.append("")
            header_parts.append(f"- **页数**: {document.page_count}")
            header_parts.append(f"- **总区域数**: {document.total_regions}")
            
            # 按类型统计区域
            region_stats = self._calculate_region_statistics(document)
            for region_type, count in region_stats.items():
                header_parts.append(f"- **{region_type}**: {count}个")
            
            if document.processing_time:
                header_parts.append(f"- **处理时间**: {document.processing_time:.2f}秒")
            
            header_parts.append("")
            header_parts.append("---")
            header_parts.append("")
            
            return "\n".join(header_parts)
            
        except Exception as e:
            logger.error(f"头部信息生成失败: {str(e)}")
            return ""
    
    def _calculate_region_statistics(self, document: Document) -> Dict[str, int]:
        """计算区域类型统计，排除图片区域"""
        stats = {}
        
        try:
            for page in document.pages:
                for region in page.regions:
                    # 排除图片区域
                    if region.region_type != RegionType.IMAGE:
                        region_name = region.region_type.value
                        stats[region_name] = stats.get(region_name, 0) + 1
        except Exception as e:
            logger.error(f"区域统计计算失败: {str(e)}")
        
        return stats
    
    def _generate_page_content(self, page: PageLayout) -> str:
        """生成页面内容，直接处理每个区域，不进行合并"""
        try:
            content_parts = []
            
            # 移除页面标题，直接生成内容
            # 过滤掉图片区域，只处理非图片区域
            non_image_regions = [r for r in page.regions if r.region_type != RegionType.IMAGE]
            logger.debug(f"页面 {page.page_number + 1}: 总区域 {len(page.regions)}，非图片区域 {len(non_image_regions)}")
            
            # 按阅读顺序处理非图片区域，不进行合并
            sorted_regions = sorted(non_image_regions, key=lambda r: r.reading_order)
            
            for region in sorted_regions:
                region_content = self._generate_region_content(region)
                if region_content.strip():  # 只添加非空内容
                    content_parts.append(region_content)
            
            return "\n\n".join(content_parts)  # 使用双换行符分隔区域
            
        except Exception as e:
            logger.error(f"页面内容生成失败: {str(e)}")
            return ""
    
    def _generate_region_content(self, region: Region) -> str:
        """生成区域内容，只有TITLE类型生成标题格式，其他都生成文本格式"""
        try:
            # 跳过图片区域和标题占位符，不生成任何内容
            if region.region_type == RegionType.IMAGE:
                logger.debug(f"跳过图片区域: {region.bbox}")
                return ""
            
            # 跳过FIGURE类型的区域（图片）
            if region.region_type == RegionType.FIGURE:
                logger.debug(f"跳过图片区域: {region.bbox}")
                return ""
            
            # 跳过所有占位符内容（以[开头且以]结尾的内容）
            if hasattr(region, 'content') and region.content:
                content = region.content.strip()
                if content.startswith('[') and content.endswith(']'):
                    logger.debug(f"跳过占位符内容: {content}")
                    return ""
                
                # 跳过常见的占位符模式
                placeholder_patterns = [
                    r'^\[Figure\]$',
                    r'^\[FigureCaption\]$',
                    r'^\[Table\]$',
                    r'^\[TableCaption\]$',
                    r'^\[Formula\]$',
                    r'^\[FormulaCaption\]$',
                    r'^\[Image\]$',
                    r'^\[Caption\]$',
                    r'^\[Abandon\]$'
                ]
                
                for pattern in placeholder_patterns:
                    if re.match(pattern, content):
                        logger.debug(f"跳过占位符内容: {content}")
                        return ""
            
            # 只有TITLE类型才生成标题格式
            if region.region_type == RegionType.TITLE:
                return self._generate_title_content(region)
            # 表格类型特殊处理
            elif region.region_type == RegionType.TABLE:
                return self._generate_table_content(region)
            # 公式类型特殊处理
            elif region.region_type == RegionType.FORMULA:
                return self._generate_formula_content(region)
            # 其他所有类型（TEXT、HEADER、FOOTER、CAPTION等）都作为普通文本处理
            else:
                return self._generate_text_content(region)
                
        except Exception as e:
            logger.error(f"区域内容生成失败: {str(e)}")
            return ""
    
    def _generate_text_content(self, region) -> str:
        """生成文本内容
        
        对于Text类型的区域，生成普通段落文本，不添加标题标记
        
        Args:
            region: 文本区域对象（可能是TextRegion或普通Region）
            
        Returns:
            str: 格式化的文本内容
        """
        content_parts = []
        
        try:
            # 如果是TextRegion且有text_content
            if hasattr(region, 'text_content') and region.text_content:
                for text_data in region.text_content:
                    # TextElement对象有text属性，不是content属性
                    text_content = getattr(text_data, 'text', None) or getattr(text_data, 'content', None)
                    if not text_content:
                        continue
                    
                    # 清理和格式化文本
                    cleaned_text = self._clean_text(text_content)
                    
                    # 对于Text类型区域，直接添加为普通文本，不判断标题
                    if cleaned_text.strip():
                        content_parts.append(cleaned_text.strip())
            
            # 如果是普通Region且有content
            elif hasattr(region, 'content') and region.content:
                # 跳过占位符内容
                if region.content.strip().startswith('[') and region.content.strip().endswith(']'):
                    return ""
                
                cleaned_text = self._clean_text(region.content)
                if cleaned_text.strip():
                    content_parts.append(cleaned_text.strip())
            
            # 返回合并的文本，直接连接不添加空格
            return "".join(content_parts) if content_parts else ""
            
        except Exception as e:
            logger.error(f"文本内容生成失败: {str(e)}")
            return ""
    
    def _generate_title_content(self, region) -> str:
        """生成标题内容
        
        专门处理TITLE类型的区域，将同一个Title区域的所有文字直接合并为一个标题
        此方法只会被TITLE类型的区域调用，无需类型检查
        
        Args:
            region: 标题区域对象（调用前已确保是TITLE类型）
            
        Returns:
            str: 格式化的标题内容
        """
        try:
            text_parts = []
            title_level = 2  # 默认标题级别
            first_text_for_level = True
            
            # 如果是TextRegion且有text_content
            if hasattr(region, 'text_content') and region.text_content:
                for text_data in region.text_content:
                    # TextElement对象有text属性，不是content属性
                    text_content = getattr(text_data, 'text', None) or getattr(text_data, 'content', None)
                    if not text_content:
                        continue
                    
                    # 清理文本并收集
                    cleaned_text = self._clean_text(text_content)
                    if cleaned_text.strip():
                        text_parts.append(cleaned_text.strip())
                    
                    # 使用第一个有效文本的字体大小确定标题级别
                    if first_text_for_level and cleaned_text.strip():
                        title_level = self._determine_title_level(text_data)
                        first_text_for_level = False
            
            # 如果是普通Region且有content
            elif hasattr(region, 'content') and region.content:
                # 跳过占位符内容
                if region.content.strip().startswith('[') and region.content.strip().endswith(']'):
                    return ""
                
                cleaned_text = self._clean_text(region.content)
                if cleaned_text.strip():
                    text_parts.append(cleaned_text.strip())
                # 使用字体大小判断标题级别
                title_level = self._determine_title_level(region)
            
            # 将所有文本合并为一个标题
            if text_parts:
                # 直接合并所有文本，不添加空格
                merged_title = "".join(text_parts)
                # 去除多余的空格和换行符
                merged_title = re.sub(r'\s+', ' ', merged_title).strip()
                return f"{'#' * title_level} {merged_title}"
            
            return ""
            
        except Exception as e:
            logger.error(f"标题内容生成失败: {str(e)}")
            return ""
    

    def _generate_table_content(self, table_region) -> str:
        """生成表格内容
        
        支持Markdown和HTML两种表格格式
        
        Args:
            table_region: 表格区域对象（应该是TableRegion对象）
            
        Returns:
            str: 格式化的表格内容
        """
        content_parts = []
        
        try:
            # 首先检查是否是TableRegion对象且有table_content属性
            if hasattr(table_region, 'table_content') and table_region.table_content:
                logger.debug(f"处理TableRegion对象，包含 {len(table_region.table_content)} 个表格")
                
                for i, table_data in enumerate(table_region.table_content):
                    if i > 0:
                        content_parts.append("")  # 多个表格间空行
                    
                    # 直接生成表格内容，不添加表格标题
                    if self.config.table_format == "markdown":
                        table_md = self._generate_markdown_table(table_data)
                        if table_md.strip():  # 只有当表格有内容时才添加
                            content_parts.append(table_md)
                    else:
                        # HTML格式
                        table_html = self._generate_html_table(table_data)
                        if table_html.strip():
                            content_parts.append(table_html)
                
                if content_parts:
                    return "\n".join(content_parts)
            
            # 如果没有table_content属性或为空，检查是否有已转换的Markdown格式内容
            elif hasattr(table_region, 'content') and table_region.content:
                logger.debug("使用已转换的表格Markdown内容")
                return table_region.content
            
            # 最后回退到文本内容生成
            else:
                logger.warning(f"表格区域缺少table_content和content属性，回退到文本内容生成")
                return self._generate_text_content(table_region)
                
        except Exception as e:
            logger.error(f"表格内容生成失败: {str(e)}")
            # 尝试回退到文本内容
            try:
                return self._generate_text_content(table_region)
            except:
                logger.warning(f"表格内容解析完全失败: {str(e)}")
                return ""
        
        return ""
    
    def _generate_formula_content(self, formula_region: FormulaRegion) -> str:
        """增强公式处理"""
        if not formula_region.formula_content:
            return ""

        content_parts = []
        formula_count = 0

        for formula in formula_region.formula_content:
            # 新增公式有效性检查
            if not hasattr(formula, 'latex') or not formula.latex.strip():
                continue

            latex = formula.latex.strip()
            
            # 公式标准化处理
            latex = re.sub(r'\s+', ' ', latex)  # 压缩空白
            latex = latex.replace('\\ ', '\\')  # 修复常见转义

            # 根据配置生成不同格式
            if self.config.formula_format == "latex":
                content_parts.append(f"$$\n{latex}\n$$")
            else:
                # 新增编号和引用支持
                formula_count += 1
                content_parts.append(f"**公式({formula_count})**: \n```latex\n{latex}\n```")

            # 新增公式描述支持
            if hasattr(formula, 'description') and formula.description:
                content_parts.append(f"*{formula.description}*")

        return "\n\n".join(content_parts) if content_parts else ""

    def _post_process_markdown(self, content: str) -> str:
        """增强的Markdown后处理"""
        if not content:
            return ""

        # 分阶段处理
        content = self._normalize_line_breaks(content)
        content = self._fix_table_formatting(content)
        content = self._adjust_headings(content)
        return content.strip()

    def _normalize_line_breaks(self, content: str) -> str:
        """标准化换行"""
        # 保留表格内的单换行，其他情况双换行
        lines = content.split('\n')
        result = []
        in_table = False

        for line in lines:
            is_table_line = '|' in line and '-' not in line
            
            if is_table_line:
                in_table = True
                result.append(line)
            elif in_table and not line.strip():
                continue  # 跳过表格内的空行
            else:
                in_table = False
                result.append(line)

        # 合并多余空行
        return re.sub(r'\n{3,}', '\n\n', '\n'.join(result))

    def _fix_table_formatting(self, content: str) -> str:
        """修复表格格式"""
        # 不再自动添加表格前后的空行，保持原始格式
        return content

    def _adjust_headings(self, content: str) -> str:
        """调整标题格式"""
        # 确保标题前后有空行
        content = re.sub(r'(#+\s.*?)\n([^#\n])', r'\1\n\n\2', content)
        return re.sub(r'([^\n#])\n(#+\s)', r'\1\n\n\2', content)

    def save_to_file(self, markdown_content: str, output_path: Path) -> None:
        """保存Markdown内容到文件
        
        Args:
            markdown_content: Markdown内容
            output_path: 输出文件路径
        """
        try:
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"Markdown文件已保存到: {output_path}")
            
        except Exception as e:
            logger.error(f"保存Markdown文件失败: {str(e)}")
            raise
    
    def batch_generate(self, documents: List[Document]) -> List[str]:
        """批量生成Markdown文档
        
        支持批量处理多个文档，提高处理效率
        
        Args:
            documents: 文档对象列表
            
        Returns:
            List[str]: Markdown内容列表
        """
        results = []
        
        try:
            for i, document in enumerate(documents):
                logger.info(f"生成第 {i+1}/{len(documents)} 个文档")
                markdown = self.generate(document)
                results.append(markdown)
            
            logger.info(f"批量生成完成，共处理 {len(documents)} 个文档")
            return results
            
        except Exception as e:
            logger.error(f"批量生成失败: {str(e)}")
            return results
    
    def _generate_markdown_table(self, table_data) -> str:
        """增强版Markdown表格生成，彻底去除全空行（最终再过滤一遍）"""
        if not hasattr(table_data, 'headers') and not hasattr(table_data, 'rows'):
            return ""

        def is_valid_table(headers, rows):
            if not any(any(str(cell).strip() for cell in row) for row in rows):
                return False
            return bool(headers or rows)

        headers = getattr(table_data, 'headers', [])
        rows = getattr(table_data, 'rows', [])
        
        if not is_valid_table(headers, rows):
            return ""

        align_map = {
            'left': ':---',
            'center': ':---:',
            'right': '---:'
        }
        
        def clean_cell(cell):
            content = str(cell).strip()
            content = re.sub(r'\s+', ' ', content)
            content = content.replace('|', '\\|')
            return content or " "

        table_lines = []
        if headers:
            cleaned_headers = [clean_cell(h) for h in headers]
            table_lines.append(f"| {' | '.join(cleaned_headers)} |")
            alignments = getattr(table_data, 'alignments', ['left']*len(headers))
            separators = [align_map.get(align.lower(), '---') for align in alignments]
            table_lines.append(f"| {' | '.join(separators)} |")

        for row in rows:
            if not any(str(cell).strip() for cell in row):
                continue
            padded_row = list(row) + [""] * (len(headers) - len(row))
            cleaned_row = [clean_cell(cell) for cell in padded_row]
            table_lines.append(f"| {' | '.join(cleaned_row)} |")

        # 最后再过滤一遍全空行
        filtered_lines = [line for line in table_lines if any(cell.strip() for cell in line.strip('|').split('|'))]
        return "\n".join(filtered_lines) if filtered_lines else ""

    def _clean_text(self, text: str) -> str:
        """
        文本清洗：去除多余空白、特殊不可见字符，保留必要格式。

        Args:
            text (str): 原始文本

        Returns:
            str: 清洗后的文本
        """
        if not isinstance(text, str):
            return ""
        # 去除不可见字符和多余空白
        cleaned = text.replace('\u200b', '').replace('\ufeff', '')
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip()
    
    def _determine_title_level(self, text_data) -> int:
        """
        根据字体大小智能判断标题级别，适配不同类型的输入对象。
        支持从配置文件读取阈值。

        Args:
            text_data: 文本数据对象，可能是TextData、Region或其他包含font_size的对象

        Returns:
            int: 标题级别（1~6，1为最高级标题）
        """
        try:
            # 尝试从不同属性获取字体大小
            font_size = None
            
            # 优先尝试获取font_size属性
            if hasattr(text_data, 'font_size') and text_data.font_size is not None:
                font_size = text_data.font_size
            # 备选：尝试avg_line_height
            elif hasattr(text_data, 'avg_line_height') and text_data.avg_line_height is not None:
                font_size = text_data.avg_line_height+3
            # 备选：尝试height属性（可能是bbox相关）
            elif hasattr(text_data, 'height') and text_data.height is not None:
                font_size = text_data.height
            
            # 根据字体大小判断标题级别
            if font_size is not None:
                # 尝试从配置读取阈值，否则使用默认值
                thresholds = getattr(self.config, 'title_level_thresholds', {})
                level_1_threshold = thresholds.get('level_1', 18)
                level_2_threshold = thresholds.get('level_2', 16)
                level_3_threshold = thresholds.get('level_3', 14)
                level_4_threshold = thresholds.get('level_4', 12)
                level_5_threshold = thresholds.get('level_5', 10)
                
                if font_size >= level_1_threshold:      # 特大标题
                    return 1
                elif font_size >= level_2_threshold:    # 大标题
                    return 2
                elif font_size >= level_3_threshold:    # 中等标题
                    return 3
                elif font_size >= level_4_threshold:    # 小标题
                    return 4
                elif font_size >= level_5_threshold:    # 更小标题
                    return 5
                else:                                   # 最小标题
                    return 6
            
            # 如果没有字体大小信息，尝试根据置信度调整
            confidence = getattr(text_data, 'confidence', 1.0)
            if confidence >= 0.9:
                return 2  # 高置信度，可能是重要标题
            elif confidence >= 0.7:
                return 3  # 中等置信度
            else:
                return 4  # 低置信度，降低标题级别
            
        except Exception as e:
            logger.debug(f"标题级别判断失败: {str(e)}")
            return 3  # 默认返回三级标题
