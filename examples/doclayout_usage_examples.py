"""
DocLayout版式分析器使用示例
演示如何使用doclayout_yolo模型进行文档版式分析
"""

import cv2
import numpy as np
from pathlib import Path
import yaml

from src.pipeline.layout_analyzer import DocLayoutAnalyzer
from src.config.settings import LayoutAnalyzerConfig

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


def load_config_from_yaml(config_path: str = "config.yaml") -> LayoutAnalyzerConfig:
    """从YAML文件加载配置"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)
        
        layout_config = config_dict.get('layout_analyzer', {})
        
        # 创建配置对象
        config = LayoutAnalyzerConfig(
            model_path=layout_config.get('model_path', 'doclayout.pt'),
            model_type=layout_config.get('model_type', 'doclayout'),
            confidence_threshold=layout_config.get('confidence_threshold', 0.4),
            iou_threshold=layout_config.get('iou_threshold', 0.45),
            use_gpu=layout_config.get('use_gpu', True),
            batch_size=layout_config.get('batch_size', 1),
            input_size=layout_config.get('input_size', 1024),
            max_det=layout_config.get('max_det', 300),
            min_region_area=layout_config.get('min_region_area', 50.0),
            merge_nearby_regions=layout_config.get('merge_nearby_regions', True),
            sort_by_reading_order=layout_config.get('sort_by_reading_order', True),
            visualization_enabled=layout_config.get('visualization_enabled', True),
            show_confidence=layout_config.get('show_confidence', True),
            show_class_names=layout_config.get('show_class_names', True),
            bbox_thickness=layout_config.get('bbox_thickness', 2)
        )
        
        return config
        
    except Exception as e:
        logger.error(f"加载配置失败: {e}")
        # 返回默认配置
        return LayoutAnalyzerConfig()


def example_single_image_analysis():
    """单张图片版式分析示例"""
    logger.info("=== 单张图片版式分析示例 ===")
    
    # 加载配置
    config = load_config_from_yaml()
    
    # 创建分析器
    analyzer = DocLayoutAnalyzer(config)
    
    # 测试图片路径（需要替换为实际的图片路径）
    image_path = "test_image.png"  # 替换为实际图片路径
    
    # 检查图片是否存在
    if not Path(image_path).exists():
        logger.warning(f"测试图片不存在: {image_path}")
        logger.info("请将PDF转换为图片后再运行此示例")
        return
    
    try:
        # 执行版式分析
        elements = analyzer.analyze_layout(image_path, page_num=0)
        
        # 打印分析结果
        logger.info(f"检测到 {len(elements)} 个版式元素:")
        for i, element in enumerate(elements):
            logger.info(f"  元素 {i+1}: {element.type}, "
                       f"置信度: {element.confidence:.3f}, "
                       f"边界框: {element.bbox}, "
                       f"面积: {element.area:.0f}")
        
        # 获取统计信息
        stats = analyzer.get_layout_statistics(elements)
        logger.info(f"统计信息: {stats}")
        
        # 可视化结果
        output_path = "layout_analysis_result.jpg"
        annotated_image = analyzer.visualize_layout(image_path, elements, output_path)
        logger.info(f"可视化结果已保存到: {output_path}")
        
        # 按类型筛选元素
        title_elements = analyzer.get_elements_by_type(elements, "Title")
        plaintext_elements = analyzer.get_elements_by_type(elements, "PlainText")
        figure_elements = analyzer.get_elements_by_type(elements, "Figure")
        table_elements = analyzer.get_elements_by_type(elements, "Table")
        formula_elements = analyzer.get_elements_by_type(elements, "IsolateFormula")
        
        logger.info(f"标题元素: {len(title_elements)} 个")
        logger.info(f"普通文本元素: {len(plaintext_elements)} 个")
        logger.info(f"图片元素: {len(figure_elements)} 个")
        logger.info(f"表格元素: {len(table_elements)} 个")
        logger.info(f"公式元素: {len(formula_elements)} 个")
        
    except Exception as e:
        logger.error(f"版式分析失败: {e}")


def example_batch_analysis():
    """批量图片版式分析示例"""
    logger.info("=== 批量图片版式分析示例 ===")
    
    # 加载配置
    config = load_config_from_yaml()
    
    # 创建分析器
    analyzer = DocLayoutAnalyzer(config)
    
    # 测试图片列表（需要替换为实际的图片路径）
    image_paths = [
        "page_1.png",
        "page_2.png", 
        "page_3.png"
    ]
    
    # 过滤存在的图片
    existing_images = [path for path in image_paths if Path(path).exists()]
    
    if not existing_images:
        logger.warning("没有找到测试图片")
        logger.info("请将PDF转换为图片后再运行此示例")
        return
    
    try:
        # 批量分析
        results = analyzer.analyze_batch(existing_images)
        
        # 打印结果
        for image_path, elements in results.items():
            logger.info(f"图片 {image_path}: 检测到 {len(elements)} 个元素")
            
            # 生成可视化结果
            output_path = f"batch_result_{Path(image_path).stem}.jpg"
            analyzer.visualize_layout(image_path, elements, output_path)
        
    except Exception as e:
        logger.error(f"批量分析失败: {e}")


def example_custom_config():
    """自定义配置示例"""
    logger.info("=== 自定义配置示例 ===")
    
    # 创建自定义配置
    custom_config = LayoutAnalyzerConfig(
        model_path="doclayout.pt",
        confidence_threshold=0.3,  # 降低置信度阈值
        use_gpu=True,
        visualization_enabled=True,
        show_confidence=True
    )
    
    # 创建分析器
    analyzer = DocLayoutAnalyzer(custom_config)
    
    logger.info(f"自定义配置置信度阈值: {custom_config.confidence_threshold}")
    logger.info(f"类别映射: {analyzer.category_mapping}")
    
    # 测试图片路径
    image_path = "test_image.png"  # 替换为实际的图片路径
    
    if Path(image_path).exists():
        try:
            # 执行分析
            elements = analyzer.analyze_layout(image_path)
            
            # 生成可视化结果
            output_path = "custom_analysis_result.jpg"
            analyzer.visualize_layout(image_path, elements, output_path)
            
            logger.info(f"自定义配置分析完成，检测到 {len(elements)} 个元素")
            
        except Exception as e:
            logger.error(f"自定义配置分析失败: {e}")
    else:
        logger.warning(f"测试图片不存在: {image_path}")


def example_direct_doclayout_usage():
    """直接使用doclayout_yolo的示例（按照用户提供的方法）"""
    logger.info("=== 直接使用doclayout_yolo示例 ===")
    
    try:
        from doclayout_yolo import YOLOv10
        
        # Load the pre-trained model
        model = YOLOv10("doclayout.pt")
        
        # 测试图片路径
        image_path = "test_image.png"  # 替换为实际图片路径
        
        if not Path(image_path).exists():
            logger.warning(f"测试图片不存在: {image_path}")
            return
        
        # Perform prediction
        det_res = model.predict(
            image_path,     # Image to predict
            imgsz=1024,     # Prediction image size
            conf=0.2,       # Confidence threshold
            device="cuda:0" # Device to use (e.g., 'cuda:0' or 'cpu')
        )
        
        # Annotate and save the result
        annotated_frame = det_res[0].plot(pil=True, line_width=5, font_size=20)
        
        # 转换PIL图像为OpenCV格式并保存
        annotated_cv = cv2.cvtColor(np.array(annotated_frame), cv2.COLOR_RGB2BGR)
        cv2.imwrite("direct_result.jpg", annotated_cv)
        
        logger.info("直接使用doclayout_yolo分析完成，结果保存为: direct_result.jpg")
        
        # 打印检测结果信息
        if det_res and len(det_res) > 0:
            result = det_res[0]
            if hasattr(result, 'boxes') and result.boxes is not None:
                num_detections = len(result.boxes)
                logger.info(f"检测到 {num_detections} 个对象")
            else:
                logger.info("未检测到对象")
        
    except ImportError:
        logger.error("doclayout_yolo未安装，请先安装: pip install doclayout_yolo")
    except Exception as e:
        logger.error(f"直接使用doclayout_yolo失败: {e}")


if __name__ == "__main__":
    # 运行所有示例
    try:
        # 示例1: 单张图片分析
        example_single_image_analysis()
        
        print("\n" + "="*50 + "\n")
        
        # 示例2: 批量分析
        example_batch_analysis()
        
        print("\n" + "="*50 + "\n")
        
        # 示例3: 自定义配置
        example_custom_config()
        
        print("\n" + "="*50 + "\n")
        
        # 示例4: 直接使用doclayout_yolo
        example_direct_doclayout_usage()
        
    except Exception as e:
        logger.error(f"运行示例失败: {e}")
