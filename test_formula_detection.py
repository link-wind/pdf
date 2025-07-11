#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试LaTeX公式错误检测和大模型识别功能
"""

import sys
from loguru import logger
from pathlib import Path
import tempfile
from PIL import Image, ImageDraw, ImageFont
import os

from src import load_config
from src.pipeline.formula_parser import FormulaParser
from src.models.document import FormulaRegion, FormulaData, BoundingBox, RegionType


def setup_logger(verbose=False):
    """配置日志记录器"""
    log_level = "DEBUG" if verbose else "INFO"
    logger.remove()  # 移除默认处理器
    logger.add(sys.stderr, level=log_level)


def create_formula_image(latex_formula, width=400, height=100):
    """创建一个包含公式的测试图像"""
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # 尝试加载字体
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 16)
    except IOError:
        font = ImageFont.load_default()
    
    # 绘制公式文本（这只是模拟，实际上不是真正的公式渲染）
    draw.text((10, 40), f"Formula: {latex_formula}", fill=(0, 0, 0), font=font)
    
    return image


def test_formula_detection_and_llm():
    """测试公式错误检测和大模型识别功能"""
    # 加载配置
    config = load_config("config.yaml")
    
    # 确保启用LLM功能
    config.formula_parser.use_llm = True
    config.formula_parser.llm_fallback = True
    
    # 初始化公式解析器
    formula_parser = FormulaParser(config.formula_parser)
    
    # 测试用例 - 包含常见的Markdown渲染错误的公式
    test_cases = [
        # 未定义控制序列错误
        "\\Tilde{f}(x)",
        # 大写希腊字母错误
        "\\Alpha + \\Beta = \\Gamma",
        # 括号不匹配
        "\\frac{1}{2} + \\sqrt{x",
        # 环境不匹配
        "\\begin{array} a & b \\\\ c & d"
    ]
    
    # 测试每个用例
    for i, latex in enumerate(test_cases, 1):
        logger.info(f"测试用例 #{i}: {latex}")
        
        # 创建一个临时图像
        formula_image = create_formula_image(latex)
        
        # 创建临时文件保存图像
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                formula_image.save(tmp_file.name, 'PNG')
                temp_path = tmp_file.name
                
            # 创建公式区域对象
            formula_region = FormulaRegion(
                region_type=RegionType.FORMULA,
                bbox=BoundingBox(x1=0, y1=0, x2=400, y2=100),
                page_number=0,
                confidence=0.9,
                page_path=temp_path
            )
            
            # 手动添加错误的公式内容，用于测试错误检测
            formula_region.formula_content = [
                FormulaData(latex=latex, confidence=0.9)
            ]
            
            # 检查是否检测到错误
            has_error = formula_parser._has_latex_error(formula_region.formula_content)
            logger.info(f"检测到错误: {has_error}")
            
            if has_error:
                # 使用大模型解析
                logger.info("尝试使用大模型解析...")
                llm_result = formula_parser._parse_with_llm(formula_region)
                
                if llm_result and len(llm_result) > 0:
                    logger.info(f"大模型解析结果: {llm_result[0].latex}")
                else:
                    logger.warning("大模型解析失败")
            
            logger.info("-" * 50)
            
        finally:
            # 清理临时文件
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
    
    return True


if __name__ == "__main__":
    # 设置日志
    setup_logger(verbose=True)
    
    # 运行测试
    logger.info("开始测试公式错误检测和大模型识别功能...")
    test_formula_detection_and_llm()
    
    logger.info("测试完成") 