#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
阅读顺序可视化测试脚本

功能：
1. 可视化显示PDF页面的区域检测结果
2. 标注LayoutLMv3预测的阅读顺序
3. 对比不同阅读顺序算法的效果
4. 生成测试报告图片
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_agg import FigureCanvasAgg

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from src import PDFPipeline, load_config
from src.models.document import Document, Page, Region, RegionType
from src.pipeline.reading_order import ReadingOrderAnalyzer


class ReadingOrderVisualizer:
    """阅读顺序可视化器"""
    
    def __init__(self, output_dir: str = "test_output"):
        """初始化可视化器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 定义颜色映射
        self.region_colors = {
            RegionType.TITLE: '#FF6B6B',           # 红色 - 标题
            RegionType.TEXT: '#4ECDC4',            # 青色 - 正文
            RegionType.TABLE: '#45B7D1',           # 蓝色 - 表格
            RegionType.FIGURE: '#96CEB4',          # 绿色 - 图片
            RegionType.IMAGE: '#96CEB4',           # 绿色 - 图片
            RegionType.FORMULA: '#FFEAA7',         # 黄色 - 公式
            RegionType.EQUATION: '#FFEAA7',        # 黄色 - 公式
            RegionType.CAPTION: '#DDA0DD',         # 紫色 - 标题
            RegionType.FIGURE_CAPTION: '#DDA0DD',  # 紫色 - 图标题
            RegionType.TABLE_CAPTION: '#DDA0DD',   # 紫色 - 表标题
            RegionType.HEADER: '#D3D3D3',          # 灰色 - 页眉
            RegionType.FOOTER: '#D3D3D3',          # 灰色 - 页脚
            RegionType.FOOTNOTE: '#FFA07A',        # 橙色 - 脚注
        }
        
        # 尝试加载字体
        self.font = self._load_font()
        
    def _load_font(self):
        """加载字体"""
        font_paths = [
            "C:/Windows/Fonts/simhei.ttf",    # 黑体
            "C:/Windows/Fonts/simsun.ttc",    # 宋体
            "C:/Windows/Fonts/msyh.ttc",      # 微软雅黑
            "/System/Library/Fonts/Arial.ttf", # macOS
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", # Linux
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, 20)
                except:
                    continue
        
        # 如果没有找到字体，使用默认字体
        return ImageFont.load_default()
    
    def visualize_page_reading_order(
        self,
        image_path: str,
        regions: List[Region],
        page_index: int = 0,
        title: str = "阅读顺序可视化"
    ) -> str:
        """可视化单页的阅读顺序
        
        Args:
            image_path: 页面图片路径
            regions: 区域列表
            page_index: 页面索引
            title: 图片标题
            
        Returns:
            str: 输出图片路径
        """
        # 读取原始图片
        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"无法读取图片: {image_path}")
            return ""
        
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        height, width = image.shape[:2]
        
        # 创建图形
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
        
        # 左侧：原始检测结果
        ax1.imshow(image)
        ax1.set_title(f"页面 {page_index + 1} - 区域检测结果", fontsize=14, fontweight='bold')
        ax1.axis('off')
        
        # 右侧：阅读顺序结果
        ax2.imshow(image)
        ax2.set_title(f"页面 {page_index + 1} - 阅读顺序结果", fontsize=14, fontweight='bold')
        ax2.axis('off')
        
        # 按阅读顺序排序区域
        sorted_regions = sorted(regions, key=lambda r: getattr(r, 'reading_order', 999))
        
        # 创建区域索引到阅读顺序的映射
        reading_order_map = {}
        for i, region in enumerate(sorted_regions):
            if hasattr(region, 'reading_order') and region.reading_order < 999:
                reading_order_map[region.reading_order] = i + 1
        
        for i, region in enumerate(regions):
            if not hasattr(region, 'bbox') or region.bbox is None:
                continue
                
            bbox = region.bbox
            x1, y1, x2, y2 = bbox.x1, bbox.y1, bbox.x2, bbox.y2
            
            # 获取区域类型和颜色
            region_type = region.region_type
            color = self.region_colors.get(region_type, '#FF69B4')
            
            # 在左侧显示检测框
            rect1 = patches.Rectangle(
                (x1, y1), x2 - x1, y2 - y1,
                linewidth=2, edgecolor=color, facecolor='none'
            )
            ax1.add_patch(rect1)
            
            # 添加区域类型标签
            type_text = region_type.value if hasattr(region_type, 'value') else str(region_type)
            ax1.text(x1, y1 - 5, f"{i+1}: {type_text}", 
                    fontsize=10, color=color, fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
            
            # 在右侧显示阅读顺序
            reading_order = getattr(region, 'reading_order', 999)
            
            # 根据阅读顺序调整颜色深度
            if reading_order < 999:
                # 使用渐变色表示阅读顺序
                order_ratio = reading_order / len(regions)
                alpha = 0.3 + 0.4 * (1 - order_ratio)  # 越早读的越深
            else:
                alpha = 0.1
            
            rect2 = patches.Rectangle(
                (x1, y1), x2 - x1, y2 - y1,
                linewidth=3, edgecolor=color, facecolor=color, alpha=alpha
            )
            ax2.add_patch(rect2)
            
            # 添加阅读顺序数字 - 显示顺序号而不是区域索引
            center_x, center_y = (x1 + x2) // 2, (y1 + y2) // 2
            
            # 查找该区域在阅读顺序中的位置（从1开始）
            display_order = reading_order_map.get(reading_order, "?")
            
            ax2.text(center_x, center_y, str(display_order), 
                    fontsize=16, color='red', fontweight='bold',
                    ha='center', va='center',
                    bbox=dict(boxstyle="circle,pad=0.3", facecolor='white', alpha=0.9))
        
        # 添加图例
        legend_elements = []
        for region_type, color in self.region_colors.items():
            type_name = region_type.value if hasattr(region_type, 'value') else str(region_type)
            legend_elements.append(patches.Patch(color=color, label=type_name))
        
        ax1.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1, 1))
        
        # 保存图片
        output_path = self.output_dir / f"reading_order_page_{page_index + 1}.png"
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"已保存页面 {page_index + 1} 的阅读顺序可视化: {output_path}")
        return str(output_path)
    
    def create_reading_order_report(
        self,
        document: Document,
        temp_dir: str,
        algorithm_info: Dict[str, Any]
    ) -> str:
        """创建阅读顺序分析报告
        
        Args:
            document: 文档对象
            temp_dir: 临时目录（包含页面图片）
            algorithm_info: 算法信息
            
        Returns:
            str: 报告文件路径
        """
        report_path = self.output_dir / "reading_order_report.html"
        
        # 生成每页的可视化图片
        image_paths = []
        temp_path = Path(temp_dir)
        
        for page_idx, page in enumerate(document.pages):
            # 查找对应的页面图片
            page_image = temp_path / f"page_{page_idx + 1}.png"
            if not page_image.exists():
                logger.warning(f"页面图片不存在: {page_image}")
                continue
            
            # 获取页面区域
            regions = []
            if hasattr(page, 'regions') and page.regions:
                regions = list(page.regions)
            elif hasattr(page, 'all_regions') and page.all_regions:
                regions = list(page.all_regions)
            
            if regions:
                image_path = self.visualize_page_reading_order(
                    str(page_image), regions, page_idx
                )
                if image_path:
                    image_paths.append((page_idx + 1, image_path))
        
        # 生成HTML报告
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>阅读顺序分析报告</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .info-table {{ margin: 20px 0; border-collapse: collapse; width: 100%; }}
                .info-table th, .info-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .info-table th {{ background-color: #f2f2f2; }}
                .page-section {{ margin: 30px 0; }}
                .page-title {{ font-size: 18px; font-weight: bold; margin-bottom: 10px; }}
                .page-image {{ max-width: 100%; height: auto; }}
                .legend {{ margin: 20px 0; }}
                .legend-item {{ display: inline-block; margin-right: 20px; }}
                .legend-color {{ display: inline-block; width: 20px; height: 20px; margin-right: 5px; vertical-align: middle; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>PDF阅读顺序分析报告</h1>
                <p>生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <h2>算法信息</h2>
            <table class="info-table">
                <tr><th>算法类型</th><td>{algorithm_info.get('algorithm', '未知')}</td></tr>
                <tr><th>模型路径</th><td>{algorithm_info.get('layout_reader_model_path', '未知')}</td></tr>
                <tr><th>设备</th><td>{algorithm_info.get('device', '未知')}</td></tr>
                <tr><th>最大区域数</th><td>{algorithm_info.get('max_regions', '未知')}</td></tr>
                <tr><th>LayoutLMv3可用</th><td>{'是' if algorithm_info.get('layoutlmv3_available', False) else '否'}</td></tr>
                <tr><th>Transformers可用</th><td>{'是' if algorithm_info.get('transformers_available', False) else '否'}</td></tr>
            </table>
            
            <h2>图例说明</h2>
            <div class="legend">
        """
        
        # 添加图例
        for region_type, color in self.region_colors.items():
            type_name = region_type.value if hasattr(region_type, 'value') else str(region_type)
            html_content += f'<div class="legend-item"><span class="legend-color" style="background-color: {color};"></span>{type_name}</div>'
        
        html_content += """
            </div>
            
            <h2>页面分析结果</h2>
        """
        
        # 添加每页的可视化结果
        for page_num, image_path in image_paths:
            rel_path = Path(image_path).name
            html_content += f"""
            <div class="page-section">
                <div class="page-title">页面 {page_num}</div>
                <img src="{rel_path}" alt="页面 {page_num} 阅读顺序" class="page-image">
            </div>
            """
        
        html_content += """
        </body>
        </html>
        """
        
        # 保存HTML报告
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"已生成阅读顺序分析报告: {report_path}")
        return str(report_path)
    
    def compare_reading_orders(
        self,
        image_path: str,
        regions_before: List[Region],
        regions_after: List[Region],
        page_index: int = 0
    ) -> str:
        """对比阅读顺序前后的效果
        
        Args:
            image_path: 页面图片路径
            regions_before: 处理前的区域列表
            regions_after: 处理后的区域列表
            page_index: 页面索引
            
        Returns:
            str: 对比图片路径
        """
        # 读取原始图片
        image = cv2.imread(image_path)
        if image is None:
            return ""
        
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 创建对比图形
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
        
        # 左侧：处理前
        ax1.imshow(image)
        ax1.set_title(f"页面 {page_index + 1} - 原始顺序", fontsize=14, fontweight='bold')
        ax1.axis('off')
        
        # 右侧：处理后
        ax2.imshow(image)
        ax2.set_title(f"页面 {page_index + 1} - LayoutLMv3优化后", fontsize=14, fontweight='bold')
        ax2.axis('off')
        
        # 绘制处理前的区域
        for i, region in enumerate(regions_before):
            if hasattr(region, 'bbox') and region.bbox:
                bbox = region.bbox
                x1, y1, x2, y2 = bbox.x1, bbox.y1, bbox.x2, bbox.y2
                
                rect = patches.Rectangle(
                    (x1, y1), x2 - x1, y2 - y1,
                    linewidth=2, edgecolor='blue', facecolor='none'
                )
                ax1.add_patch(rect)
                ax1.text(x1, y1 - 5, str(i + 1), fontsize=12, color='blue', fontweight='bold')
        
        # 绘制处理后的区域
        sorted_regions = sorted(regions_after, key=lambda r: getattr(r, 'reading_order', 999))
        for region in sorted_regions:
            if hasattr(region, 'bbox') and region.bbox:
                bbox = region.bbox
                x1, y1, x2, y2 = bbox.x1, bbox.y1, bbox.x2, bbox.y2
                reading_order = getattr(region, 'reading_order', 999)
                
                rect = patches.Rectangle(
                    (x1, y1), x2 - x1, y2 - y1,
                    linewidth=2, edgecolor='red', facecolor='none'
                )
                ax2.add_patch(rect)
                ax2.text(x1, y1 - 5, str(reading_order), fontsize=12, color='red', fontweight='bold')
        
        # 保存对比图
        output_path = self.output_dir / f"reading_order_comparison_page_{page_index + 1}.png"
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)


def test_reading_order_with_visualization(pdf_path: str, output_dir: str = "test_output"):
    """测试阅读顺序并生成可视化结果
    
    Args:
        pdf_path: PDF文件路径
        output_dir: 输出目录
    """
    logger.info(f"开始测试阅读顺序: {pdf_path}")
    
    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    try:
        # 初始化配置和管道
        config = load_config()
        pipeline = PDFPipeline(config)
        
        # 初始化可视化器
        visualizer = ReadingOrderVisualizer(output_dir)
        
        # 处理PDF
        logger.info("开始处理PDF...")
        result = pipeline.process(pdf_path)
        
        if not result.get('success', False):
            raise Exception(f"PDF处理失败: {result.get('error', 'Unknown error')}")
        
        document = result['document']
        
        # 获取临时目录路径
        pdf_name = Path(pdf_path).stem
        temp_dir = f"output/temp/{pdf_name}"
        
        # 获取算法信息
        algorithm_info = pipeline.processors['reading_order'].get_algorithm_info()
        
        # 生成可视化报告
        logger.info("生成可视化报告...")
        report_path = visualizer.create_reading_order_report(
            document, temp_dir, algorithm_info
        )
        
        # 生成统计信息
        total_pages = len(document.pages)
        total_regions = sum(len(page.regions) if hasattr(page, 'regions') and page.regions 
                          else len(page.all_regions) if hasattr(page, 'all_regions') and page.all_regions 
                          else 0 for page in document.pages)
        
        logger.info(f"测试完成!")
        logger.info(f"总页数: {total_pages}")
        logger.info(f"总区域数: {total_regions}")
        logger.info(f"可视化报告: {report_path}")
        logger.info(f"输出目录: {output_path.absolute()}")
        
        return report_path
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        raise


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="阅读顺序可视化测试")
    parser.add_argument("pdf_path", help="PDF文件路径")
    parser.add_argument("-o", "--output", default="output/test", help="输出目录")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    parser.add_argument("-b", "--batch", action="store_true", help="批量处理目录中的所有PDF")
    
    args = parser.parse_args()
    
    # 配置日志
    if args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    
    # 批量处理
    if args.batch and os.path.isdir(args.pdf_path):
        process_directory(args.pdf_path, args.output, args.verbose)
        return
    
    # 单文件处理
    # 检查文件是否存在
    if not os.path.exists(args.pdf_path):
        logger.error(f"PDF文件不存在: {args.pdf_path}")
        return
    
    # 运行测试
    try:
        report_path = test_reading_order_with_visualization(args.pdf_path, args.output)
        print(f"\n✅ 测试完成! 查看报告: {report_path}")
    except Exception as e:
        logger.error(f"测试失败: {e}")


def process_directory(directory_path: str, output_base: str, verbose: bool = False):
    """批量处理目录中的所有PDF文件
    
    Args:
        directory_path: PDF文件目录
        output_base: 输出基础目录
        verbose: 是否输出详细信息
    """
    pdf_files = [f for f in os.listdir(directory_path) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        logger.error(f"目录 {directory_path} 中没有PDF文件")
        return
    
    logger.info(f"找到 {len(pdf_files)} 个PDF文件")
    
    for i, pdf_file in enumerate(pdf_files):
        pdf_path = os.path.join(directory_path, pdf_file)
        pdf_name = os.path.splitext(pdf_file)[0]
        output_dir = os.path.join(output_base, pdf_name)
        
        logger.info(f"处理 [{i+1}/{len(pdf_files)}]: {pdf_file}")
        
        try:
            report_path = test_reading_order_with_visualization(pdf_path, output_dir)
            logger.info(f"完成 {pdf_file}，报告: {report_path}")
        except Exception as e:
            logger.error(f"处理 {pdf_file} 失败: {e}")
            if verbose:
                import traceback
                traceback.print_exc()


if __name__ == "__main__":
    main()
