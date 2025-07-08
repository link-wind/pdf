#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF文档解析系统 - 命令行入口

用于将PDF文档转换为结构化的Markdown格式，支持多种文档场景。
"""

import argparse
import os
import sys
import time
from pathlib import Path

from loguru import logger

from src import PDFPipeline, load_config


def setup_logger(verbose=False):
    """配置日志记录器"""
    log_level = "DEBUG" if verbose else "INFO"
    logger.remove()  # 移除默认处理器
    logger.add(sys.stderr, level=log_level)
    logger.add("logs/pdf_parser_{time}.log", rotation="10 MB", level="DEBUG")


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="PDF文档解析系统 - 将PDF转换为结构化Markdown"
    )
    
    # 必需参数
    parser.add_argument(
        "-i", "--input", 
        required=True,
        help="输入PDF文件路径"
    )
    
    # 可选参数
    parser.add_argument(
        "-o", "--output",
        help="输出Markdown文件路径 (默认: 与输入文件同名的.md文件)"
    )
    parser.add_argument(
        "-s", "--scene",
        choices=["academic", "development", "general"],
        default="general",
        help="文档场景类型 (默认: general)"
    )
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="配置文件路径 (默认: config.yaml)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="启用详细输出"
    )
    parser.add_argument(
        "--list-scenes",
        action="store_true",
        help="列出所有可用的场景类型"
    )
    
    return parser.parse_args()


def validate_input(args):
    """验证输入参数"""
    # 检查输入文件是否存在
    if not os.path.isfile(args.input):
        logger.error(f"输入文件不存在: {args.input}")
        return False
    
    # 检查输入文件是否为PDF
    if not args.input.lower().endswith(".pdf"):
        logger.error(f"输入文件不是PDF格式: {args.input}")
        return False
    
    # 检查配置文件是否存在
    if not os.path.isfile(args.config):
        logger.error(f"配置文件不存在: {args.config}")
        return False
    
    # 设置默认输出路径（如果未指定）
    if not args.output:
        input_path = Path(args.input)
        args.output = str(input_path.with_suffix(".md"))
        logger.info(f"未指定输出路径，使用默认路径: {args.output}")
    
    # 确保输出目录存在
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"创建输出目录: {output_dir}")
    
    return True


def list_available_scenes():
    """列出所有可用的场景类型"""
    scenes = {
        "academic": "学术论文 - 优化用于处理复杂公式、表格和多栏版式",
        "development": "开发文档 - 优化用于处理代码块和复杂的逻辑结构",
        "general": "通用文档 - 适用于大多数常规文档"
    }
    
    print("\n可用的场景类型:")
    for scene, description in scenes.items():
        print(f"  - {scene}: {description}")
    print()


def process_pdf(args):
    """处理PDF文件"""
    try:
        # 加载配置
        config = load_config(args.config)
        
        # 初始化处理管道
        pipeline = PDFPipeline(settings=config)
        
        # 记录开始时间
        start_time = time.time()
        
        # 处理PDF文件
        logger.info(f"开始处理PDF文件: {args.input}")
        logger.info(f"场景类型: {args.scene}")
        
        result = pipeline.process(
            pdf_path=args.input
        )
        
        # 计算处理时间
        processing_time = time.time() - start_time
        
        # 输出结果
        if result['success']:
            logger.info(f"处理完成，输出文件: {result['output_path']}")
            logger.info(f"处理时间: {processing_time:.2f}秒")
            
            # 打印详细信息（如果启用）
            if args.verbose and 'metadata' in result:
                print("\n处理结果:")
                print(f"  - 页数: {result['metadata'].get('pages_count', 'N/A')}")
                print(f"  - 识别区域: {result['metadata'].get('total_regions', 'N/A')}个")
                print(f"  - 处理时间: {processing_time:.2f}秒")
                print(f"  - 输出文件: {result['output_path']}")
                
            return True
        else:
            logger.error(f"处理失败: {result.get('error', '未知错误')}")
            return False
    
    except Exception as e:
        logger.error(f"处理PDF文件时出错: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return False


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    # 配置日志记录器
    setup_logger(args.verbose)
    
    # 如果请求列出场景，则显示场景列表并退出
    if args.list_scenes:
        list_available_scenes()
        return 0
    
    # 验证输入参数
    if not validate_input(args):
        return 1
    
    # 处理PDF文件
    success = process_pdf(args)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
