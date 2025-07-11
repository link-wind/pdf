#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
特定CSV问题修复工具 - 专门用于修复特定文件导致的CSV格式问题
"""

import os
import json
import argparse
from pathlib import Path


def fix_specific_file(markdown_dir, file_id, output_file, output_format="jsonl"):
    """
    修复特定的问题文件并输出正确格式
    
    Args:
        markdown_dir: 包含markdown文件的目录
        file_id: 问题文件的ID（不含后缀）
        output_file: 输出文件路径
        output_format: 输出格式 (jsonl, csv_manual)
    """
    # 定位文件
    md_file = Path(markdown_dir) / f"{file_id}.md"
    if not md_file.exists():
        print(f"错误: 文件 {md_file} 不存在")
        return False
    
    try:
        # 读取markdown内容
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 确保输出目录存在
        output_path = Path(output_file)
        if not output_path.parent.exists():
            output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if output_format == "jsonl":
            # 创建JSON对象
            data = {"file_id": file_id, "answer": content}
            
            # 写入JSON文件
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"已将文件 {file_id} 保存为JSON: {output_file}")
        
        elif output_format == "csv_manual":
            # 手动构造CSV内容
            with open(output_file, 'w', encoding='utf-8') as f:
                # 写入CSV头
                f.write("file_id,answer\n")
                
                # 对内容进行特殊处理，确保CSV格式正确
                # 1. 替换所有双引号为两个双引号(CSV转义规则)
                safe_content = content.replace('"', '""')
                # 2. 删除可能导致格式问题的字符
                safe_content = safe_content.replace('\r', ' ')
                
                # 写入一行，整体用双引号包围确保格式正确
                f.write(f'"{file_id}","{safe_content}"\n')
            
            print(f"已将文件 {file_id} 保存为CSV: {output_file}")
        
        return True
    
    except Exception as e:
        print(f"处理文件时出错: {e}")
        return False


def create_csv_with_problem_file_excluded(markdown_dir, problem_file_id, output_csv):
    """
    创建不包含问题文件的CSV
    
    Args:
        markdown_dir: 包含markdown文件的目录
        problem_file_id: 问题文件的ID（不含后缀）
        output_csv: 输出CSV文件路径
    """
    print(f"创建排除问题文件的CSV...")
    
    # 获取所有markdown文件
    md_files = list(Path(markdown_dir).glob("*.md"))
    if not md_files:
        print(f"错误：在目录 {markdown_dir} 中没有找到markdown文件")
        return False
    
    # 确保输出目录存在
    output_path = Path(output_csv)
    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # 打开CSV文件
        with open(output_csv, 'w', encoding='utf-8') as f:
            # 写入CSV头
            f.write("file_id,answer\n")
            
            # 处理每个文件
            for md_file in md_files:
                file_id = md_file.stem  # 不含后缀的文件名
                
                # 跳过问题文件
                if file_id == problem_file_id:
                    print(f"跳过问题文件: {md_file.name}")
                    continue
                
                try:
                    # 读取markdown内容
                    with open(md_file, 'r', encoding='utf-8') as mf:
                        content = mf.read()
                    
                    # 处理内容确保CSV格式正确
                    safe_content = content.replace('"', '""')
                    
                    # 写入一行
                    f.write(f'"{file_id}","{safe_content}"\n')
                    print(f"已处理: {md_file.name}")
                    
                except Exception as e:
                    print(f"处理文件 {md_file.name} 时出错: {e}")
        
        print(f"CSV文件已生成: {output_csv}")
        return True
        
    except Exception as e:
        print(f"创建CSV文件时出错: {e}")
        return False


def combine_csv_and_problem_file(main_csv, problem_file_json, output_csv):
    """
    将主CSV文件和单独处理的问题文件合并
    
    Args:
        main_csv: 主CSV文件路径
        problem_file_json: 问题文件的JSON路径
        output_csv: 输出的合并CSV文件路径
    """
    try:
        # 读取问题文件JSON
        with open(problem_file_json, 'r', encoding='utf-8') as f:
            problem_data = json.load(f)
        
        # 读取主CSV文件的所有内容
        with open(main_csv, 'r', encoding='utf-8') as f:
            csv_content = f.readlines()
        
        # 处理问题文件内容为CSV格式
        file_id = problem_data['file_id']
        content = problem_data['answer'].replace('"', '""')
        problem_csv_line = f'"{file_id}","{content}"\n'
        
        # 合并内容
        with open(output_csv, 'w', encoding='utf-8') as f:
            # 写入CSV头
            f.write(csv_content[0])
            
            # 写入主CSV内容（不含头）
            f.writelines(csv_content[1:])
            
            # 添加问题文件
            f.write(problem_csv_line)
        
        print(f"已成功合并文件到: {output_csv}")
        return True
    
    except Exception as e:
        print(f"合并文件时出错: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="修复特定CSV问题文件")
    parser.add_argument(
        "-i", "--input", 
        default="output/markdown",
        help="包含markdown文件的输入目录 (默认: output/markdown)"
    )
    parser.add_argument(
        "-o", "--output",
        default="output/fixed_submission.csv",
        help="输出文件路径 (默认: output/fixed_submission.csv)"
    )
    parser.add_argument(
        "--problem-id",
        default="1c2222c5-9057-44ef-84e0-cc2536f2e19d",
        help="问题文件的ID (默认: 1c2222c5-9057-44ef-84e0-cc2536f2e19d)"
    )
    parser.add_argument(
        "--fix-method",
        choices=["two_step", "direct"],
        default="two_step",
        help="修复方法 (默认: two_step)"
    )
    
    args = parser.parse_args()
    
    # 根据修复方法执行不同的处理流程
    if args.fix_method == "two_step":
        # 两步法：先生成不含问题文件的CSV，再单独处理问题文件并合并
        
        # 步骤1：创建不包含问题文件的CSV
        step1_csv = args.output.rsplit(".", 1)[0] + "_step1.csv"
        success1 = create_csv_with_problem_file_excluded(args.input, args.problem_id, step1_csv)
        if not success1:
            return 1
        
        # 步骤2：单独处理问题文件为JSON
        problem_json = args.output.rsplit(".", 1)[0] + "_problem.json"
        success2 = fix_specific_file(args.input, args.problem_id, problem_json, "jsonl")
        if not success2:
            return 1
        
        # 步骤3：合并文件
        success3 = combine_csv_and_problem_file(step1_csv, problem_json, args.output)
        
        # 清理中间文件
        if os.path.exists(step1_csv) and os.path.exists(problem_json) and success3:
            try:
                os.remove(step1_csv)
                os.remove(problem_json)
                print("已清理中间文件")
            except:
                print("无法删除中间文件")
        
        return 0 if success3 else 1
    
    else:  # direct方法
        # 直接方法：单独处理问题文件为CSV
        success = fix_specific_file(args.input, args.problem_id, args.output, "csv_manual")
        return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main()) 