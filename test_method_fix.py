#!/usr/bin/env python3
"""验证方法名修复"""

import sys
sys.path.append('.')

def test_method_names():
    """测试方法名是否正确"""
    try:
        from src.pipeline.ocr_processor import OCRProcessor
        from src.pipeline.reading_order import ReadingOrderAnalyzer
        from src.config.settings import load_config
        
        print("✓ 模块导入成功")
        
        config = load_config('config.yaml')
        print("✓ 配置加载成功")
        
        # 测试OCRProcessor
        ocr = OCRProcessor(config.ocr_processor)
        if hasattr(ocr, 'process_region'):
            print("✓ OCRProcessor.process_region 方法存在")
        else:
            print("✗ OCRProcessor.process_region 方法不存在")
            
        # 测试ReadingOrderAnalyzer  
        reading_order = ReadingOrderAnalyzer(config.reading_order)
        if hasattr(reading_order, 'analyze_reading_order'):
            print("✓ ReadingOrderAnalyzer.analyze_reading_order 方法存在")
        else:
            print("✗ ReadingOrderAnalyzer.analyze_reading_order 方法不存在")
            
        print("\n方法名修复验证完成!")
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_method_names()
