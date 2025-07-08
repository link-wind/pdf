#!/usr/bin/env python3
"""测试OCR处理"""

import sys
import cv2
import numpy as np
from pathlib import Path
from PIL import Image

sys.path.append('.')

def test_ocr_simple():
    """测试OCR处理"""
    try:
        from src.pipeline.ocr_processor import OCRProcessor
        from src.config.settings import load_config
        from src.models.document import Region, RegionType, BoundingBox
        
        print("初始化OCR处理器...")
        config = load_config('config.yaml')
        ocr = OCRProcessor(config.ocr_processor)
        
        # 测试图片路径（选择第一页）
        image_path = "output/temp/太极计划星间激光通信测距的伪随机码选取/page_001.png"
        
        if not Path(image_path).exists():
            print(f"测试图片不存在: {image_path}")
            return False
        
        print(f"加载测试图片: {image_path}")
        image = cv2.imread(image_path)
        if image is None:
            print("无法读取图片")
            return False
        
        print(f"图片尺寸: {image.shape}")
        
        # 创建一个测试区域（整个图片的上半部分）
        height, width = image.shape[:2]
        test_bbox = BoundingBox(
            x1=50,
            y1=50, 
            x2=width-50,
            y2=height//2
        )
        
        test_region = Region(
            region_type=RegionType.TEXT,
            bbox=test_bbox,
            confidence=1.0,
            page_number=1
        )
        
        print(f"测试区域: {test_bbox}")
        print("开始OCR识别...")
        
        # 调用OCR处理
        result = ocr.process_region(test_region, image)
        
        print("OCR结果:")
        print(f"  content: {result.get('content', '')[:100]}...")
        print(f"  text_blocks数量: {len(result.get('text_blocks', []))}")
        print(f"  confidence: {result.get('confidence', 0)}")
        
        if result.get('content'):
            print("✓ OCR识别成功!")
            return True
        else:
            print("✗ OCR未识别到内容")
            return False
            
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_ocr_simple()
