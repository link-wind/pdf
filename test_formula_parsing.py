#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试公式解析功能
"""

import os
import sys
from pathlib import Path
import tempfile

from loguru import logger

from src import load_config
from src.pipeline.formula_parser import FormulaParser
from src.models.document import FormulaRegion, BoundingBox, RegionType
from PIL import Image

def setup_logger(verbose=False):
    """配置日志记录器"""
    log_level = "DEBUG" if verbose else "INFO"
    logger.remove()  # 移除默认处理器
    logger.add(sys.stderr, level=log_level)


def find_sample_formula_image():
    """查找示例公式图片"""
    # 尝试在常见位置查找公式图像
    possible_paths = [
        "data/samples/formulas",
        "data/input/samples",
        "data/test",
        "samples"
    ]
    
    for base_path in possible_paths:
        if not os.path.exists(base_path):
            continue
        
        path = Path(base_path)
        # 查找所有图片文件
        images = list(path.glob("*.png")) + list(path.glob("*.jpg")) + list(path.glob("*.jpeg"))
        
        if images:
            return str(images[0])
    
    # 如果没有找到图片，创建一个示例图片进行测试
    logger.warning("未找到示例公式图像，将创建一个测试图像")
    
    # 创建一个临时图像用于测试
    temp_img_path = os.path.join(tempfile.gettempdir(), "test_formula.png")
    
    # 创建一个简单的图像
    img = Image.new('RGB', (500, 200), color=(255, 255, 255))
    img.save(temp_img_path)
    
    logger.info(f"创建测试图像: {temp_img_path}")
    return temp_img_path


def test_formula_parsing():
    """测试公式解析功能"""
    # 加载配置
    config = load_config("config.yaml")
    
    # 初始化公式解析器
    formula_parser = FormulaParser(config.formula_parser)
    
    # 查找示例公式图像
    image_path = find_sample_formula_image()
    logger.info(f"使用公式图像: {image_path}")
    
    # 创建一个模拟的公式区域
    formula_region = FormulaRegion(
        region_type=RegionType.FORMULA,
        bbox=BoundingBox(x1=0, y1=0, x2=500, y2=200),
        confidence=0.9,
        page_number=1
    )
    
    # 添加页面图像信息
    formula_region.page_path = image_path
    try:
        with Image.open(image_path) as page_img:
            formula_region.page_image = page_img.copy()
    except Exception as e:
        logger.warning(f"加载页面图像失败: {e}")
        formula_region.page_image = None
    
    # 测试公式解析
    logger.info("开始解析公式...")
    result = formula_parser.parse(formula_region)
    
    # 打印结果
    if result and len(result) > 0:
        logger.info("公式解析成功!")
        for i, formula_data in enumerate(result):
            logger.info(f"公式 #{i+1}:")
            logger.info(f"LaTeX: {formula_data.latex}")
            logger.info(f"置信度: {formula_data.confidence}")
    else:
        logger.warning("公式解析失败或未返回内容")
    
    return result


if __name__ == "__main__":
    # 设置日志
    setup_logger(verbose=True)
    
    # 测试公式解析
    logger.info("开始测试公式解析功能...")
    result = test_formula_parsing()
    
    logger.info("测试完成") 