#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
阅读顺序可视化测试脚本

使用方法:
python test_reading_order_visual.py <pdf_path>

输出:
- 在output/test目录下生成阅读顺序可视化图像和报告
"""

import os
import sys
import argparse
from pathlib import Path

# 确保可以导入项目模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入测试模块
from test_reading_order_visualization import test_reading_order_with_visualization

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="阅读顺序可视化测试")
    parser.add_argument("pdf_path", nargs='?', default=None, help="PDF文件或目录路径")
    parser.add_argument("-o", "--output", default="output/test", help="输出目录")
    parser.add_argument("-d", "--data-dir", default="data/input/test", help="数据目录（如果未指定PDF路径）")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    # 配置日志级别
    if args.verbose:
        try:
            logger.remove()
            logger.add(sys.stderr, level="DEBUG")
        except:
            logger.setLevel(logging.DEBUG)
    
    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)
    
    # 确定要处理的PDF路径
    pdf_path = args.pdf_path
    if pdf_path is None:
        # 如果未指定PDF路径，使用数据目录中的第一个PDF文件
        data_dir = Path(args.data_dir)
        pdf_files = list(data_dir.glob("*.pdf"))
        if not pdf_files:
            logger.error(f"数据目录 {data_dir} 中没有PDF文件")
            return 1
        pdf_path = str(pdf_files[0])
        logger.info(f"未指定PDF文件，使用: {pdf_path}")
    
    # 检查PDF路径是否存在
    if not os.path.exists(pdf_path):
        logger.error(f"PDF文件或目录不存在: {pdf_path}")
        return 1
    
    try:
        # 运行可视化测试
        logger.info(f"开始处理: {pdf_path}")
        logger.info(f"输出目录: {args.output}")
        
        report_path = test_reading_order_with_visualization(pdf_path, args.output)
        
        logger.info(f"处理完成，报告路径: {report_path}")
        print(f"\n✅ 测试完成! 查看报告: {report_path}")
        return 0
    
    except Exception as e:
        logger.error(f"测试失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 