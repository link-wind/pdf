"""Markdown生成模块
将解析后的文档内容转换为Markdown格式
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import re
import os

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

# LLM辅助函数的导入
from ..utils.llm_aided import llm_aided_title

def count_leading_hashes(text: str) -> int:
    """统计文本开头的#号数量"""
    if not text:
        return 0
    count = 0
    for char in text.strip():
        if char == '#':
            count += 1
        else:
            break
    return count

def strip_leading_hashes(text: str) -> str:
    """去除文本开头的#号"""
    if not text:
        return text
    stripped = text.strip()
    while stripped.startswith('#'):
        stripped = stripped[1:]
    return stripped.strip()

def get_title_level(block) -> int:
    """获取标题级别并进行规范化"""
    # 如果传入的是字符串，先统计#号数量
    if isinstance(block, str):
        title_level = count_leading_hashes(block)
    else:
        # 如果是block对象，获取level属性
        title_level = block.get('level', 1) if hasattr(block, 'get') else getattr(block, 'level', 1)
    
    # 规范化标题级别
    if title_level > 4:  # 最大4级标题
        title_level = 4
    elif title_level < 1:
        title_level = 0  # 0表示非标题
    
    return title_level

def fix_title_blocks(blocks):
    """修复标题块"""
    for block in blocks:
        if block.get("type") == "TITLE":
            title_content = ' '.join([span.get('content', '') for line in block.get('lines', []) for span in line.get('spans', [])])
            title_level = count_leading_hashes(title_content)
            
            # 使用get_title_level进行规范化
            block['level'] = get_title_level({'level': title_level})
            
            # 清理标题内容，去除#号
            if 'lines' in block:
                for line in block['lines']:
                    if 'spans' in line:
                        for span in line['spans']:
                            if 'content' in span:
                                span['content'] = strip_leading_hashes(span['content'])
                            break
                        break
    return blocks



class MarkdownGenerator:
    """Markdown生成器
    
    负责将解析后的文档结构转换为Markdown格式文本，
    支持多种文档类型和自定义格式配置。
    """
    
    def __init__(self, config: MarkdownGeneratorConfig = None, llm_config = None):
        """初始化Markdown生成器
        
        Args:
            config: Markdown生成器配置对象
            llm_config: LLM配置对象或字典，用于标题优化
        """
        self.config = config or MarkdownGeneratorConfig()
        
        # 处理LLM配置
        if llm_config is None:
            self.llm_config = {}
        elif hasattr(llm_config, '__dict__'):  # 如果是配置对象
            self.llm_config = {
                'api_key': getattr(llm_config, 'api_key', ''),
                'base_url': getattr(llm_config, 'base_url', 'https://api.deepseek.com'),
                'model': getattr(llm_config, 'model', 'deepseek-chat'),
                'temperature': getattr(llm_config, 'temperature', 0.7),
                'max_tokens': getattr(llm_config, 'max_tokens', 4096),
                'timeout': getattr(llm_config, 'timeout', 30),
                'max_retries': getattr(llm_config, 'max_retries', 3),
                'enabled': getattr(llm_config, 'enabled', False),
                'provider': getattr(llm_config, 'provider', 'deepseek')
            }
        else:  # 如果是字典
            self.llm_config = llm_config
        
        logger.info("Markdown生成器初始化完成")
    
    def generate(self, document: Document) -> str:
        """生成Markdown文档
        
        采用Pipeline模式，按顺序处理文档的各个部分：
        1. 逐页内容生成
        2. 标题优化处理
        3. 格式化和优化
        
        Args:
            document: 解析后的文档对象
            
        Returns:
            str: Markdown格式的文档内容
        """
        try:
            logger.info("开始生成Markdown文档")
            
            # 首先优化文档标题
            document = self.optimize_document_titles(document)
            
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
    

    
    def _generate_page_content(self, page: PageLayout) -> str:
        """生成页面内容，直接处理每个区域，不进行合并"""
        try:
            content_parts = []
            
            # 移除页面标题，直接生成内容
            # 过滤掉图片区域，只处理非图片区域
            non_image_regions = [r for r in page.regions if r.region_type != RegionType.FIGURE]
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
        """生成区域内容"""
        try:
            # 跳过图片区域
            if region.region_type == RegionType.FIGURE:
                return ""
            
            # 跳过占位符内容
            if hasattr(region, 'content') and region.content:
                content = region.content.strip()
                if content.startswith('[') and content.endswith(']'):
                    return ""
            
            # 根据区域类型生成内容
            if region.region_type == RegionType.TITLE:
                return self._generate_title_content(region)
            elif region.region_type == RegionType.TABLE:
                return self._generate_table_content(region)
            elif region.region_type == RegionType.ISOLATE_FORMULA:
                return self._generate_formula_content(region)
            else:
                return self._generate_text_content(region)
                
        except Exception as e:
            logger.error(f"区域内容生成失败: {str(e)}")
            return ""
    
    def _generate_text_content(self, region) -> str:
        """生成文本内容"""
        try:
            # 处理TextRegion
            if hasattr(region, 'text_content') and region.text_content:
                text_parts = []
                for text_data in region.text_content:
                    text_content = getattr(text_data, 'text', None) or getattr(text_data, 'content', None)
                    if text_content:
                        cleaned_text = self._clean_text(text_content)
                        if cleaned_text.strip():
                            text_parts.append(cleaned_text.strip())
                return "".join(text_parts)
            
            # 处理普通Region
            elif hasattr(region, 'content') and region.content:
                if region.content.strip().startswith('[') and region.content.strip().endswith(']'):
                    return ""
                cleaned_text = self._clean_text(region.content)
                return cleaned_text.strip() if cleaned_text.strip() else ""
            
            return ""
            
        except Exception as e:
            logger.error(f"文本内容生成失败: {str(e)}")
            return ""
    
    def _generate_title_content(self, region) -> str:
        """生成标题内容"""
        try:
            text_parts = []
            title_level = 1
            
            # 提取文本内容
            if hasattr(region, 'text_content') and region.text_content:
                for text_data in region.text_content:
                    text_content = getattr(text_data, 'text', None) or getattr(text_data, 'content', None)
                    if text_content:
                        cleaned_text = self._clean_text(text_content)
                        if cleaned_text.strip():
                            text_parts.append(cleaned_text.strip())
            elif hasattr(region, 'content') and region.content:
                if region.content.strip().startswith('[') and region.content.strip().endswith(']'):
                    return ""
                cleaned_text = self._clean_text(region.content)
                if cleaned_text.strip():
                    text_parts.append(cleaned_text.strip())
            
            # 确定标题级别
            if hasattr(region, 'title_level') and region.title_level:
                title_level = get_title_level({'level': region.title_level})
            elif hasattr(region, 'level') and region.level:
                title_level = get_title_level({'level': region.level})
            else:
                title_level = get_title_level({'level': title_level})
            
            # 生成标题
            if text_parts:
                merged_title = "".join(text_parts)
                merged_title = re.sub(r'\s+', ' ', merged_title).strip()
                return f"{'#' * title_level} {merged_title}"
            
            return ""
            
        except Exception as e:
            logger.error(f"标题内容生成失败: {str(e)}")
            return ""
    
    def optimize_document_titles(self, document: Document) -> Document:
        """
        四步标题优化流程：
        1. 格式解析：基于Markdown格式的#号数量确定初始级别
        2. 智能优化：使用LLM根据上下文和视觉特征优化标题层级
        3. 规范化输出：确保标题级别在合理范围内（1-4级）
        4. 结构化输出：在最终的Markdown中正确格式化标题
        
        Args:
            document: 文档对象
            
        Returns:
            Document: 优化后的文档对象
        """
        try:
            logger.info("开始四步标题优化流程")
            
            # 第一步：格式解析 - 基于Markdown格式的#号数量确定初始级别
            title_regions = self._parse_title_formats(document)
            if not title_regions:
                logger.info("未发现标题区域，跳过标题优化")
                return document
            
            logger.info(f"第一步完成：解析到 {len(title_regions)} 个标题")
            
            # 第二步：智能优化 - 使用LLM根据上下文和视觉特征优化标题层级
            if self._should_use_llm_optimization(document):
                logger.info("第二步：开始LLM智能优化")
                self._apply_llm_title_optimization(title_regions)
                logger.info("第二步完成：LLM智能优化完成")
            else:
                logger.info("第二步：使用传统方法优化标题")
                self._apply_traditional_title_optimization(document)
                logger.info("第二步完成：传统方法优化完成")
            
            # 第三步：规范化输出 - 确保标题级别在合理范围内（1-4级）
            self._normalize_title_levels(document)
            logger.info("第三步完成：标题级别规范化完成")
            
            # 第四步：结构化输出 - 确保标题层级的连续性和合理性
            self._structure_title_hierarchy(document)
            logger.info("第四步完成：标题层级结构化完成")
            
            logger.info("四步标题优化流程完成")
            return document
            
        except Exception as e:
            logger.error(f"标题优化流程失败: {str(e)}")
            return document
    
    def _parse_title_formats(self, document: Document) -> list:
        """
        第一步：格式解析 - 基于Markdown格式的#号数量确定初始级别
        
        Args:
            document: 文档对象
            
        Returns:
            list: 标题区域列表
        """
        title_regions = []
        
        try:
            for page in document.pages:
                for region in page.regions:
                    if region.region_type == RegionType.TITLE:
                        # 获取文本内容，支持多种region类型
                        text_content = ''
                        
                        # 如果是TextRegion且有text_content
                        if hasattr(region, 'text_content') and region.text_content:
                            text_parts = []
                            for text_data in region.text_content:
                                text = getattr(text_data, 'text', None) or getattr(text_data, 'content', None)
                                if text:
                                    text_parts.append(text.strip())
                            text_content = ' '.join(text_parts)
                        
                        # 如果是普通Region
                        if not text_content:
                            text_content = getattr(region, 'text', '') or getattr(region, 'content', '')
                        
                        if text_content:
                            # 检查是否包含Markdown标题标记
                            hash_count = count_leading_hashes(text_content)
                            
                            if hash_count > 0:
                                # 基于#号数量设置初始级别
                                region.title_level = hash_count
                                # 清理内容，去除#号
                                region.clean_text = strip_leading_hashes(text_content)
                                logger.debug(f"解析标题格式: #{hash_count} {region.clean_text}")
                            else:
                                # 没有#号的标题，设置默认级别
                                region.title_level = 1  # 默认为一级标题
                                region.clean_text = text_content.strip()
                                logger.debug(f"无格式标题，设为默认级别: {region.clean_text}")
                            
                            title_regions.append(region)
                        
        except Exception as e:
            logger.error(f"标题格式解析失败: {str(e)}")
        
        return title_regions
    
    def _apply_traditional_title_optimization(self, document: Document) -> None:
        """
        传统方法优化标题（当LLM不可用时的备选方案）
        使用fix_title_blocks逻辑
        
        Args:
            document: 文档对象
        """
        try:
            # 构建blocks结构
            blocks = []
            
            for page in document.pages:
                for region in page.regions:
                    if region.region_type == RegionType.TITLE:
                        block = {
                            "type": "TITLE",
                            "region": region,
                            "lines": [{
                                "spans": [{
                                    "content": getattr(region, 'clean_text', '') or getattr(region, 'text', '') or getattr(region, 'content', '')
                                }]
                            }]
                        }
                        blocks.append(block)
            
            # 应用fix_title_blocks逻辑
            optimized_blocks = fix_title_blocks(blocks)
            
            # 将结果应用回region
            for block in optimized_blocks:
                if 'region' in block and 'level' in block:
                    region = block['region']
                    region.title_level = block['level']
                    
        except Exception as e:
            logger.error(f"传统标题优化失败: {str(e)}")
    
    def _normalize_title_levels(self, document: Document) -> None:
        """
        第三步：规范化输出 - 确保标题级别在合理范围内（1-4级）
        
        Args:
            document: 文档对象
        """
        try:
            for page in document.pages:
                for region in page.regions:
                    if region.region_type == RegionType.TITLE and hasattr(region, 'title_level'):
                        # 使用get_title_level函数进行规范化
                        normalized_level = get_title_level({'level': region.title_level})
                        region.title_level = normalized_level
                        
                        logger.debug(f"标题级别规范化: {region.title_level} -> {normalized_level}")
                        
        except Exception as e:
            logger.error(f"标题级别规范化失败: {str(e)}")
    
    def _structure_title_hierarchy(self, document: Document) -> None:
        """
        第四步：结构化输出 - 确保标题层级的连续性和合理性
        
        Args:
            document: 文档对象
        """
        try:
            # 收集所有标题
            all_titles = []
            for page in document.pages:
                for region in page.regions:
                    if region.region_type == RegionType.TITLE and hasattr(region, 'title_level'):
                        all_titles.append(region)
            
            if not all_titles:
                return
            
            # 确保层级连续性
            prev_level = 0
            for region in all_titles:
                current_level = region.title_level
                
                # 如果跳级太大，调整为连续级别
                if current_level > prev_level + 1:
                    region.title_level = prev_level + 1
                    logger.debug(f"调整跳级标题: {current_level} -> {region.title_level}")
                
                prev_level = region.title_level
                
                # 确保不超过4级
                if region.title_level > 4:
                    region.title_level = 4
                    logger.debug(f"限制标题级别为4级: {region.title_level}")
                
        except Exception as e:
            logger.error(f"标题层级结构化失败: {str(e)}")
    
    def _apply_llm_title_optimization(self, title_regions: list) -> None:
        """
        第二步：智能优化 - 使用LLM根据上下文和视觉特征优化标题层级
        
        Args:
            title_regions: 标题区域列表
        """
        try:
            if not title_regions:
                logger.debug("没有标题区域需要LLM优化")
                return
            
            # 构建page_info_list结构
            page_info_list = []
            page_regions_map = {}  # 用于映射页面和区域
            
            # 简化页面信息构建逻辑
            page_info = {
                "page_id": "default_page",
                "page_width": 800,  # 默认页面宽度
                "page_height": 1200,  # 默认页面高度
                "regions": []
            }
            page_info_list.append(page_info)
            
            # 为每个标题区域构建信息
            for region in title_regions:
                region_info = {
                    "region_id": getattr(region, 'region_id', id(region)),
                    "bbox": getattr(region, 'bbox', [0, 0, 0, 0]),
                    "text": getattr(region, 'clean_text', '') or getattr(region, 'text', '') or getattr(region, 'content', ''),
                    "region_type": "title",
                    "avg_line_height": self._calculate_region_height(region),
                    "initial_level": getattr(region, 'title_level', 1)
                }
                page_info["regions"].append(region_info)
            
            if not page_info_list:
                logger.debug("没有找到有效的页面信息，跳过LLM优化")
                return
            
            # 调用LLM辅助标题优化
            logger.info(f"开始LLM辅助标题优化，处理{len(title_regions)}个标题")
            optimized_result = llm_aided_title(
                page_info_list=page_info_list,
                llm_config=self.llm_config
            )
            
            if optimized_result and 'pages' in optimized_result:
                # 将LLM返回的优化级别应用回标题区域
                region_level_map = {}
                
                for page_data in optimized_result['pages']:
                    for region_data in page_data.get('regions', []):
                        region_id = region_data.get('region_id')
                        optimized_level = region_data.get('level', 1)
                        region_level_map[region_id] = optimized_level
                
                # 更新标题区域的级别
                for region in title_regions:
                    region_id = getattr(region, 'region_id', id(region))
                    if region_id in region_level_map:
                        old_level = region.title_level
                        region.title_level = region_level_map[region_id]
                        logger.debug(f"LLM优化标题级别: {str(old_level)} -> {str(region.title_level)} ('{getattr(region, 'clean_text', '')}')")
                
                logger.info("LLM辅助标题优化完成")
            else:
                logger.warning("LLM优化返回结果为空，保持原有级别")
                
        except Exception as e:
            logger.error(f"LLM辅助标题优化失败: {str(e)}")
            # 发生错误时，保持原有级别，不影响后续处理
    
    def _should_use_llm_optimization(self, document: Document) -> bool:
        """判断是否应该使用LLM优化"""
        # 检查配置是否启用LLM标题优化
        if not getattr(self.config, 'enable_llm_title_optimization', False):
            return False
            
        # 检查LLM配置是否可用
        if not self.llm_config or not self.llm_config.get('enabled', False):
            return False
            
        # 检查API密钥是否配置
        if not self.llm_config.get('api_key'):
            return False
            
        # 检查标题数量是否达到阈值
        title_count = sum(1 for page in document.pages 
                         for region in page.regions 
                         if region.region_type == RegionType.TITLE)
        threshold = getattr(self.config, 'llm_title_threshold', 5)
        return title_count >= threshold
    
    def _calculate_region_height(self, region) -> float:
        """计算区域的平均行高"""
        if hasattr(region, 'bbox') and region.bbox:
            # 处理BoundingBox对象
            if hasattr(region.bbox, 'y2') and hasattr(region.bbox, 'y1'):
                return abs(region.bbox.y2 - region.bbox.y1)
            # 处理列表或元组格式的bbox
            elif isinstance(region.bbox, (list, tuple)) and len(region.bbox) >= 4:
                return abs(region.bbox[3] - region.bbox[1])
        return 20.0

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
                # 创建一个空的table_content属性以避免未来的错误
                if not hasattr(table_region, 'table_content'):
                    table_region.table_content = []
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
        """增强公式处理，确保公式能正确在Markdown中渲染"""
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
                # 使用双美元符号，确保整行居中显示
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
        """Markdown后处理"""
        if not content:
            return ""
        content = self._normalize_line_breaks(content)
        content = self._adjust_headings(content)
        return content.strip()
    


    def _normalize_line_breaks(self, content: str) -> str:
        """标准化换行"""
        content = re.sub(r'\n{3,}', '\n\n', content)
        return content.lstrip('\n')



    def _adjust_headings(self, content: str) -> str:
        """调整标题格式"""
        content = re.sub(r'(#+\s.*?)\n([^#\n])', r'\1\n\n\2', content)
        return re.sub(r'([^\n#])\n(#+\s)', r'\1\n\n\2', content)

    def save_to_file(self, content: str, output_path: str) -> bool:
        """保存Markdown内容到文件"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Markdown文件已保存到: {output_path}")
            return True
        except Exception as e:
            logger.error(f"保存Markdown文件失败: {str(e)}")
            return False
    

    
    def _generate_markdown_table(self, table_data) -> str:
        """生成Markdown格式的表格"""
        try:
            if isinstance(table_data, str):
                return table_data
            
            if hasattr(table_data, 'rows') and table_data.rows:
                rows = table_data.rows
                if rows:
                    header = "| " + " | ".join(str(cell) for cell in rows[0]) + " |"
                    separator = "| " + " | ".join("---" for _ in rows[0]) + " |"
                    body_rows = ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows[1:]]
                    return "\n".join([header, separator] + body_rows)
            
            return str(table_data)
        except Exception as e:
            logger.error(f"表格生成失败: {str(e)}")
            return str(table_data) if table_data else ""

    def _clean_text(self, text: str) -> str:
        """清理文本内容"""
        if not text:
            return ""
        try:
            return re.sub(r'\s+', ' ', text).strip()
        except Exception as e:
            logger.error(f"文本清理失败: {str(e)}")
            return text
