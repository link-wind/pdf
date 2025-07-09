#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
查看PDF处理结果的可视化脚本

显示指定目录中的处理结果，包括布局分析和阅读顺序。

使用方法:
python view_layout_results.py -o <output_dir>
"""

import os
import sys
import argparse
import glob
import webbrowser
from pathlib import Path

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


def find_result_files(output_dir: str):
    """查找处理结果文件
    
    Args:
        output_dir: 输出目录
        
    Returns:
        tuple: (report_files, image_files)
    """
    output_path = Path(output_dir)
    
    # 查找HTML报告
    report_files = list(output_path.glob("*.html"))
    
    # 查找图像文件
    image_files = list(output_path.glob("reading_order_page_*.png"))
    
    return report_files, image_files


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="查看PDF处理结果")
    parser.add_argument("-o", "--output", default="output/test", help="输出目录")
    
    args = parser.parse_args()
    
    # 检查输出目录是否存在
    if not os.path.exists(args.output):
        logger.error(f"输出目录不存在: {args.output}")
        return 1
    
    # 查找处理结果
    report_files, image_files = find_result_files(args.output)
    
    # 显示处理结果
    logger.info(f"在 {args.output} 中找到 {len(report_files)} 个报告和 {len(image_files)} 个图像")
    
    # 如果存在报告，打开第一个报告
    if report_files:
        report_path = report_files[0]
        logger.info(f"打开报告: {report_path}")
        
        # 构建文件URL
        file_url = f"file://{os.path.abspath(report_path)}"
        
        # 尝试打开浏览器
        try:
            webbrowser.open(file_url)
        except Exception as e:
            logger.error(f"无法打开浏览器: {e}")
            logger.info(f"请手动打开报告: {os.path.abspath(report_path)}")
    
    # 显示图像文件列表
    if image_files:
        logger.info("图像文件列表:")
        for img_path in sorted(image_files):
            logger.info(f"  - {img_path}")
    
    # 如果没有结果
    if not report_files and not image_files:
        logger.warning(f"在 {args.output} 中未找到处理结果")
        logger.info("请先运行 visualize_pdf_reading_order.py 生成处理结果")
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 