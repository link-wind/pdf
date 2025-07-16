#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
生成提交CSV文件脚本
格式要求: ["file_id", "answer"]
- file_id: md文档文件名（不包含后缀）
- answer: markdown解析结果

处理流程：先生成JSON格式，再转换为CSV格式
"""

import os
import csv
import json
import argparse
from pathlib import Path
import pandas as pd


def create_json_from_markdown(markdown_dir, output_json):
    """
    根据markdown文件创建中间JSON文件
    
    Args:
        markdown_dir: 包含markdown文件的目录路径
        output_json: 输出的JSON文件路径
    """
    print(f"开始处理目录 {markdown_dir} 中的markdown文件...")
    
    # 确保输出目录存在
    output_path = Path(output_json)
    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 获取所有markdown文件
    md_files = list(Path(markdown_dir).glob("*.md"))
    if not md_files:
        print(f"错误：在目录 {markdown_dir} 中没有找到markdown文件")
        return False, None
    
    print(f"找到 {len(md_files)} 个markdown文件")
    
    # 准备JSON数据
    json_data = []
    
    # 处理每个markdown文件
    for md_file in md_files:
        file_id = md_file.stem  # 获取文件名（不含后缀）
        
        try:
            # 读取markdown内容
            with open(md_file, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # 添加到JSON数据
            json_data.append({
                "file_id": file_id,
                "answer": md_content
            })
            print(f"已处理: {md_file.name}")
            
        except Exception as e:
            print(f"处理文件 {md_file} 时出错: {e}")
    
    # 写入JSON文件
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print(f"中间JSON文件已生成: {output_json}")
    return True, json_data


def convert_json_to_csv(json_data, json_file, csv_file):
    """
    将JSON数据转换为CSV格式
    
    Args:
        json_data: JSON数据对象，如果为None则从json_file读取
        json_file: JSON文件路径
        csv_file: 输出的CSV文件路径
    """
    try:
        # 如果没有提供json_data，则从文件读取
        if json_data is None:
            with open(json_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
        
        # 使用pandas处理CSV写入，更可靠地处理特殊字符
        df = pd.DataFrame(json_data)
        df.to_csv(csv_file, index=False, quoting=csv.QUOTE_ALL)
        print(f"CSV文件已从JSON生成: {csv_file}")
        return True
    except Exception as e:
        print(f"转换JSON到CSV时出错: {e}")
        return False


def create_submission_files(markdown_dir, output_file, keep_json=True):
    """
    创建提交文件，先生成JSON，再转换为CSV
    
    Args:
        markdown_dir: 包含markdown文件的目录路径
        output_file: 输出文件路径（不含扩展名）
        keep_json: 是否保留中间JSON文件
    """
    # 确定输出文件路径
    output_base = output_file.rsplit(".", 1)[0] if "." in output_file else output_file
    json_file = f"{output_base}.json"
    csv_file = f"{output_base}.csv"
    
    # 第一步：生成JSON文件
    success, json_data = create_json_from_markdown(markdown_dir, json_file)
    if not success:
        return False
    
    # 第二步：将JSON转换为CSV
    csv_success = convert_json_to_csv(json_data, json_file, csv_file)
    
    # 如果不需要保留JSON文件且CSV生成成功，则删除JSON文件
    if not keep_json and csv_success and os.path.exists(json_file):
        try:
            os.remove(json_file)
            print(f"已删除中间JSON文件: {json_file}")
        except Exception as e:
            print(f"无法删除JSON文件: {e}")
    
    return csv_success


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="生成提交文件 - 先JSON后CSV")
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
        "--keep-json",
        action="store_true",
        default=True,
        help="保留中间JSON文件 (默认: 保留)"
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="仅生成JSON文件，不转换为CSV (默认: 生成两者)"
    )
    
    args = parser.parse_args()
    
    # 确定基本输出文件名（不含扩展名）
    output_base = args.output.rsplit(".", 1)[0] if "." in args.output else args.output
    
    if args.json_only:
        # 仅生成JSON文件
        json_file = f"{output_base}.json"
        success, _ = create_json_from_markdown(args.input, json_file)
    else:
        # 生成JSON和CSV
        success = create_submission_files(args.input, args.output, args.keep_json)
    
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main()) 