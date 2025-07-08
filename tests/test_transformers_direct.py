#!/usr/bin/env python3
"""
测试直接使用AutoModel.from_pretrained加载360LayoutAnalysis模型
"""

import sys
import os
from pathlib import Path
import traceback
from PIL import Image
import torch

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

from src.config.settings import LayoutAnalyzerConfig
from src.pipeline.layout_analyzer import LayoutAnalyzer


def test_direct_transformers_loading():
    """测试直接使用AutoModel.from_pretrained加载模型"""
    
    logger.info("测试直接使用AutoModel.from_pretrained加载360LayoutAnalysis模型")
    logger.info("=" * 60)
    
    try:
        # 1. 检查环境
        logger.info("检查环境...")
        logger.info(f"Python版本: {sys.version}")
        logger.info(f"PyTorch版本: {torch.__version__}")
        logger.info(f"CUDA可用: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            logger.info(f"CUDA版本: {torch.version.cuda}")
            logger.info(f"GPU设备: {torch.cuda.get_device_name(0)}")
        
        # 2. 创建配置（强制使用Transformers）
        config = LayoutAnalyzerConfig()
        config.model_path = None  # 设置为None强制使用Transformers
        config.confidence_threshold = 0.5
        config.use_gpu = torch.cuda.is_available()
        
        logger.info("配置信息:")
        logger.info(f"  - 模型路径: {config.model_path}")
        logger.info(f"  - 置信度阈值: {config.confidence_threshold}")
        logger.info(f"  - 使用GPU: {config.use_gpu}")
        
        # 3. 初始化分析器
        logger.info("\n正在初始化版式分析器...")
        analyzer = LayoutAnalyzer(config)
        
        # 4. 获取模型信息
        model_info = analyzer.get_model_info()
        logger.info("\n模型信息:")
        for key, value in model_info.items():
            logger.info(f"  - {key}: {value}")
        
        # 5. 创建测试图像
        logger.info("\n创建测试图像...")
        test_image = create_test_image()
        
        # 保存测试图像
        test_output_dir = project_root / "test_output"
        test_output_dir.mkdir(exist_ok=True)
        test_image_path = test_output_dir / "test_image_direct_transformers.png"
        test_image.save(test_image_path)
        logger.info(f"测试图像保存到: {test_image_path}")
        
        # 6. 进行版式分析
        logger.info("\n开始版式分析...")
        import time
        start_time = time.time()
        
        page_layout = analyzer.analyze(test_image, page_num=0)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 7. 输出结果
        logger.info("\n版式分析完成！")
        logger.info(f"处理时间: {processing_time:.3f}秒")
        logger.info(f"页面尺寸: {page_layout.width}x{page_layout.height}")
        logger.info(f"文本区域: {len(page_layout.text_regions)}个")
        logger.info(f"表格区域: {len(page_layout.table_regions)}个")
        logger.info(f"公式区域: {len(page_layout.formula_regions)}个")
        logger.info(f"图像区域: {len(page_layout.image_regions)}个")
        
        # 8. 详细输出区域信息
        all_regions = page_layout.all_regions
        logger.info(f"\n总共检测到 {len(all_regions)} 个区域:")
        
        for i, region in enumerate(all_regions):
            logger.info(f"  区域 {i+1}: {region.region_type.value}, "
                       f"位置: ({region.bbox.x1:.1f}, {region.bbox.y1:.1f}, "
                       f"{region.bbox.x2:.1f}, {region.bbox.y2:.1f}), "
                       f"置信度: {region.confidence:.3f}")
        
        # 9. 生成可视化结果
        logger.info("\n生成可视化结果...")
        vis_path = test_output_dir / "layout_analysis_direct_transformers.png"
        vis_image = analyzer.visualize_layout(test_image, page_layout, str(vis_path))
        
        if vis_image:
            logger.info(f"可视化结果保存到: {vis_path}")
        else:
            logger.warning("可视化生成失败")
        
        # 10. 保存详细分析结果
        result_path = test_output_dir / "direct_transformers_analysis_result.txt"
        save_analysis_result(result_path, model_info, page_layout, all_regions, processing_time)
        logger.info(f"分析结果保存到: {result_path}")
        
        logger.info("\n✅ 直接Transformers模型加载测试完成!")
        return True
        
    except Exception as e:
        logger.error(f"\n❌ 测试失败: {str(e)}")
        logger.error(traceback.format_exc())
        return False


def create_test_image():
    """创建测试图像"""
    # 创建一个更大的测试图像
    image = Image.new('RGB', (1200, 800), color='white')
    
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(image)
    
    # 尝试使用默认字体
    try:
        font = ImageFont.load_default()
    except:
        font = None
    
    # 绘制不同类型的区域
    regions = [
        # 标题
        {'bbox': (50, 50, 1150, 120), 'color': 'lightblue', 'text': '测试文档标题', 'label': 'Title'},
        # 作者信息
        {'bbox': (50, 140, 1150, 180), 'color': 'lightgray', 'text': '作者信息和日期', 'label': 'Header'},
        # 摘要
        {'bbox': (50, 200, 1150, 300), 'color': 'lightgreen', 'text': '摘要内容区域', 'label': 'Abstract'},
        # 正文左栏
        {'bbox': (50, 320, 570, 650), 'color': 'lightyellow', 'text': '正文左栏内容', 'label': 'Text'},
        # 正文右栏
        {'bbox': (590, 320, 1150, 650), 'color': 'lightyellow', 'text': '正文右栏内容', 'label': 'Text'},
        # 表格
        {'bbox': (50, 670, 570, 750), 'color': 'lightcoral', 'text': '表格区域', 'label': 'Table'},
        # 图像
        {'bbox': (590, 670, 1150, 750), 'color': 'lightpink', 'text': '图像区域', 'label': 'Figure'},
        # 页脚
        {'bbox': (50, 760, 1150, 790), 'color': 'lightgray', 'text': '页脚信息', 'label': 'Footer'},
    ]
    
    for region in regions:
        # 绘制区域背景
        draw.rectangle(region['bbox'], fill=region['color'], outline='black', width=2)
        
        # 添加文本
        if font:
            text_x = region['bbox'][0] + 10
            text_y = region['bbox'][1] + 10
            draw.text((text_x, text_y), region['text'], fill='black', font=font)
            
            # 添加标签
            label_y = text_y + 20
            draw.text((text_x, label_y), f"[{region['label']}]", fill='darkblue', font=font)
    
    return image


def save_analysis_result(result_path: Path, model_info: dict, page_layout, all_regions: list, processing_time: float):
    """保存分析结果"""
    with open(result_path, 'w', encoding='utf-8') as f:
        f.write("360LayoutAnalysis 直接Transformers模型测试结果\n")
        f.write("=" * 60 + "\n\n")
        
        f.write("模型信息:\n")
        f.write("-" * 30 + "\n")
        for key, value in model_info.items():
            f.write(f"{key}: {value}\n")
        f.write("\n")
        
        f.write("分析结果:\n")
        f.write("-" * 30 + "\n")
        f.write(f"处理时间: {processing_time:.3f}秒\n")
        f.write(f"页面尺寸: {page_layout.width}x{page_layout.height}\n")
        f.write(f"总区域数: {len(all_regions)}\n")
        f.write(f"文本区域: {len(page_layout.text_regions)}个\n")
        f.write(f"表格区域: {len(page_layout.table_regions)}个\n")
        f.write(f"公式区域: {len(page_layout.formula_regions)}个\n")
        f.write(f"图像区域: {len(page_layout.image_regions)}个\n\n")
        
        f.write("区域详情:\n")
        f.write("-" * 30 + "\n")
        for i, region in enumerate(all_regions):
            f.write(f"区域 {i+1}:\n")
            f.write(f"  类型: {region.region_type.value}\n")
            f.write(f"  位置: ({region.bbox.x1:.1f}, {region.bbox.y1:.1f}, "
                   f"{region.bbox.x2:.1f}, {region.bbox.y2:.1f})\n")
            f.write(f"  置信度: {region.confidence:.3f}\n")
            f.write(f"  面积: {region.bbox.area:.1f}\n")
            f.write(f"  阅读顺序: {region.reading_order}\n\n")


def test_model_direct_loading():
    """直接测试模型加载"""
    logger.info("直接测试AutoModel.from_pretrained加载...")
    
    try:
        from transformers import AutoModel
        
        logger.info("正在加载模型...")
        model = AutoModel.from_pretrained("qihoo360/360LayoutAnalysis")
        
        logger.info("✅ 模型加载成功!")
        logger.info(f"模型类型: {type(model)}")
        logger.info(f"模型设备: {next(model.parameters()).device}")
        
        # 测试模型属性
        logger.info("模型属性:")
        for attr in dir(model):
            if not attr.startswith('_'):
                logger.info(f"  - {attr}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 直接模型加载失败: {str(e)}")
        logger.error(traceback.format_exc())
        return False


def main():
    """主函数"""
    logger.info("360LayoutAnalysis 直接Transformers模型测试")
    logger.info("=" * 60)
    
    # 测试1: 直接模型加载
    logger.info("\n测试1: 直接模型加载")
    success1 = test_model_direct_loading()
    
    # 测试2: 完整功能测试
    logger.info("\n测试2: 完整功能测试")
    success2 = test_direct_transformers_loading()
    
    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("测试总结")
    logger.info("=" * 60)
    
    if success1:
        logger.info("✅ 直接模型加载: 成功")
    else:
        logger.info("❌ 直接模型加载: 失败")
    
    if success2:
        logger.info("✅ 完整功能测试: 成功")
    else:
        logger.info("❌ 完整功能测试: 失败")
    
    if success1 or success2:
        logger.info("🎉 至少一个测试成功，系统基本可用！")
        return 0
    else:
        logger.error("💥 所有测试都失败，请检查环境配置！")
        return 1


if __name__ == "__main__":
    sys.exit(main())
