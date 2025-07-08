#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF处理主管道类
整合所有处理步骤，提供统一的处理接口

Author: PDF Pipeline Team
Date: 2024
"""

import os
import time
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger
from PIL import Image

from ..config.settings import Settings
from ..models.document import Document, Page, Region, PageLayout, BoundingBox, RegionType
from .pdf_converter import PDFConverter
from .layout_analyzer import LayoutAnalyzer
from .ocr_processor import OCRProcessor
from .table_parser import TableParser
from .formula_parser import FormulaParser
from .reading_order import ReadingOrderAnalyzer
from .md_generator import MarkdownGenerator


class PDFPipeline:
    """PDF处理主管道类"""
    
    def __init__(self, settings: Settings, output_dir: Optional[str] = None):
        """
        初始化PDF处理管道
        
        Args:
            settings: 配置对象
            output_dir: 输出目录路径
        """
        self.settings = settings
        self.output_dir = Path(output_dir) if output_dir else Path("./output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化处理器
        self.processors = {}
        self._init_processors()
        
        logger.info("PDF Pipeline 初始化完成")
    
    def _init_processors(self):
        """初始化各个处理器"""
        try:
            # 基础处理器（必需）
            self.processors['pdf_converter'] = PDFConverter(self.settings.pdf_converter)
            self.processors['layout_analyzer'] = LayoutAnalyzer(self.settings.layout_analyzer)
            self.processors['md_generator'] = MarkdownGenerator(self.settings.md_generator)
            
            # 可选处理器
            if getattr(self.settings.ocr_processor, 'enabled', True):
                self.processors['ocr_processor'] = OCRProcessor(self.settings.ocr_processor)
            
            if getattr(self.settings.table_parser, 'enabled', True):
                self.processors['table_parser'] = TableParser(self.settings.table_parser)
            
            if getattr(self.settings.formula_parser, 'enabled', True):
                self.processors['formula_parser'] = FormulaParser(self.settings.formula_parser)
            
            # 阅读顺序分析器
            self.processors['reading_order'] = ReadingOrderAnalyzer(self.settings.reading_order)
            
            logger.info(f"已初始化处理器: {list(self.processors.keys())}")
        except Exception as e:
            logger.error(f"处理器初始化失败: {str(e)}")
            raise
    
    def reload_layout_analyzer(self):
        """重新加载Layout Analyzer（用于场景切换后）"""
        try:
            logger.info("重新加载Layout Analyzer...")
            self.processors['layout_analyzer'] = LayoutAnalyzer(self.settings.layout_analyzer)
            logger.info("Layout Analyzer重新加载完成")
        except Exception as e:
            logger.error(f"Layout Analyzer重新加载失败: {str(e)}")
            raise

    def process(self, pdf_path: str, temp_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        处理PDF文件
        
        Args:
            pdf_path: PDF文件路径
            temp_dir: 临时目录路径
            
        Returns:
            Dict[str, Any]: 处理结果字典，包含success、document、markdown_content、statistics等
        """
        start_time = time.time()
        pdf_path = Path(pdf_path)
        
        # 设置临时目录
        if temp_dir:
            temp_dir = Path(temp_dir)
        else:
            temp_dir = self.output_dir / "temp" / pdf_path.stem
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"开始处理PDF: {pdf_path.name}")
        logger.info(f"临时目录: {temp_dir}")
        logger.info(f"当前配置: DocLayout模型")
        
        try:
            # 创建文档对象
            document = Document(
                source_path=pdf_path,
                metadata={
                    'model_type': 'doclayout',
                    'processing_start_time': start_time
                }
            )
            
            # 步骤1: PDF转图片
            logger.info("步骤1: PDF转图片...")
            images = self.processors['pdf_converter'].convert_pdf_to_images(pdf_path)
            # 保存图片到临时目录
            image_paths = self.processors['pdf_converter'].save_images(
                images, temp_dir, filename_prefix="page"
            )
            logger.info(f"转换完成，共 {len(images)} 页")
            
            # 步骤2: 版式分析
            logger.info("步骤2: 版式分析...")
            layout_results = []
            for i, image_path in enumerate(image_paths):
                logger.debug(f"分析第 {i+1}/{len(images)} 页...")
                # 版式分析 - 直接使用图片路径
                regions = self.processors['layout_analyzer'].analyze_layout(str(image_path), page_num=i)
                layout_results.append(regions)
                
                # 创建页面对象
                page = Page(page_number=i+1, image_path=str(image_path), regions=regions)
                document.pages.append(page)
            
            logger.info(f"版式分析完成，共检测到 {sum(len(r) for r in layout_results)} 个区域")
            
            # 步骤3: 多元素并行解析
            logger.info("步骤3: 多元素并行解析...")
            
            # 处理每一页
            for page in document.pages:
                logger.debug(f"处理第 {page.page_number} 页，共 {len(page.regions)} 个区域")
                
                for region in page.regions:
                    try:
                        # OCR处理
                        if ('ocr_processor' in self.processors and 
                            region.region_type in [RegionType.TEXT, RegionType.TITLE, RegionType.HEADER, RegionType.FOOTER]):
                            logger.debug(f"OCR处理区域: {region.region_type.value}")
                            # 创建TextRegion对象
                            from ..models.document import TextRegion
                            text_region = TextRegion(
                                region_type=region.region_type,
                                bbox=region.bbox,
                                confidence=region.confidence,
                                page_number=region.page_number,
                                reading_order=region.reading_order
                            )
                            # 加载页面图像
                            with Image.open(page.image_path) as page_img:
                                if page_img.mode != 'RGB':
                                    page_img = page_img.convert('RGB')
                                # 调用处理器
                                try:
                                    # 转换PIL图像为numpy数组
                                    image_array = np.array(page_img)
                                    result = self.processors['ocr_processor'].process_region(text_region, image_array)
                                    
                                    # 检查OCR结果
                                    if result and result.get('content') and len(result['content'].strip()) > 0:
                                        # 将OCR结果正确存储到TextRegion中
                                        text_region.text_content = result.get('text_blocks', [])
                                        # 同时为兼容性设置基类的content字段
                                        text_region.content = result.get('content', '')
                                        text_region.confidence = result.get('confidence', region.confidence)
                                        # 用更新后的TextRegion替换原region
                                        page.regions[page.regions.index(region)] = text_region
                                        logger.debug(f"OCR识别成功: {result['content'][:50]}...")
                                    else:
                                        logger.warning(f"OCR未识别到文本内容，跳过区域")
                                        text_region.content = ""
                                        text_region.text_content = []
                                        page.regions[page.regions.index(region)] = text_region
                                except Exception as e:
                                    logger.warning(f"OCR处理失败: {e}")
                                    text_region.content = ""
                                    text_region.text_content = []
                                    page.regions[page.regions.index(region)] = text_region
                        
                        # 表格解析
                        elif ('table_parser' in self.processors and 
                              region.region_type in [RegionType.TABLE]):
                            logger.debug("表格解析处理...")
                            # 创建TableRegion对象
                            from ..models.document import TableRegion
                            table_region = TableRegion(
                                region_type=region.region_type,
                                bbox=region.bbox,
                                confidence=region.confidence,
                                page_number=region.page_number,
                                reading_order=region.reading_order
                            )
                            # 复制原始内容
                            table_region.content = region.content
                            
                            # 添加页面图像信息
                            table_region.page_path = page.image_path
                            # 如果需要加载图像，使用PIL
                            try:
                                with Image.open(page.image_path) as page_img:
                                    table_region.page_image = page_img.copy()
                            except Exception as e:
                                logger.warning(f"加载页面图像失败: {e}")
                                table_region.page_image = None
                            
                            # 调用解析器
                            try:
                                table_data_list = self.processors['table_parser'].parse(table_region)
                                if table_data_list and len(table_data_list) > 0:
                                    # 将解析结果存储到TableRegion的table_content属性
                                    table_region.table_content = table_data_list
                                    
                                    # 同时生成Markdown格式的content作为备用
                                    table_data = table_data_list[0]
                                    if hasattr(table_data, 'headers') and hasattr(table_data, 'rows'):
                                        markdown_table = self._convert_table_to_markdown(table_data)
                                        table_region.content = markdown_table
                                        table_region.metadata = {
                                            'row_count': table_data.row_count,
                                            'col_count': table_data.col_count,
                                            'confidence': table_data.confidence,
                                            'caption': table_data.caption
                                        }
                                    else:
                                        # 兼容旧格式
                                        table_region.content = getattr(table_data, 'table_html', '') or getattr(table_data, 'table_text', '') or ''
                                        table_region.metadata = getattr(table_data, 'metadata', {})
                                else:
                                    table_region.table_content = []
                                    table_region.content = ""
                                    logger.warning(f"表格解析未识别到内容，跳过区域")
                                
                                # 替换原始region为TableRegion
                                page.regions[page.regions.index(region)] = table_region
                                
                            except Exception as e:
                                logger.warning(f"表格解析失败: {e}")
                                table_region.table_content = []
                                table_region.content = ""
                                # 即使解析失败也替换为TableRegion，保持类型一致性
                                page.regions[page.regions.index(region)] = table_region
                        
                        # 公式识别
                        elif ('formula_parser' in self.processors and 
                              region.region_type in [RegionType.EQUATION, RegionType.FORMULA]):
                            logger.debug("公式识别处理...")
                            # 创建FormulaRegion对象
                            from ..models.document import FormulaRegion
                            formula_region = FormulaRegion(
                                region_type=region.region_type,
                                bbox=region.bbox,
                                confidence=region.confidence,
                                page_number=region.page_number,
                                reading_order=region.reading_order
                            )
                            # 添加页面图像信息
                            formula_region.page_path = page.image_path
                            try:
                                with Image.open(page.image_path) as page_img:
                                    formula_region.page_image = page_img.copy()
                            except Exception as e:
                                logger.warning(f"加载页面图像失败: {e}")
                                formula_region.page_image = None
                            # 调用解析器
                            try:
                                formula_data_list = self.processors['formula_parser'].parse(formula_region)
                                if formula_data_list and len(formula_data_list) > 0:
                                    # 设置公式内容到formula_content字段
                                    formula_region.formula_content = formula_data_list
                                    # 使用第一个公式数据设置content作为fallback
                                    formula_data = formula_data_list[0]
                                    formula_region.content = formula_data.latex or formula_data.mathml or ''
                                    formula_region.metadata = {
                                        'confidence': formula_data.confidence,
                                        'latex': formula_data.latex,
                                        'mathml': formula_data.mathml
                                    }
                                    logger.info(f"公式解析成功，LaTeX: {formula_data.latex[:50] if formula_data.latex else 'None'}...")
                                    # 将解析后的FormulaRegion替换原有的region
                                    page.regions[page.regions.index(region)] = formula_region
                                else:
                                    formula_region.content = ""
                                    logger.warning(f"公式识别未识别到内容，跳过区域")
                                    page.regions[page.regions.index(region)] = formula_region
                            except Exception as e:
                                logger.warning(f"公式识别失败: {e}")
                                formula_region.content = ""
                                page.regions[page.regions.index(region)] = formula_region
                        
                    except Exception as e:
                        logger.warning(f"处理区域 {region.region_type.value} 时出错: {e}")
                        continue
            
            # 步骤4: 阅读顺序重构
            logger.info("步骤4: 阅读顺序重构...")
            try:
                # 保存原始Page对象的image_path信息
                original_image_paths = [page.image_path for page in document.pages]
                
                # 构建完整的PageLayout对象并统一调用阅读顺序分析
                # 为每页构建PageLayout对象
                page_layouts = []
                for i, page in enumerate(document.pages):
                    # 确保width和height有有效值
                    page_width = getattr(page, 'width', None) or 2550.0  # A4纸宽度的像素值
                    page_height = getattr(page, 'height', None) or 3300.0  # A4纸高度的像素值
                    
                    page_layout = PageLayout(
                        width=page_width,
                        height=page_height,
                        page_number=page.page_number
                    )
                    # 保存image_path到PageLayout对象
                    page_layout.image_path = page.image_path
                    
                    # 将regions添加到PageLayout中的相应列表
                    for region in page.regions:
                        if hasattr(region.region_type, 'value'):
                            region_type_str = region.region_type.value
                        else:
                            region_type_str = str(region.region_type)
                        
                        if region_type_str in ['Text', 'Title', 'Header', 'Footer']:
                            page_layout.text_regions.append(region)
                        elif region_type_str in ['Table']:
                            page_layout.table_regions.append(region)
                        elif region_type_str in ['Figure']:
                            page_layout.image_regions.append(region)
                        elif region_type_str in ['Equation', 'Formula']:
                            page_layout.formula_regions.append(region)
                        else:
                            page_layout.text_regions.append(region)  # 默认作为文本处理
                    
                    page_layouts.append(page_layout)
                
                # 更新Document对象的pages为PageLayout对象
                document.pages = page_layouts
                
                # 统一调用阅读顺序分析
                if self.processors['reading_order'].config.use_layoutreader:
                    logger.info("启用LayoutReader阅读顺序分析")
                else:
                    logger.info("使用空间排序进行阅读顺序分析")
                
                logger.info(f"深度学习栏分析: {self.processors['reading_order'].use_deep_learning_for_columns}")
                
                self.processors['reading_order'].analyze_reading_order(document)
                
                # 将结果同步回原始Page对象，确保image_path正确传递
                original_pages = []
                for i, page_layout in enumerate(document.pages):
                    # 创建新的Page对象，从PageLayout或原始保存的路径获取image_path
                    image_path = getattr(page_layout, 'image_path', '')
                    if not image_path and i < len(original_image_paths):
                        image_path = original_image_paths[i]
                    
                    page = Page(
                        page_number=page_layout.page_number,
                        image_path=image_path,
                        regions=page_layout.all_regions
                    )
                    page.width = page_layout.width
                    page.height = page_layout.height
                    original_pages.append(page)
                
                document.pages = original_pages
                
                logger.info(f"阅读顺序重构完成，共处理 {len(document.pages)} 页")
                
            except Exception as e:
                logger.error(f"阅读顺序重构失败: {e}")
                # 如果失败，至少按原有顺序编号
                for page in document.pages:
                    for i, region in enumerate(page.regions):
                        region.reading_order = i + 1
            
            # 步骤5: 生成Markdown
            logger.info("步骤5: 生成Markdown...")
            output_path = self.output_dir / f"{pdf_path.stem}.md"
            try:
                markdown_content = self.processors['md_generator'].generate(document)
                document.markdown_content = markdown_content
                
                # 保存Markdown文件
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                logger.info(f"Markdown文件已保存: {output_path}")
            except Exception as e:
                logger.error(f"Markdown生成失败: {e}")
                document.markdown_content = "# Markdown生成失败\n\n处理过程中出现错误。"
                # 仍然保存错误信息到文件
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(document.markdown_content)
            
            # 更新处理统计
            end_time = time.time()
            processing_time = end_time - start_time
            
            document.metadata.update({
                'processing_end_time': end_time,
                'processing_time': processing_time,
                'total_pages': len(document.pages),
                'total_regions': sum(len(page.regions) for page in document.pages),
                'model_type': 'doclayout'
            })
            
            logger.info(f"PDF处理完成，耗时: {processing_time:.2f}秒")
            logger.info(f"总页数: {document.metadata['total_pages']}")
            logger.info(f"总区域数: {document.metadata['total_regions']}")
            
            # 返回兼容Gradio前端的结果字典
            return {
                'success': True,
                'document': document,
                'markdown_content': document.markdown_content,
                'statistics': {
                    'processing_time': processing_time,
                    'total_pages': document.metadata['total_pages'],
                    'total_regions': document.metadata['total_regions'],
                    'model_type': document.metadata['model_type']
                },
                'output_path': str(output_path)
            }
            
        except Exception as e:
            logger.error(f"PDF处理失败: {str(e)}")
            # 返回失败结果
            return {
                'success': False,
                'error': str(e),
                'document': None,
                'markdown_content': '',
                'statistics': {}
            }
        finally:
            # 清理临时文件（可选）
            if hasattr(self, '_cleanup_temp') and self._cleanup_temp:
                try:
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    logger.debug(f"已清理临时目录: {temp_dir}")
                except Exception as e:
                    logger.warning(f"清理临时目录失败: {e}")
    
    def get_processor_status(self) -> Dict[str, bool]:
        """获取各个处理器的加载状态
        
        Returns:
            Dict[str, bool]: 处理器名称到加载状态的映射
        """
        return {name: True for name in self.processors.keys()}
    
    def get_model_info(self) -> str:
        """获取当前模型信息"""
        return "DocLayout YOLO模型"
    
    def _convert_table_to_markdown(self, table_data) -> str:
        """将TableData对象转换为Markdown表格格式
        
        Args:
            table_data: TableData对象
            
        Returns:
            str: Markdown格式的表格
        """
        try:
            if not table_data.headers and not table_data.rows:
                return "[空表格]"
            
            lines = []
            
            # 处理表头
            if table_data.headers:
                # 表头行
                header_row = "| " + " | ".join(str(h) for h in table_data.headers) + " |"
                lines.append(header_row)
                
                # 分隔符行
                separator = "| " + " | ".join("---" for _ in table_data.headers) + " |"
                lines.append(separator)
            
            # 处理数据行
            if table_data.rows:
                for row in table_data.rows:
                    # 确保行数据与表头数量一致
                    if table_data.headers:
                        padded_row = row[:len(table_data.headers)]
                        while len(padded_row) < len(table_data.headers):
                            padded_row.append("")
                    else:
                        padded_row = row
                    
                    row_str = "| " + " | ".join(str(cell) for cell in padded_row) + " |"
                    lines.append(row_str)
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"表格转换为Markdown失败: {e}")
            return ""
    

