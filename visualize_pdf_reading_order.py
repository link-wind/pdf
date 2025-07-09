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
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # 1. 加载配置
            logger.info(f"加载配置...")
            config = load_config()
            
            # 2. 初始化PDF转换器
            logger.info(f"初始化PDF转换器...")
            pdf_converter = PDFConverter(config.pdf_converter)
            
            # 3. 初始化版式分析器
            logger.info(f"初始化版式分析器...")
            layout_analyzer = LayoutAnalyzer(config.layout_analyzer)
            
            # 4. 初始化阅读顺序分析器
            logger.info(f"初始化阅读顺序分析器...")
            reading_order_analyzer = ReadingOrderAnalyzer(config.reading_order)
            
            # 5. 初始化可视化器
            visualizer = ReadingOrderVisualizer(output_dir)
            
            # 6. 转换PDF为图片
            logger.info(f"将PDF转换为图片...")
            images = pdf_converter.convert_pdf_to_images(pdf_path)
            logger.info(f"转换完成，共 {len(images)} 页")
            
            # 7. 保存图片到临时目录
            temp_image_paths = []
            for i, img in enumerate(images):
                temp_image_path = os.path.join(temp_dir, f"page_{i+1}.png")
                img.save(temp_image_path, "PNG")
                temp_image_paths.append(temp_image_path)
            
            # 8. 处理每一页
            for page_idx, img_path in enumerate(temp_image_paths):
                logger.info(f"处理第 {page_idx+1} 页...")
                
                # 分析版式
                layout_result = layout_analyzer.analyze_layout(img_path)
                page = type('Page', (), {'regions': layout_result})()
                
                # 分析阅读顺序
                document = type('Document', (), {'pages': [page]})()
                reading_order_analyzer.analyze_reading_order(document)
                
                # 可视化结果
                output_img_path = visualizer.visualize_page_reading_order(
                    img_path, page.regions, page_idx, 
                    title=f"页面 {page_idx+1} 阅读顺序和版式分析"
                )
                
                logger.info(f"页面 {page_idx+1} 处理完成，输出: {output_img_path}")
            
            # 9. 生成HTML报告
            logger.info("生成HTML报告...")
            document = type('Document', (), {'pages': []})()
            for page_idx, img_path in enumerate(temp_image_paths):
                # 获取版式分析结果
                layout_result = layout_analyzer.analyze_layout(img_path)
                page = type('Page', (), {'regions': layout_result})()
                document.pages.append(page)
            
            report_path = visualizer.create_reading_order_report(
                document=document,
                temp_dir=temp_dir,
                algorithm_info=reading_order_analyzer.get_algorithm_info()
            )
            
            logger.info(f"报告生成完成: {report_path}")
            
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