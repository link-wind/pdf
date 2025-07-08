"""模型注册器使用示例

展示如何使用模型注册器简化模型注册过程
"""

import os
import sys
import torch
import numpy as np
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from src.models import (
    ModelFactory,
    BaseModel,
    register_model,
    register_model_adapter,
    batch_register_models,
    batch_register_model_adapters,
    ModelRegistry,
    DocLayoutModelAdapter
)
from src.config import Settings


# 创建一个简单的自定义模型类
class SimpleModel(BaseModel):
    """简单的自定义模型，用于演示"""
    
    def __init__(self, name, version):
        self.name = name
        self.version = version
    
    def predict(self, input_data):
        """模拟预测方法"""
        return f"预测结果: {input_data} (使用 {self.name} v{self.version})"
    
    def get_model_info(self):
        """获取模型信息"""
        return {
            "name": self.name,
            "version": self.version,
            "type": "simple_model"
        }
    
    def to_device(self, device):
        """模拟设备转移"""
        print(f"将模型 {self.name} 转移到 {device}")
        return self


# 使用装饰器注册模型加载函数
@register_model("simple_model", description="一个简单的演示模型")
def load_simple_model(model_path, **kwargs):
    """加载简单模型"""
    # 在实际应用中，这里会从model_path加载模型
    # 这里只是演示，所以直接创建一个模型实例
    version = kwargs.get("version", "1.0")
    return SimpleModel("SimpleModel", version)


# 创建一个自定义适配器类
class CustomAdapter(BaseModel):
    """自定义适配器，用于演示"""
    
    def __init__(self, base_model):
        self.base_model = base_model
    
    def predict(self, input_data, **kwargs):
        """增强的预测方法"""
        # 添加前处理
        processed_input = f"处理后的{input_data}"
        
        # 调用基础模型
        result = self.base_model.predict(processed_input)
        
        # 添加后处理
        enhanced_result = f"增强后的{result}"
        
        return enhanced_result
    
    def get_model_info(self):
        """获取模型信息"""
        base_info = self.base_model.get_model_info()
        return {
            **base_info,
            "adapter": "CustomAdapter"
        }
    
    def to_device(self, device):
        """设备转移"""
        self.base_model = self.base_model.to_device(device)
        return self


def demonstrate_model_registry():
    """演示模型注册器的使用"""
    print("\n===== 模型注册器使用示例 =====")
    
    # 获取模型工厂实例
    factory = ModelFactory.get_instance()
    
    print("\n1. 使用装饰器注册模型")
    # 上面已经使用@register_model装饰器注册了simple_model
    
    # 加载simple_model
    simple_model = factory.get_model("simple_model", "dummy_path")
    print(f"模型信息: {simple_model.get_model_info()}")
    print(f"预测结果: {simple_model.predict('测试输入')}")
    
    print("\n2. 使用register_model_adapter注册适配器")
    
    # 注册适配器
    register_model_adapter(
        model_type="enhanced_simple_model",
        adapter_class=CustomAdapter,
        base_model_type="simple_model",
        description="增强版简单模型"
    )
    
    # 加载增强版模型
    enhanced_model = factory.get_model("enhanced_simple_model", "dummy_path", version="2.0")
    print(f"适配器模型信息: {enhanced_model.get_model_info()}")
    print(f"适配器预测结果: {enhanced_model.predict('测试输入')}")
    
    print("\n3. 使用batch_register_models批量注册模型")
    
    # 定义多个模型加载函数
    def load_model_a(model_path):
        return SimpleModel("ModelA", "1.0")
    
    def load_model_b(model_path):
        return SimpleModel("ModelB", "1.0")
    
    # 批量注册
    batch_register_models([
        {
            "model_type": "model_a",
            "loader_func": load_model_a,
            "description": "模型A"
        },
        {
            "model_type": "model_b",
            "loader_func": load_model_b,
            "description": "模型B"
        }
    ])
    
    # 加载批量注册的模型
    model_a = factory.get_model("model_a", "dummy_path")
    model_b = factory.get_model("model_b", "dummy_path")
    
    print(f"模型A信息: {model_a.get_model_info()}")
    print(f"模型B信息: {model_b.get_model_info()}")
    
    print("\n4. 使用batch_register_model_adapters批量注册适配器")
    
    # 批量注册适配器
    batch_register_model_adapters([
        {
            "model_type": "enhanced_model_a",
            "adapter_class": CustomAdapter,
            "base_model_type": "model_a",
            "description": "增强版模型A"
        },
        {
            "model_type": "enhanced_model_b",
            "adapter_class": CustomAdapter,
            "base_model_type": "model_b",
            "description": "增强版模型B"
        }
    ])
    
    # 加载批量注册的适配器模型
    enhanced_a = factory.get_model("enhanced_model_a", "dummy_path")
    enhanced_b = factory.get_model("enhanced_model_b", "dummy_path")
    
    print(f"增强版模型A信息: {enhanced_a.get_model_info()}")
    print(f"增强版模型B信息: {enhanced_b.get_model_info()}")
    
    print("\n5. 查看已注册的模型类型")
    model_types = factory.get_available_model_types()
    print(f"可用模型类型: {model_types}")
    
    print("\n6. 查看模型描述")
    for model_type in model_types:
        description = factory.get_model_description(model_type)
        if description:
            print(f"{model_type}: {description}")
    
    print("\n7. 标准适配器的使用")
    # 项目中已经注册了标准适配器
    print("项目中已注册的标准适配器:")
    standard_adapters = [
        "doclayout_adapter",
        "layoutreader_adapter",
        "formula_adapter",
        "table_adapter",
        "ocr_adapter"
    ]
    
    for adapter_type in standard_adapters:
        description = factory.get_model_description(adapter_type)
        if description:
            print(f"{adapter_type}: {description}")
    
    print("\n===== 模型注册器示例结束 =====\n")


if __name__ == "__main__":
    demonstrate_model_registry()