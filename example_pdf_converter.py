#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF转换器使用示例

演示如何使用pdf2image PDF转换器
"""

from pathlib import Path
from src.pipeline.pdf_converter import PDFConverter

def main():
    """主函数"""
    # 配置参数
    config = {
        'dpi': 300,
        'format': 'PNG',
        'quality': 95,
        'poppler_path': None,  # Windows用户可能需要设置
        'use_cairo': True,
        'single_thread': True
    }
    
    # 创建转换器
    converter = PDFConverter(config)
    
    # 显示转换器信息
    print("PDF转换器信息:")
    info = converter.get_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    # 示例PDF文件路径
    pdf_path = "太极计划星间激光通信测距的伪随机码选取.pdf"
    
    if not Path(pdf_path).exists():
        print(f"PDF文件不存在: {pdf_path}")
        return
    
    try:
        # 获取页数
        page_count = converter.get_page_count(pdf_path)
        print(f"\nPDF页数: {page_count}")
        
        # 转换PDF为图像
        print(f"\n开始转换PDF...")
        images = converter.convert_pdf_to_images(pdf_path)
        print(f"转换完成，共 {len(images)} 页")
        
        # 显示图像信息
        for i, img in enumerate(images):
            print(f"  页面 {i+1}: {img.size} ({img.mode})")
        
        # 保存图像
        output_dir = "output/pdf_images"
        saved_paths = converter.save_images(images, output_dir, "page")
        print(f"\n图像已保存到: {output_dir}")
        print(f"保存的文件:")
        for path in saved_paths:
            print(f"  {path}")
            
        # 转换单页示例
        print(f"\n转换单页示例:")
        single_page = converter.convert_single_page(pdf_path, 0)
        print(f"第1页: {single_page.size} ({single_page.mode})")
        
        # 保存单页
        single_page.save("output/single_page.png")
        print("单页已保存为: output/single_page.png")
        
    except Exception as e:
        print(f"转换失败: {e}")


if __name__ == "__main__":
    main()
