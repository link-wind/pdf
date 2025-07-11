#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CSV修复工具 - 专门用于将Markdown内容导出为正确格式的CSV
通过更可靠的方法确保即使包含特殊字符的内容也能正确导出
"""

import os
import json
import base64
import argparse
from pathlib import Path


def create_csv_special(markdown_dir, output_csv, encoding_method="raw"):
    """
    使用特殊方法创建CSV文件，避免格式问题
    
    Args:
        markdown_dir: 包含markdown文件的目录
        output_csv: 输出的CSV文件路径
        encoding_method: 编码方法 ("raw", "base64")
    """
    print(f"开始处理目录 {markdown_dir} 中的markdown文件...")
    
    # 确保输出目录存在
    output_path = Path(output_csv)
    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 获取所有markdown文件
    md_files = list(Path(markdown_dir).glob("*.md"))
    if not md_files:
        print(f"错误：在目录 {markdown_dir} 中没有找到markdown文件")
        return False
    
    print(f"找到 {len(md_files)} 个markdown文件")
    
    try:
        # 打开CSV文件，使用UTF-8编码并带BOM标记（可能有助于Excel识别）
        with open(output_csv, 'w', encoding='utf-8-sig') as f:
            # 写入CSV头
            f.write('file_id,answer\n')
            
            # 逐个处理文件
            for md_file in md_files:
                file_id = md_file.stem  # 不含后缀的文件名
                
                try:
                    # 读取markdown内容
                    with open(md_file, 'r', encoding='utf-8') as mf:
                        content = mf.read()
                    
                    # 根据编码方法处理content
                    if encoding_method == "base64":
                        # Base64编码（确保完全避免格式问题，但需要在使用前解码）
                        encoded_content = base64.b64encode(content.encode('utf-8')).decode('ascii')
                        safe_content = encoded_content
                    else:  # raw模式
                        # 手动转义引号和逗号，使用自定义分隔符
                        safe_content = content.replace('"', '""')  # 双引号转义
                    
                    # 写入一行，用双引号包围内容防止格式问题
                    f.write(f'"{file_id}","{safe_content}"\n')
                    print(f"已处理: {md_file.name}")
                    
                except Exception as e:
                    print(f"处理文件 {md_file.name} 时出错: {e}")
        
        print(f"CSV文件已生成: {output_csv}")
        return True
        
    except Exception as e:
        print(f"创建CSV文件时出错: {e}")
        return False


def create_tsv_format(markdown_dir, output_tsv):
    """
    创建TSV格式文件（用制表符分隔，避免逗号分隔的问题）
    
    Args:
        markdown_dir: 包含markdown文件的目录
        output_tsv: 输出的TSV文件路径
    """
    print(f"开始处理目录 {markdown_dir} 中的markdown文件...")
    
    # 确保输出目录存在
    output_path = Path(output_tsv)
    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 获取所有markdown文件
    md_files = list(Path(markdown_dir).glob("*.md"))
    if not md_files:
        print(f"错误：在目录 {markdown_dir} 中没有找到markdown文件")
        return False
    
    print(f"找到 {len(md_files)} 个markdown文件")
    
    try:
        # 打开TSV文件
        with open(output_tsv, 'w', encoding='utf-8') as f:
            # 写入头部
            f.write("file_id\tanswer\n")
            
            # 逐个处理文件
            for md_file in md_files:
                file_id = md_file.stem  # 不含后缀的文件名
                
                try:
                    # 读取markdown内容
                    with open(md_file, 'r', encoding='utf-8') as mf:
                        content = mf.read()
                    
                    # 将内容中的制表符替换为空格（确保不破坏TSV结构）
                    safe_content = content.replace('\t', '    ')
                    # 确保内容不包含换行符（替换为\\n）
                    safe_content = safe_content.replace('\n', '\\n')
                    
                    # 写入一行
                    f.write(f"{file_id}\t{safe_content}\n")
                    print(f"已处理: {md_file.name}")
                    
                except Exception as e:
                    print(f"处理文件 {md_file.name} 时出错: {e}")
        
        print(f"TSV文件已生成: {output_tsv}")
        return True
        
    except Exception as e:
        print(f"创建TSV文件时出错: {e}")
        return False


def create_jsonl_format(markdown_dir, output_jsonl):
    """
    创建JSONL格式文件（每行一个JSON对象，最可靠的格式）
    
    Args:
        markdown_dir: 包含markdown文件的目录
        output_jsonl: 输出的JSONL文件路径
    """
    print(f"开始处理目录 {markdown_dir} 中的markdown文件...")
    
    # 确保输出目录存在
    output_path = Path(output_jsonl)
    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 获取所有markdown文件
    md_files = list(Path(markdown_dir).glob("*.md"))
    if not md_files:
        print(f"错误：在目录 {markdown_dir} 中没有找到markdown文件")
        return False
    
    print(f"找到 {len(md_files)} 个markdown文件")
    
    try:
        # 打开JSONL文件
        with open(output_jsonl, 'w', encoding='utf-8') as f:
            # 逐个处理文件
            for md_file in md_files:
                file_id = md_file.stem  # 不含后缀的文件名
                
                try:
                    # 读取markdown内容
                    with open(md_file, 'r', encoding='utf-8') as mf:
                        content = mf.read()
                    
                    # 创建JSON对象并写入一行
                    json_obj = {"file_id": file_id, "answer": content}
                    f.write(json.dumps(json_obj, ensure_ascii=False) + "\n")
                    print(f"已处理: {md_file.name}")
                    
                except Exception as e:
                    print(f"处理文件 {md_file.name} 时出错: {e}")
        
        print(f"JSONL文件已生成: {output_jsonl}")
        return True
        
    except Exception as e:
        print(f"创建JSONL文件时出错: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="修复CSV导出问题 - 多种格式选择")
    parser.add_argument(
        "-i", "--input", 
        default="output/markdown",
        help="包含markdown文件的输入目录 (默认: output/markdown)"
    )
    parser.add_argument(
        "-o", "--output",
        default="output/submission.csv",
        help="输出文件路径 (默认: output/submission.csv)"
    )
    parser.add_argument(
        "--format",
        choices=["csv", "tsv", "jsonl"],
        default="csv",
        help="输出格式选择 (默认: csv)"
    )
    parser.add_argument(
        "--encoding",
        choices=["raw", "base64"],
        default="raw",
        help="内容编码方式，仅用于CSV格式 (默认: raw)"
    )
    
    args = parser.parse_args()
    
    # 根据选择的格式创建相应的输出文件
    if args.format == "tsv":
        output_file = args.output.rsplit(".", 1)[0] + ".tsv" if args.output.endswith(".csv") else args.output
        success = create_tsv_format(args.input, output_file)
    elif args.format == "jsonl":
        output_file = args.output.rsplit(".", 1)[0] + ".jsonl" if args.output.endswith(".csv") else args.output
        success = create_jsonl_format(args.input, output_file)
    else:
        success = create_csv_special(args.input, args.output, args.encoding)
    
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main()) 