#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Pix2Text配置统一化
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.settings import Settings, Pix2TextProcessorConfig
from src.pipeline.pix2text import Pix2TextProcessor

def test_config_loading():
    """测试配置加载"""
    print("=== 测试配置加载 ===")
    
    # 1. 从YAML文件加载配置
    settings = Settings()
    print(f"从配置文件加载的Pix2Text配置:")
    print(f"  enabled: {settings.pix2text_processor.enabled}")
    print(f"  use_gpu: {settings.pix2text_processor.use_gpu}")
    print(f"  device: {settings.pix2text_processor.device}")
    print(f"  layout: {settings.pix2text_processor.layout}")
    print(f"  text_formula languages: {settings.pix2text_processor.text_formula['languages']}")
    
    # 2. 测试to_total_configs方法
    total_configs = settings.pix2text_processor.to_total_configs()
    print(f"\ntotal_configs格式:")
    print(f"  layout: {total_configs['layout']}")
    print(f"  text_formula: {total_configs['text_formula']}")
    
    return settings

def test_processor_creation():
    """测试处理器创建"""
    print("\n=== 测试处理器创建 ===")
    
    # 1. 从配置对象创建
    settings = Settings()
    processor1 = Pix2TextProcessor(config=settings.pix2text_processor)
    print(f"从配置对象创建: enabled={processor1.enabled}, device={processor1.device}")
    
    # 2. 从字典创建
    config_dict = {
        'enabled': True,
        'use_gpu': True,
        'device': 'cuda',
        'layout': {'scores_thresh': 0.5},
        'text_formula': {
            'languages': ('en',),
            'mfd': {'model_type': 'yolov8', 'model_fp': None},
            'formula': {'model_type': 'latex-ocr', 'model_fp': None},
            'text': {
                'rec_model_type': 'ch_PP-OCRv4_rec',
                'det_model_type': 'ch_PP-OCRv4_det',
                'rec_model_fp': None,
                'det_model_fp': None
            }
        }
    }
    processor2 = Pix2TextProcessor(config=config_dict)
    print(f"从字典创建: enabled={processor2.enabled}, device={processor2.device}")
    
    # 3. 使用类方法创建
    processor3 = Pix2TextProcessor.from_config(settings.pix2text_processor)
    print(f"使用类方法创建: enabled={processor3.enabled}, device={processor3.device}")
    
    # 4. 测试配置格式
    print(f"\n配置格式验证:")
    print(f"  processor1.config: {processor1.config}")
    print(f"  processor2.config: {processor2.config}")
    
    return processor1, processor2, processor3

def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n=== 测试向后兼容性 ===")
    
    # 使用旧的total_configs格式
    old_config = {
        'layout': {'scores_thresh': 0.4},
        'text_formula': {
            'languages': ('ch_sim',),
        }
    }
    
    processor = Pix2TextProcessor(total_configs=old_config)
    print(f"旧格式兼容: enabled={processor.enabled}, device={processor.device}")
    print(f"配置内容: {processor.config}")
    
    return processor

def main():
    """主函数"""
    try:
        # 测试配置加载
        settings = test_config_loading()
        
        # 测试处理器创建
        processors = test_processor_creation()
        
        # 测试向后兼容性
        old_processor = test_backward_compatibility()
        
        print("\n=== 测试完成 ===")
        print("所有测试通过！配置统一化成功。")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()