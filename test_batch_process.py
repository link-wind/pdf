#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量处理测试脚本
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from src import PDFPipeline, load_config

def test_batch_process():
    """测试批量处理功能"""
    try:
        # 加载配置
        config = load_config("config.yaml")
        
        # 初始化处理管道
        pipeline = PDFPipeline(settings=config)
        
        # 创建测试目录
        input_dir = Path("data/input/samples")
        output_dir = Path("output/markdown")
        
        # 确保目录存在
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查是否有测试PDF文件
        pdf_files = list(input_dir.glob("*.pdf"))
        if not pdf_files:
            print(f"在 {input_dir} 中没有找到PDF文件")
            print("请将一些PDF文件放入该目录中进行测试")
            return
        
        print(f"找到 {len(pdf_files)} 个PDF文件")
        
        # 处理每个PDF文件
        for pdf_file in pdf_files:
            print(f"\n处理文件: {pdf_file.name}")
            
            # 生成输出文件路径
            output_file = output_dir / f"{pdf_file.stem}.md"
            
            try:
                # 处理PDF
                result = pipeline.process(pdf_path=str(pdf_file))
                
                if result['success']:
                    # 移动输出文件到指定位置
                    if result['output_path'] != str(output_file):
                        import shutil
                        shutil.move(result['output_path'], str(output_file))
                    
                    print(f"✓ 成功处理: {output_file}")
                else:
                    print(f"✗ 处理失败: {result.get('error', '未知错误')}")
                    
            except Exception as e:
                print(f"✗ 处理文件 {pdf_file.name} 时出错: {e}")
        
        print(f"\n批量处理完成！输出目录: {output_dir}")
        
    except Exception as e:
        print(f"批量处理测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_batch_process()
