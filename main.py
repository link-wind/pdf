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
    
    # 输入参数组 - 互斥选项
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "-i", "--input", 
        help="输入PDF文件路径"
    )
    input_group.add_argument(
        "-b", "--batch",
        action="store_true",
        help="批量处理模式 - 处理data/input/samples目录下的所有PDF文件"
    )
    
    # 可选参数
    parser.add_argument(
        "-o", "--output",
        help="输出Markdown文件路径 (默认: 与输入文件同名的.md文件) 或批量处理输出目录 (默认: output/markdown)"
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
    # 检查配置文件是否存在
    if not os.path.isfile(args.config):
        logger.error(f"配置文件不存在: {args.config}")
        return False
    
    if args.batch:
        # 批量处理模式
        input_dir = Path("data/input/samples")
        if not input_dir.exists():
            logger.error(f"批量处理输入目录不存在: {input_dir}")
            return False
        
        # 检查是否有PDF文件
        pdf_files = list(input_dir.glob("*.pdf"))
        if not pdf_files:
            logger.error(f"在目录 {input_dir} 中没有找到PDF文件")
            return False
        
        # 设置默认输出目录
        if not args.output:
            args.output = "output/markdown"
            logger.info(f"未指定输出目录，使用默认目录: {args.output}")
        
        # 确保输出目录存在
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"输出目录: {output_dir}")
        
    else:
        # 单文件处理模式
        if not os.path.isfile(args.input):
            logger.error(f"输入文件不存在: {args.input}")
            return False
        
        # 检查输入文件是否为PDF
        if not args.input.lower().endswith(".pdf"):
            logger.error(f"输入文件不是PDF格式: {args.input}")
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


def process_single_pdf(pdf_path, output_path, pipeline, verbose=False):
    """处理单个PDF文件"""
    try:
        # 记录开始时间
        start_time = time.time()
        
        # 处理PDF文件
        logger.info(f"开始处理PDF文件: {pdf_path}")
        
        result = pipeline.process(pdf_path=pdf_path)
        
        # 计算处理时间
        processing_time = time.time() - start_time
        
        # 输出结果
        if result['success']:
            # 移动或重命名输出文件到指定位置
            if result['output_path'] != output_path:
                import shutil
                import os
                # 如果目标文件已存在则先删除
                if os.path.exists(output_path):
                    if os.path.isfile(output_path):
                        os.remove(output_path)
                    # 如果是目录，我们不处理，让shutil.move自动处理
                shutil.move(result['output_path'], output_path)
            
            logger.info(f"处理完成，输出文件: {output_path}")
            logger.info(f"处理时间: {processing_time:.2f}秒")
            
            # 打印详细信息（如果启用）
            if verbose and 'metadata' in result:
                print(f"\n处理结果 - {Path(pdf_path).name}:")
                print(f"  - 页数: {result['metadata'].get('pages_count', 'N/A')}")
                print(f"  - 识别区域: {result['metadata'].get('total_regions', 'N/A')}个")
                print(f"  - 处理时间: {processing_time:.2f}秒")
                print(f"  - 输出文件: {output_path}")
                
            return True, processing_time
        else:
            logger.error(f"处理失败: {result.get('error', '未知错误')}")
            return False, processing_time
    
    except Exception as e:
        logger.error(f"处理PDF文件 {pdf_path} 时出错: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False, 0


def process_batch(args):
    """批量处理PDF文件"""
    try:
        # 加载配置
        config = load_config(args.config)
        
        # 初始化处理管道
        pipeline = PDFPipeline(settings=config)
        
        # 获取所有PDF文件
        input_dir = Path("data/input/samples")
        pdf_files = list(input_dir.glob("*.pdf"))
        
        logger.info(f"找到 {len(pdf_files)} 个PDF文件")
        logger.info(f"场景类型: {args.scene}")
        
        # 处理结果统计
        successful_count = 0
        failed_count = 0
        total_time = 0
        
        # 逐个处理PDF文件
        for pdf_file in pdf_files:
            # 生成输出文件路径
            output_file = Path(args.output) / f"{pdf_file.stem}.md"
            
            # 处理单个PDF文件
            success, processing_time = process_single_pdf(
                pdf_path=str(pdf_file),
                output_path=str(output_file),
                pipeline=pipeline,
                verbose=args.verbose
            )
            
            if success:
                successful_count += 1
            else:
                failed_count += 1
            
            total_time += processing_time
        
        # 打印批量处理结果
        logger.info(f"\n批量处理完成:")
        logger.info(f"  - 成功: {successful_count} 个文件")
        logger.info(f"  - 失败: {failed_count} 个文件")
        logger.info(f"  - 总时间: {total_time:.2f}秒")
        logger.info(f"  - 平均时间: {total_time/len(pdf_files):.2f}秒/文件")
        
        return successful_count > 0
        
    except Exception as e:
        logger.error(f"批量处理时出错: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return False


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
            # 移动或重命名输出文件到指定位置
            if result['output_path'] != args.output:
                import shutil
                import os
                # 如果目标文件已存在则先删除
                if os.path.exists(args.output):
                    if os.path.isfile(args.output):
                        os.remove(args.output)
                    # 如果是目录，我们不处理，让shutil.move自动处理
                shutil.move(result['output_path'], args.output)
            
            logger.info(f"处理完成，输出文件: {args.output}")
            logger.info(f"处理时间: {processing_time:.2f}秒")
            
            # 打印详细信息（如果启用）
            if args.verbose and 'metadata' in result:
                print("\n处理结果:")
                print(f"  - 页数: {result['metadata'].get('pages_count', 'N/A')}")
                print(f"  - 识别区域: {result['metadata'].get('total_regions', 'N/A')}个")
                print(f"  - 处理时间: {processing_time:.2f}秒")
                print(f"  - 输出文件: {args.output}")
                
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
    if args.batch:
        success = process_batch(args)
    else:
        success = process_pdf(args)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
