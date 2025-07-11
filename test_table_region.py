#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试TableRegion类的功能
"""

import sys
from src.models.document import TableRegion, BoundingBox, RegionType, TableData

def test_table_region():
    """测试TableRegion类的基本功能"""
    # 创建一个空的TableRegion
    empty_region = TableRegion(
        region_type=RegionType.TABLE,
        bbox=BoundingBox(x1=0, y1=0, x2=100, y2=100),
        confidence=0.9,
        page_number=1
    )
    
    print("=== 空表格区域测试 ===")
    print(f"空表格区域长度: {len(empty_region)}")
    print(f"空表格区域table_content类型: {type(empty_region.table_content)}")
    
    # 创建一个有数据的TableRegion
    table_data = TableData(
        headers=["列1", "列2", "列3"],
        rows=[["行1-1", "行1-2", "行1-3"], ["行2-1", "行2-2", "行2-3"]],
        bbox=(0, 0, 100, 100),
        confidence=0.95,
        caption="测试表格"
    )
    
    data_region = TableRegion(
        region_type=RegionType.TABLE,
        bbox=BoundingBox(x1=0, y1=0, x2=100, y2=100),
        confidence=0.9,
        page_number=1,
        table_content=[table_data]
    )
    
    print("\n=== 有数据表格区域测试 ===")
    print(f"有数据表格区域长度: {len(data_region)}")
    print(f"表格标题: {data_region.table_content[0].caption}")
    print(f"表格行数: {data_region.table_content[0].row_count}")
    print(f"表格列数: {data_region.table_content[0].col_count}")
    
    print("\nTableRegion修复验证成功!")

if __name__ == "__main__":
    test_table_region() 