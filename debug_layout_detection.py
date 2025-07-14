#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版式分析调试工具
用于可视化检测结果，诊断标题等元素的边界框位置准确性
"""

import cv2
import numpy as np
from pathlib import Path
import argparse
from typing import List, Tuple

# 添加项目路径
import sys
sys.path.append(str(Path(__file__).parent))

from src.pipeline.layout_analyzer import LayoutAnalyzer
from src.config.settings import Settings
from src.models.document import Region, RegionType

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class LayoutDebugger:
    """版式分析调试器"""
    
    def __init__(self, config_path: str = None):
        """初始化调试器"""
        self.settings = Settings(config_path)
        self.analyzer = LayoutAnalyzer(self.settings.layout_analyzer)
        
        # 定义颜色映射（BGR格式）
        self.color_map = {
            RegionType.TITLE: (0, 0, 255),           # 红色 - 标题
            RegionType.PLAINTEXT: (0, 255, 0),       # 绿色 - 普通文本
            RegionType.FIGURE: (255, 0, 0),          # 蓝色 - 图片
            RegionType.TABLE: (0, 255, 255),         # 黄色 - 表格
            RegionType.ISOLATE_FORMULA: (255, 0, 255), # 紫色 - 公式
            RegionType.FIGURE_CAPTION: (128, 128, 0), # 深青色 - 图片标题
            RegionType.TABLE_CAPTION: (128, 0, 128),  # 深紫色 - 表格标题
            RegionType.FORMULA_CAPTION: (0, 128, 128), # 深黄色 - 公式标号
        }
        
    def analyze_and_visualize(self, image_path: str, output_path: str = None) -> Tuple[List[Region], np.ndarray]:
        """分析图像并可视化检测结果
        
        Args:
            image_path: 输入图像路径
            output_path: 输出图像路径，如果为None则不保存
            
        Returns:
            Tuple[List[Region], np.ndarray]: 检测到的区域列表和可视化图像
        """
        # 读取图像
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法读取图像: {image_path}")
            
        # 进行版式分析
        regions = self.analyzer.analyze_layout(image_path)
        
        # 创建可视化图像
        vis_image = self._draw_regions(image.copy(), regions)
        
        # 保存结果
        if output_path:
            cv2.imwrite(output_path, vis_image)
            logger.info(f"可视化结果已保存到: {output_path}")
            
        return regions, vis_image
    
    def _draw_regions(self, image: np.ndarray, regions: List[Region]) -> np.ndarray:
        """在图像上绘制检测区域
        
        Args:
            image: 输入图像
            regions: 检测到的区域列表
            
        Returns:
            np.ndarray: 绘制了检测框的图像
        """
        for i, region in enumerate(regions):
            # 获取边界框坐标
            bbox = region.bbox
            x1, y1, x2, y2 = int(bbox.x1), int(bbox.y1), int(bbox.x2), int(bbox.y2)
            
            # 获取颜色
            color = self.color_map.get(region.region_type, (128, 128, 128))  # 默认灰色
            
            # 绘制边界框
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
            
            # 准备标签文本
            label = f"{region.region_type.value}"
            if hasattr(region, 'confidence'):
                label += f" ({region.confidence:.2f})"
            
            # 计算文本尺寸
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            thickness = 1
            (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, thickness)
            
            # 绘制标签背景
            cv2.rectangle(image, 
                         (x1, y1 - text_height - baseline - 5), 
                         (x1 + text_width + 5, y1), 
                         color, -1)
            
            # 绘制标签文本
            cv2.putText(image, label, (x1 + 2, y1 - baseline - 2), 
                       font, font_scale, (255, 255, 255), thickness)
            
            # 在区域中心绘制序号
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            cv2.putText(image, str(i), (center_x - 10, center_y + 5), 
                       font, 0.8, (255, 255, 255), 2)
        
        return image
    
    def print_detection_summary(self, regions: List[Region], image_path: str):
        """打印检测结果摘要
        
        Args:
            regions: 检测到的区域列表
            image_path: 图像路径
        """
        print(f"\n=== 版式分析结果摘要 ===")
        print(f"图像: {image_path}")
        print(f"检测到的区域数量: {len(regions)}")
        print(f"置信度阈值: {self.settings.layout_analyzer.confidence_threshold}")
        print(f"IoU阈值: {self.settings.layout_analyzer.iou_threshold}")
        
        # 按类型统计
        type_counts = {}
        for region in regions:
            region_type = region.region_type
            type_counts[region_type] = type_counts.get(region_type, 0) + 1
        
        print("\n=== 按类型统计 ===")
        for region_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"{region_type.value}: {count}")
        
        # 详细信息
        print("\n=== 详细检测结果 ===")
        for i, region in enumerate(regions):
            bbox = region.bbox
            conf = getattr(region, 'confidence', 'N/A')
            print(f"{i:2d}. {region.region_type.value:15s} | "
                  f"位置: ({bbox.x1:4.0f},{bbox.y1:4.0f})-({bbox.x2:4.0f},{bbox.y2:4.0f}) | "
                  f"尺寸: {bbox.width:4.0f}x{bbox.height:4.0f} | "
                  f"置信度: {conf}")
        
        # 标题特别分析
        title_regions = [r for r in regions if r.region_type == RegionType.TITLE]
        if title_regions:
            print("\n=== 标题检测分析 ===")
            for i, title in enumerate(title_regions):
                bbox = title.bbox
                conf = getattr(title, 'confidence', 'N/A')
                aspect_ratio = bbox.width / bbox.height if bbox.height > 0 else 0
                print(f"标题 {i+1}: 位置({bbox.x1:.0f},{bbox.y1:.0f})-({bbox.x2:.0f},{bbox.y2:.0f}) | "
                      f"尺寸: {bbox.width:.0f}x{bbox.height:.0f} | "
                      f"宽高比: {aspect_ratio:.2f} | "
                      f"置信度: {conf}")
                
                # 检查可能的问题
                issues = []
                if conf != 'N/A' and conf < 0.6:
                    issues.append("置信度较低")
                if bbox.height < 20:
                    issues.append("高度过小")
                if aspect_ratio > 20:
                    issues.append("过于狭长")
                if bbox.width < 50:
                    issues.append("宽度过小")
                    
                if issues:
                    print(f"  ⚠️  潜在问题: {', '.join(issues)}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="版式分析调试工具")
    parser.add_argument("image_path", help="输入图像路径")
    parser.add_argument("-o", "--output", help="输出可视化图像路径")
    parser.add_argument("-c", "--config", help="配置文件路径")
    parser.add_argument("--show", action="store_true", help="显示可视化结果")
    
    args = parser.parse_args()
    
    # 检查输入文件
    if not Path(args.image_path).exists():
        print(f"错误: 输入图像不存在: {args.image_path}")
        return
    
    # 创建调试器
    debugger = LayoutDebugger(args.config)
    
    # 设置输出路径
    if args.output:
        output_path = args.output
    else:
        input_path = Path(args.image_path)
        output_path = str(input_path.parent / f"{input_path.stem}_debug{input_path.suffix}")
    
    try:
        # 分析并可视化
        regions, vis_image = debugger.analyze_and_visualize(args.image_path, output_path)
        
        # 打印摘要
        debugger.print_detection_summary(regions, args.image_path)
        
        # 显示结果
        if args.show:
            cv2.imshow("Layout Detection Debug", vis_image)
            print("\n按任意键关闭窗口...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            
    except Exception as e:
        logger.error(f"调试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()