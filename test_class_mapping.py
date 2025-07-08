#!/usr/bin/env python3
"""测试类别映射"""

import sys
sys.path.append('.')

from src.pipeline.layout_analyzer import LayoutAnalyzer
from src.config.settings import load_config

def test_class_mapping():
    config = load_config('config.yaml')
    analyzer = LayoutAnalyzer(config.layout_analyzer)
    
    print("DocLayout YOLO类别映射测试：")
    print("=" * 50)
    
    for i, name in enumerate(analyzer.class_names):
        region_type = analyzer._map_to_region_type(name)
        print(f"{i}: {name:<15} -> {region_type}")
    
    print("\n舍弃内容（返回None）:")
    abandon_types = ['Abandon', 'Figure', 'FigureCaption', 'TableFootnote', 'FormulaCaption']
    for name in abandon_types:
        region_type = analyzer._map_to_region_type(name)
        if region_type is None:
            print(f"✓ {name} 正确舍弃")
        else:
            print(f"✗ {name} 应该舍弃但返回了 {region_type}")

if __name__ == "__main__":
    test_class_mapping()
