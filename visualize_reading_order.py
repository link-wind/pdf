#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
阅读顺序可视化脚本 - 简化版

直接使用 ReadingOrderVisualizer 生成可视化图片，不进行完整的处理管道。

使用方法:
python visualize_reading_order.py <image_path> <json_path> <output_dir>
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.models.document import Region, BoundingBox, RegionType
    from test_reading_order_visualization import ReadingOrderVisualizer
except ImportError as e:
    logger.error(f"导入模块失败: {e}")
    sys.exit(1)


def load_regions_from_json(json_path: str) -> List[Region]:
    """从JSON文件加载区域信息
    
    Args:
        json_path: JSON文件路径
        
    Returns:
        List[Region]: 区域列表
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        regions = []
        
        # 处理不同格式的JSON
        if isinstance(data, list):
            # 直接的区域列表
            for i, region_data in enumerate(data):
                region = create_region_from_dict(region_data, i)
                if region:
                    regions.append(region)
        
        elif isinstance(data, dict):
            # 可能包含在pages或regions键中
            if 'regions' in data:
                for i, region_data in enumerate(data['regions']):
                    region = create_region_from_dict(region_data, i)
                    if region:
                        regions.append(region)
            
            elif 'pages' in data and len(data['pages']) > 0:
                page_data = data['pages'][0]  # 只处理第一页
                if 'regions' in page_data:
                    for i, region_data in enumerate(page_data['regions']):
                        region = create_region_from_dict(region_data, i)
                        if region:
                            regions.append(region)
        
        logger.info(f"从JSON加载了 {len(regions)} 个区域")
        return regions
    
    except Exception as e:
        logger.error(f"加载JSON失败: {e}")
        return []


def create_region_from_dict(region_data: Dict[str, Any], index: int) -> Region:
    """从字典创建区域对象
    
    Args:
        region_data: 区域数据字典
        index: 区域索引
        
    Returns:
        Region: 区域对象
    """
    try:
        # 处理边界框
        bbox = None
        if 'bbox' in region_data:
            bbox_data = region_data['bbox']
            if isinstance(bbox_data, dict) and all(k in bbox_data for k in ['x1', 'y1', 'x2', 'y2']):
                bbox = BoundingBox(
                    bbox_data['x1'], bbox_data['y1'],
                    bbox_data['x2'], bbox_data['y2']
                )
            elif isinstance(bbox_data, list) and len(bbox_data) >= 4:
                bbox = BoundingBox(
                    bbox_data[0], bbox_data[1],
                    bbox_data[2], bbox_data[3]
                )
        
        # 如果没有bbox，尝试使用坐标
        if bbox is None:
            if all(k in region_data for k in ['x1', 'y1', 'x2', 'y2']):
                bbox = BoundingBox(
                    region_data['x1'], region_data['y1'],
                    region_data['x2'], region_data['y2']
                )
        
        if bbox is None:
            logger.warning(f"区域 {index} 没有有效的边界框")
            return None
        
        # 处理区域类型
        region_type = RegionType.TEXT  # 默认文本类型
        if 'type' in region_data:
            type_str = region_data['type'].upper()
            try:
                for rt in RegionType:
                    if rt.name == type_str or rt.value == type_str:
                        region_type = rt
                        break
            except:
                pass
        
        # 创建区域对象
        region = Region(
            region_id=str(region_data.get('id', index)),
            bbox=bbox,
            region_type=region_type,
            content=region_data.get('content', ''),
            confidence=region_data.get('confidence', 1.0)
        )
        
        # 设置阅读顺序
        if 'reading_order' in region_data:
            region.reading_order = int(region_data['reading_order'])
        else:
            # 默认按索引排序
            region.reading_order = index + 1
        
        return region
    
    except Exception as e:
        logger.error(f"创建区域对象失败: {e}")
        return None


def visualize_reading_order(image_path: str, json_path: str, output_dir: str) -> str:
    """可视化阅读顺序
    
    Args:
        image_path: 图片路径
        json_path: JSON数据路径
        output_dir: 输出目录
        
    Returns:
        str: 输出图片路径
    """
    # 加载区域
    regions = load_regions_from_json(json_path)
    
    if not regions:
        logger.error("没有有效的区域")
        return ""
    
    # 创建可视化器
    visualizer = ReadingOrderVisualizer(output_dir)
    
    # 生成可视化图片
    output_path = visualizer.visualize_page_reading_order(
        image_path=image_path,
        regions=regions,
        page_index=0,
        title="阅读顺序可视化"
    )
    
    return output_path


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="简化的阅读顺序可视化")
    parser.add_argument("image_path", help="页面图片路径")
    parser.add_argument("json_path", help="区域JSON数据路径")
    parser.add_argument("-o", "--output", default="output/test", help="输出目录")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    # 配置日志
    if args.verbose:
        try:
            logger.remove()
            logger.add(sys.stderr, level="DEBUG")
        except:
            logger.setLevel(logging.DEBUG)
    
    # 检查文件是否存在
    if not os.path.exists(args.image_path):
        logger.error(f"图片文件不存在: {args.image_path}")
        return 1
    
    if not os.path.exists(args.json_path):
        logger.error(f"JSON文件不存在: {args.json_path}")
        return 1
    
    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)
    
    try:
        # 运行可视化
        logger.info(f"开始处理图片: {args.image_path}")
        logger.info(f"使用区域数据: {args.json_path}")
        logger.info(f"输出目录: {args.output}")
        
        output_path = visualize_reading_order(args.image_path, args.json_path, args.output)
        
        if output_path:
            logger.info(f"处理完成，输出图片: {output_path}")
            print(f"\n✅ 可视化完成! 查看图片: {output_path}")
            return 0
        else:
            logger.error("可视化失败")
            return 1
    
    except Exception as e:
        logger.error(f"可视化失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 