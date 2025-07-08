"""模型适配器使用示例

展示如何使用模型适配器将现有模型适配到新的模型接口，并通过模型工厂进行管理
"""

import os
import sys
import torch
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from src.models import (
    ModelFactory,
    DocLayoutModelAdapter,
    LayoutReaderModelAdapter,
    FormulaModelAdapter,
    TableModelAdapter,
    OCRModelAdapter
)
from src.config import Settings


def demonstrate_model_adapters():
    """演示模型适配器的使用"""
    print("\n===== 模型适配器使用示例 =====")
    
    # 初始化配置
    settings = Settings()
    
    # 获取模型工厂实例
    factory = ModelFactory.get_instance()
    
    # 配置模型工厂缓存
    factory.configure_cache(max_models=3, enable_gpu_cache=True)
    
    print("\n1. 加载原始模型并创建适配器")
    
    # 加载DocLayout模型
    print("\n加载DocLayout模型...")
    doclayout_model = factory.get_model('doclayout', settings.layout_analyzer.model_path)
    
    # 创建DocLayout模型适配器
    doclayout_adapter = DocLayoutModelAdapter(doclayout_model)
    print(f"DocLayout适配器信息: {doclayout_adapter.get_model_info()}")
    
    # 演示预测方法
    print("\n模型适配器提供统一的预测接口:")
    print("doclayout_adapter.predict(image_path, conf=0.5, device='cuda:0')")
    
    # 加载LayoutReader模型
    print("\n加载LayoutReader模型...")
    layoutreader_model = factory.get_model('layoutreader', settings.reading_order.layoutreader_model_path)
    
    # 创建LayoutReader模型适配器
    layoutreader_adapter = LayoutReaderModelAdapter(layoutreader_model)
    print(f"LayoutReader适配器信息: {layoutreader_adapter.get_model_info()}")
    
    # 演示设备转移
    print("\n2. 模型设备管理")
    if torch.cuda.is_available():
        print("\n将模型转移到GPU:")
        layoutreader_adapter = layoutreader_adapter.to_device('cuda:0')
        print(f"转移后设备: {layoutreader_adapter.get_model_info()['device']}")
    
        print("\n将模型转移回CPU:")
        layoutreader_adapter = layoutreader_adapter.to_device('cpu')
        print(f"转移后设备: {layoutreader_adapter.get_model_info()['device']}")
    else:
        print("\nGPU不可用，跳过设备转移演示")
    
    print("\n3. 通过模型工厂注册和管理适配器")
    
    # 注册自定义模型加载函数
    @factory.register('custom_doclayout')
    def load_custom_doclayout(model_path):
        """加载自定义DocLayout模型并返回适配器"""
        # 这里演示直接使用已有的模型
        original_model = factory.get_model('doclayout', model_path)
        return DocLayoutModelAdapter(original_model)
    
    # 使用自定义加载函数获取模型
    print("\n使用自定义加载函数获取模型适配器:")
    custom_model = factory.get_model('custom_doclayout', settings.layout_analyzer.model_path)
    print(f"自定义模型适配器信息: {custom_model.get_model_info()}")
    
    print("\n4. 适配器与原始模型的区别")
    print("\n原始模型通常有不同的接口和使用方式:")
    print("- YOLOv10: model.predict(image_path, conf=0.5)")
    print("- LayoutLMv3: model(**inputs)")
    print("- PaddleOCR: model(image_path)")
    
    print("\n适配器提供统一的接口:")
    print("- LayoutModel: model.predict(image_path, **kwargs)")
    print("- ReadingOrderModel: model.predict(boxes, **kwargs)")
    print("- OCRModel: model.predict(image_path, **kwargs)")
    
    print("\n5. 适配器的优势")
    print("- 统一接口: 所有模型都提供相同的方法名和参数结构")
    print("- 类型安全: 接口定义明确的输入输出类型")
    print("- 设备管理: 统一的to_device方法")
    print("- 信息查询: 统一的get_model_info方法")
    print("- 无缝集成: 与模型工厂协同工作")
    
    print("\n===== 模型适配器示例结束 =====\n")


if __name__ == "__main__":
    demonstrate_model_adapters()