#!/usr/bin/env python3
"""测试区域检测和OCR识别的详细过程"""

import sys
import cv2
import numpy as np
from pathlib import Path
from PIL import Image

sys.path.append('.')

def test_region_ocr():
    """测试区域检测和OCR识别"""
    try:
        from src.pipeline.layout_analyzer import LayoutAnalyzer
        from src.pipeline.ocr_processor import OCRProcessor
        from src.config.settings import load_config
        from src.models.document import Region, RegionType, BoundingBox
        
        print("初始化处理器...")
        config = load_config('config.yaml')
        layout_analyzer = LayoutAnalyzer(config.layout_analyzer)
        ocr = OCRProcessor(config.ocr_processor)
        
        # 测试图片路径
        image_path = "output/temp/太极计划星间激光通信测距的伪随机码选取/page_001.png"
        
        if not Path(image_path).exists():
            print(f"测试图片不存在: {image_path}")
            return False
        
        print(f"加载测试图片: {image_path}")
        
        # 加载图片
        pil_image = Image.open(image_path)
        np_image = np.array(pil_image)
        
        print(f"图片尺寸: {np_image.shape}")
        
        # 进行版式分析
        print("\n=== 版式分析 ===")
        regions = layout_analyzer.analyze_layout(pil_image)
        print(f"检测到区域数量: {len(regions)}")
        
        # 筛选文本区域
        text_regions = []
        for region in regions:
            if region.region_type in [RegionType.TITLE, RegionType.TEXT]:
                text_regions.append(region)
        
        print(f"文本区域数量: {len(text_regions)}")
        
        # 对每个文本区域进行OCR识别
        print("\n=== OCR识别 ===")
        for i, region in enumerate(text_regions[:5]):  # 只测试前5个区域
            print(f"\n--- 区域 {i+1} ---")
            print(f"类型: {region.region_type}")
            print(f"边界框: {region.bbox}")
            print(f"区域大小: {region.bbox.width} x {region.bbox.height}")
            
            # 进行OCR识别
            ocr_result = ocr.process_region(region, np_image)
            
            print(f"OCR结果:")
            print(f"  内容长度: {len(ocr_result.get('content', ''))}")
            print(f"  文本块数量: {len(ocr_result.get('text_blocks', []))}")
            print(f"  置信度: {ocr_result.get('confidence', 0):.3f}")
            
            # 显示文本内容（前100个字符）
            content = ocr_result.get('content', '')
            if content:
                print(f"  内容预览: {content[:100]}...")
            else:
                print(f"  ⚠️  未识别到文本内容")
                
                # 调试：保存区域图片
                x1, y1, x2, y2 = region.bbox.x1, region.bbox.y1, region.bbox.x2, region.bbox.y2
                region_img = np_image[y1:y2, x1:x2]
                
                debug_path = f"debug_region_{i+1}.png"
                cv2.imwrite(debug_path, region_img)
                print(f"  调试图片已保存: {debug_path}")
        
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_region_ocr()
