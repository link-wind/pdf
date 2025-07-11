#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
比较两个目录中文件的脚本
用于找出PDF目录和MD目录中文件名不匹配的文件
"""

import os
import argparse
from pathlib import Path


def get_file_names(directory, extension):
    """
    获取指定目录中特定扩展名文件的文件名（不含扩展名）
    
    Args:
        directory: 目录路径
        extension: 文件扩展名（例如 '.pdf', '.md'）
    
    Returns:
        文件名集合（不含扩展名）
    """
    path = Path(directory)
    if not path.exists() or not path.is_dir():
        print(f"错误：目录不存在 - {directory}")
        return set()
    
    # 获取所有指定扩展名的文件，提取文件名（不含扩展名）
    files = set()
    for file_path in path.glob(f"*{extension}"):
        files.add(file_path.stem)
    
    return files


def compare_directories(pdf_dir, md_dir):
    """
    比较两个目录中的文件名差异
    
    Args:
        pdf_dir: PDF文件目录
        md_dir: MD文件目录
    
    Returns:
        pdf_only: 仅在PDF目录中存在的文件名
        md_only: 仅在MD目录中存在的文件名
    """
    # 获取两个目录中的文件名
    pdf_files = get_file_names(pdf_dir, '.pdf')
    md_files = get_file_names(md_dir, '.md')
    
    # 找出差异
    pdf_only = pdf_files - md_files
    md_only = md_files - pdf_files
    
    return pdf_only, md_only


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="比较两个目录中的文件差异（PDF和MD）")
    parser.add_argument(
        "--pdf-dir",
        default="data/input/samples",
        help="包含PDF文件的目录 (默认: data/input/samples)"
    )
    parser.add_argument(
        "--md-dir",
        default="output/markdown",
        help="包含MD文件的目录 (默认: output/markdown)"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="将结果保存到文件 (默认: 仅显示)"
    )
    parser.add_argument(
        "--output",
        default="output/comparison_result.txt",
        help="保存结果的文件路径 (默认: output/comparison_result.txt)"
    )
    
    args = parser.parse_args()
    
    # 比较目录
    pdf_only, md_only = compare_directories(args.pdf_dir, args.md_dir)
    
    # 准备输出内容
    result = []
    result.append(f"比较结果:")
    result.append(f"PDF目录: {args.pdf_dir}")
    result.append(f"MD目录: {args.md_dir}")
    result.append("")
    
    if pdf_only:
        result.append(f"仅在PDF目录中存在的文件 ({len(pdf_only)}个):")
        for file_name in sorted(pdf_only):
            result.append(f"  - {file_name}.pdf")
        result.append("")
    else:
        result.append("没有仅在PDF目录中存在的文件")
        result.append("")
    
    if md_only:
        result.append(f"仅在MD目录中存在的文件 ({len(md_only)}个):")
        for file_name in sorted(md_only):
            result.append(f"  - {file_name}.md")
        result.append("")
    else:
        result.append("没有仅在MD目录中存在的文件")
        result.append("")
    
    # 统计信息
    total_pdf = len(pdf_only) + len(pdf_only.intersection(md_only))
    total_md = len(md_only) + len(pdf_only.intersection(md_only))
    match_count = len(pdf_only.intersection(md_only))
    
    result.append(f"统计信息:")
    result.append(f"  - PDF文件总数: {total_pdf}")
    result.append(f"  - MD文件总数: {total_md}")
    result.append(f"  - 匹配文件数: {match_count}")
    result.append(f"  - 不匹配文件数: {len(pdf_only) + len(md_only)}")
    
    # 输出结果
    output_text = "\n".join(result)
    print(output_text)
    
    # 保存结果到文件
    if args.save:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_text)
        print(f"\n结果已保存到: {args.output}")
    
    # 返回是否存在不匹配
    return 0 if not pdf_only and not md_only else 1


if __name__ == "__main__":
    import sys
    sys.exit(main()) 