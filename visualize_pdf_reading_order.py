#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF阅读顺序和版式分析可视化工具

将PDF文件的每一页转换为带有阅读顺序和版式分析标注的图片。

使用方法:
python visualize_pdf_reading_order.py <pdf_path> -o output/test
"""

import os
import sys
import time
import argparse
from pathlib import Path
import tempfile
import shutil

# 确保可以导入项目模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

try:
    from src import PDFPipeline, load_config
    from src.pipeline.pdf_converter import PDFConverter
    from src.pipeline.layout_analyzer import LayoutAnalyzer
    from src.pipeline.reading_order import ReadingOrderAnalyzer
    from test_reading_order_visualization import ReadingOrderVisualizer
except ImportError as e:
    logger.error(f"导入模块失败: {e}")
    sys.exit(1)


def process_pdf(pdf_path: str, output_dir: str, verbose: bool = False) -> None:
    """处理PDF并生成可视化结果
    
    Args:
        pdf_path: PDF文件路径
        output_dir: 输出目录
        verbose: 是否输出详细日志
    """
    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    try:
        # 1. 加载配置
        logger.info(f"加载配置...")
        config = load_config()
        
        # 2. 单独初始化必要的组件，以便可以直接访问内部对象
        logger.info(f"初始化组件...")
        pdf_converter = PDFConverter(config.pdf_converter)
        layout_analyzer = LayoutAnalyzer(config.layout_analyzer)
        reading_order_analyzer = ReadingOrderAnalyzer(config.reading_order)
        
        # 3. 转换PDF为图片
        logger.info(f"将PDF转换为图片...")
        images = pdf_converter.convert_pdf_to_images(pdf_path)
        logger.info(f"转换完成，共 {len(images)} 页")
        
        # 4. 初始化文档结构
        document = None
        
        # 5. 尝试从PDFPipeline对象的处理获取文档结构
        logger.info(f"使用PDFPipeline获取文档结构...")
        try:
            pipeline = PDFPipeline(settings=config)
            # 使用处理管道处理PDF，但我们只想获取文档结构，不需要生成Markdown
            # 检查是否有内部方法可以直接获取文档结构
            if hasattr(pipeline, 'extract_document_structure') and callable(getattr(pipeline, 'extract_document_structure')):
                logger.info("使用extract_document_structure方法...")
                document = pipeline.extract_document_structure(pdf_path)
            else:
                logger.info("使用process方法并提取文档结构...")
                # 如果没有直接方法，我们处理PDF并从pipeline对象中提取document属性
                result = pipeline.process(pdf_path=pdf_path, skip_markdown=True if hasattr(pipeline, 'skip_markdown') else False)
                # 尝试从pipeline或结果中获取document
                if hasattr(pipeline, 'document'):
                    document = pipeline.document
                elif isinstance(result, dict) and 'document' in result:
                    document = result['document']
        except Exception as e:
            logger.warning(f"无法从PDFPipeline获取文档结构: {e}")
            logger.info("退回到手动构建文档结构...")
        
        # 6. 如果无法从PDFPipeline获取文档结构，手动构建
        if not document:
            logger.info("手动构建文档结构...")
            # 创建空文档
            from src.models.document import Document, Page
            document = Document()
            
            # 检查Document类有哪些方法添加页面
            import inspect
            doc_methods = [name for name in dir(Document) if callable(getattr(Document, name)) and not name.startswith('_')]
            logger.info(f"Document类可用方法: {doc_methods}")
            
            # 保存所有页面，稍后一次性添加到文档
            pages = []
            
            # 处理每一页
            for i, img in enumerate(images):
                # 保存图片到临时文件
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp:
                    img_path = temp.name
                    img.save(img_path)
                
                try:
                    # 分析版式
                    logger.info(f"分析页面 {i+1} 版式...")
                    regions = layout_analyzer.analyze_layout(img_path, page_num=i)
                    
                    # 获取图像尺寸
                    width, height = img.size
                    logger.info(f"图像尺寸: 宽={width}, 高={height}")
                    
                    # 检查Page类需要哪些参数
                    try:
                        # 创建页面 - 提供所有必要的参数
                        page = Page(
                            page_number=i,
                            image_path=img_path,
                            regions=regions,
                            width=width,
                            height=height
                        )
                        logger.info(f"成功创建页面 {i+1}")
                        
                        # 将页面添加到列表
                        pages.append(page)
                    except Exception as e:
                        logger.error(f"创建Page对象失败: {e}")
                        # 尝试另一种方法
                        logger.info("尝试创建简化的Page对象...")
                        
                        # 动态查找Page类的参数
                        import inspect
                        sig = inspect.signature(Page.__init__)
                        
                        # 准备参数字典，根据需要添加参数
                        page_params = {
                            'page_number': i,
                            'image_path': img_path
                        }
                        
                        # 添加其他可能需要的参数
                        if 'regions' in sig.parameters:
                            page_params['regions'] = regions
                        if 'width' in sig.parameters:
                            page_params['width'] = width
                        if 'height' in sig.parameters:
                            page_params['height'] = height
                        
                        # 创建页面
                        page = Page(**page_params)
                        
                        # 如果没有通过构造函数设置区域，尝试直接设置
                        if not hasattr(page, 'regions') or page.regions is None:
                            page.regions = regions
                        
                        # 将页面添加到列表
                        pages.append(page)
                        logger.info(f"使用备选方法成功创建页面 {i+1}")
                        
                except Exception as e:
                    logger.error(f"处理页面 {i+1} 时出错: {e}")
            
            # 将所有页面添加到文档
            logger.info(f"尝试将 {len(pages)} 页添加到文档...")
            
            # 尝试不同的方法将页面添加到文档
            try:
                # 方法1: 如果document.pages是列表，直接扩展
                if hasattr(document, 'pages') and isinstance(document.pages, list):
                    document.pages.extend(pages)
                    logger.info("使用extend方法添加页面到文档")
                # 方法2: 如果有add_pages方法，使用它
                elif hasattr(document, 'add_pages') and callable(getattr(document, 'add_pages')):
                    document.add_pages(pages)
                    logger.info("使用add_pages方法添加页面到文档")
                # 方法3: 如果有append_page方法，逐个添加
                elif hasattr(document, 'append_page') and callable(getattr(document, 'append_page')):
                    for page in pages:
                        document.append_page(page)
                    logger.info("使用append_page方法添加页面到文档")
                # 方法4: 如果pages是属性，直接赋值
                else:
                    document.pages = pages
                    logger.info("直接设置document.pages")
            except Exception as e:
                logger.error(f"添加页面到文档失败: {e}")
                # 最后的备选方案
                try:
                    setattr(document, 'pages', pages)
                    logger.info("使用setattr设置document.pages")
                except Exception as e:
                    logger.error(f"设置document.pages失败: {e}")
            
            # 打印文档页数
            if hasattr(document, 'pages'):
                logger.info(f"手动构建的文档包含 {len(document.pages)} 页")
            else:
                logger.error("文档没有pages属性")
            
            # 确认每个页面都有区域
            if hasattr(document, 'pages'):
                for i, page in enumerate(document.pages):
                    if not hasattr(page, 'regions') or not page.regions:
                        logger.warning(f"页面 {i+1} 没有区域")
                    else:
                        logger.info(f"页面 {i+1} 有 {len(page.regions)} 个区域")
            
            # 分析阅读顺序
            try:
                logger.info("分析文档阅读顺序...")
                reading_order_analyzer.analyze_reading_order(document)
                logger.info("阅读顺序分析完成")
            except Exception as e:
                logger.error(f"分析阅读顺序时出错: {e}")
            
            # 再次检查文档页数
            if hasattr(document, 'pages'):
                logger.info(f"阅读顺序分析后的文档包含 {len(document.pages)} 页")
        
        # 7. 初始化可视化器
        visualizer = ReadingOrderVisualizer(output_dir)
        
        # 8. 可视化每页的阅读顺序
        logger.info(f"开始可视化处理...")
        with tempfile.TemporaryDirectory() as temp_dir:
            # 保存原始图像和页面图像文件路径映射
            page_image_paths = {}
            
            # 保存图像到临时目录
            temp_image_paths = []
            for i, img in enumerate(images):
                temp_image_path = os.path.join(temp_dir, f"page_{i+1}.png")
                img.save(temp_image_path, "PNG")
                temp_image_paths.append(temp_image_path)
                # 保存页面号和图像路径的映射
                page_image_paths[i] = temp_image_path
            
            # 如果文档没有页面，记录错误并退出
            if not document.pages:
                logger.error("文档没有包含任何页面，无法进行可视化")
            else:
                logger.info(f"文档包含 {len(document.pages)} 页，开始可视化")
                
            # 遍历文档中的页面进行可视化
            for page_idx, page in enumerate(document.pages):
                logger.info(f"生成第 {page_idx+1} 页的可视化...")
                
                # 获取页面的实际页码（可能与索引不同）
                actual_page_num = page.page_number if hasattr(page, 'page_number') else page_idx
                
                # 确保页码在有效范围内
                if actual_page_num not in page_image_paths:
                    logger.warning(f"找不到页面 {actual_page_num+1} 的图像，跳过")
                    continue
                
                # 获取对应的图像路径
                img_path = page_image_paths[actual_page_num]
                
                # 获取页面区域
                regions = page.regions if hasattr(page, 'regions') else []
                
                if not regions:
                    logger.warning(f"页面 {actual_page_num+1} 没有区域，跳过可视化")
                    continue
                    
                logger.info(f"页面 {actual_page_num+1} 有 {len(regions)} 个区域")
                
                # 可视化结果
                try:
                    output_img_path = visualizer.visualize_page_reading_order(
                        img_path, 
                        regions, 
                        actual_page_num, 
                        title=f"页面 {actual_page_num+1} 阅读顺序和版式分析 (使用与Markdown相同顺序)"
                    )
                    logger.info(f"页面 {actual_page_num+1} 可视化完成，输出: {output_img_path}")
                except Exception as e:
                    logger.error(f"可视化页面 {actual_page_num+1} 时出错: {e}")
            
            # 9. 生成HTML报告
            try:
                logger.info("生成HTML报告...")
                report_path = visualizer.create_reading_order_report(
                    document=document,
                    temp_dir=temp_dir,
                    algorithm_info={"name": "PDF处理管道", "description": "使用与Markdown生成相同的处理逻辑"}
                )
                logger.info(f"报告生成完成: {report_path}")
            except Exception as e:
                logger.error(f"生成HTML报告时出错: {e}")
                
        # 确保所有临时文件都被清理
        for page in document.pages:
            if hasattr(page, 'image_path') and os.path.exists(page.image_path):
                try:
                    os.unlink(page.image_path)
                    logger.debug(f"已删除临时文件: {page.image_path}")
                except Exception as e:
                    logger.warning(f"删除临时文件失败: {page.image_path}, 错误: {e}")
            
    except Exception as e:
        logger.error(f"处理失败: {e}")
        if verbose:
            import traceback
            traceback.print_exc()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="PDF阅读顺序和版式分析可视化")
    parser.add_argument("pdf_path", help="PDF文件路径")
    parser.add_argument("-o", "--output", default="output/test", help="输出目录")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    # 配置日志级别
    if args.verbose:
        try:
            logger.remove()
            logger.add(sys.stderr, level="DEBUG")
        except:
            logger.setLevel(logging.DEBUG)
    
    # 检查PDF文件是否存在
    if not os.path.exists(args.pdf_path):
        logger.error(f"PDF文件不存在: {args.pdf_path}")
        return 1
    
    try:
        # 处理PDF
        logger.info(f"开始处理PDF: {args.pdf_path}")
        process_pdf(args.pdf_path, args.output, args.verbose)
        print(f"\n✅ 处理完成! 输出目录: {os.path.abspath(args.output)}")
        return 0
    
    except Exception as e:
        logger.error(f"处理失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 