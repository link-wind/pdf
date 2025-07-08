"""模型缓存管理器使用示例

展示如何使用模型缓存管理器进行高级缓存管理
"""

import os
import sys
import time
import torch
import numpy as np
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from src.models import (
    ModelFactory,
    BaseModel,
    LRUCache,
    ModelCacheManager,
    get_cache_manager,
    configure_cache
)
from src.config import Settings


# 创建一个简单的模型类用于演示
class DummyModel(BaseModel):
    """用于演示的模型类"""
    
    def __init__(self, name, size_mb=100):
        self.name = name
        # 模拟模型占用内存
        self.data = torch.zeros((size_mb * 1024 * 1024 // 4,), dtype=torch.float32)
    
    def predict(self, input_data):
        """模拟预测方法"""
        return f"预测结果: {input_data} (使用 {self.name})"
    
    def get_model_info(self):
        """获取模型信息"""
        return {
            "name": self.name,
            "type": "dummy_model",
            "size_mb": self.data.numel() * 4 // (1024 * 1024)
        }
    
    def to_device(self, device):
        """设备转移"""
        print(f"将模型 {self.name} 转移到 {device}")
        self.data = self.data.to(device)
        return self


def demonstrate_lru_cache():
    """演示LRU缓存的使用"""
    print("\n===== LRU缓存使用示例 =====")
    
    # 创建LRU缓存，容量为3
    cache = LRUCache[str, str](capacity=3)
    
    # 添加缓存项
    print("\n1. 添加缓存项")
    cache.put("key1", "value1")
    cache.put("key2", "value2")
    cache.put("key3", "value3")
    
    # 获取缓存项
    print("\n2. 获取缓存项")
    print(f"key1: {cache.get('key1')}")
    print(f"key2: {cache.get('key2')}")
    print(f"key3: {cache.get('key3')}")
    print(f"key4: {cache.get('key4')}")
    
    # 添加超出容量的缓存项
    print("\n3. 添加超出容量的缓存项")
    print(f"当前缓存键: {cache.keys()}")
    cache.put("key4", "value4")
    print(f"添加key4后缓存键: {cache.keys()}")
    print(f"key1是否存在: {'key1' in cache}")
    
    # 更新缓存项
    print("\n4. 更新缓存项")
    cache.put("key2", "value2_updated")
    print(f"更新key2后缓存键: {cache.keys()}")
    print(f"key2: {cache.get('key2')}")
    
    # 移除缓存项
    print("\n5. 移除缓存项")
    cache.remove("key3")
    print(f"移除key3后缓存键: {cache.keys()}")
    
    # 调整缓存容量
    print("\n6. 调整缓存容量")
    cache.resize(2)
    print(f"调整容量为2后缓存键: {cache.keys()}")
    
    # 清空缓存
    print("\n7. 清空缓存")
    cache.clear()
    print(f"清空后缓存大小: {len(cache)}")
    
    print("\n===== LRU缓存示例结束 =====\n")


def demonstrate_model_cache_manager():
    """演示模型缓存管理器的使用"""
    print("\n===== 模型缓存管理器使用示例 =====")
    
    # 配置全局缓存管理器
    print("\n1. 配置全局缓存管理器")
    cache_manager = configure_cache(
        max_models=3,
        enable_gpu_cache=True,
        memory_threshold=0.9,
        check_interval=60
    )
    
    # 缓存模型
    print("\n2. 缓存模型")
    model1 = DummyModel("Model1", size_mb=10)
    model2 = DummyModel("Model2", size_mb=20)
    model3 = DummyModel("Model3", size_mb=30)
    
    cache_manager.cache_model("model1", model1, version="1.0")
    cache_manager.cache_model("model2", model2, version="1.0")
    cache_manager.cache_model("model3", model3, version="1.0")
    
    # 获取缓存的模型
    print("\n3. 获取缓存的模型")
    cached_model1 = cache_manager.get_model("model1")
    print(f"缓存的模型1信息: {cached_model1.get_model_info()}")
    
    # 获取所有缓存的模型信息
    print("\n4. 获取所有缓存的模型信息")
    cached_models = cache_manager.get_cached_models()
    for model_info in cached_models:
        print(f"模型: {model_info['key']}, 类型: {model_info['type']}")
    
    # 添加超出容量的模型
    print("\n5. 添加超出容量的模型")
    model4 = DummyModel("Model4", size_mb=40)
    cache_manager.cache_model("model4", model4, version="1.0")
    
    # 再次获取所有缓存的模型信息
    print("\n缓存模型4后的缓存模型信息:")
    cached_models = cache_manager.get_cached_models()
    for model_info in cached_models:
        print(f"模型: {model_info['key']}, 类型: {model_info['type']}")
    
    # 移除模型
    print("\n6. 移除模型")
    cache_manager.remove_model("model2")
    
    # 再次获取所有缓存的模型信息
    print("\n移除模型2后的缓存模型信息:")
    cached_models = cache_manager.get_cached_models()
    for model_info in cached_models:
        print(f"模型: {model_info['key']}, 类型: {model_info['type']}")
    
    # 清理最少使用的模型
    print("\n7. 清理最少使用的模型")
    cache_manager.clear_least_used_models(1)
    
    # 再次获取所有缓存的模型信息
    print("\n清理后的缓存模型信息:")
    cached_models = cache_manager.get_cached_models()
    for model_info in cached_models:
        print(f"模型: {model_info['key']}, 类型: {model_info['type']}")
    
    # 获取内存使用情况
    print("\n8. 获取内存使用情况")
    memory_usage = cache_manager.get_memory_usage()
    
    # 显示CPU内存使用情况
    if memory_usage["cpu"]["available"]:
        cpu_mem = memory_usage["cpu"]
        print(f"CPU内存: 总计 {cpu_mem['total'] / (1024**3):.2f} GB, "
              f"已用 {cpu_mem['used'] / (1024**3):.2f} GB, "
              f"可用 {cpu_mem['free'] / (1024**3):.2f} GB, "
              f"使用率 {cpu_mem['percent'] * 100:.2f}%")
    
    # 显示GPU内存使用情况
    if memory_usage["gpu"]["available"]:
        print("\nGPU内存:")
        for device in memory_usage["gpu"]["devices"]:
            print(f"GPU {device['index']} ({device['name']}): "
                  f"总计 {device['total'] / (1024**3):.2f} GB, "
                  f"已用 {device['used'] / (1024**3):.2f} GB, "
                  f"可用 {device['free'] / (1024**3):.2f} GB, "
                  f"使用率 {device['percent'] * 100:.2f}%")
    
    # 清空所有模型
    print("\n9. 清空所有模型")
    cache_manager.clear_all_models()
    
    # 再次获取所有缓存的模型信息
    print("\n清空后的缓存模型信息:")
    cached_models = cache_manager.get_cached_models()
    print(f"缓存模型数量: {len(cached_models)}")
    
    print("\n===== 模型缓存管理器示例结束 =====\n")


def demonstrate_with_model_factory():
    """演示模型缓存管理器与模型工厂的集成"""
    print("\n===== 模型缓存管理器与模型工厂集成示例 =====")
    
    # 获取模型工厂实例
    factory = ModelFactory.get_instance()
    
    # 配置模型工厂缓存
    print("\n1. 配置模型工厂缓存")
    factory.configure_cache(max_models=3, enable_gpu_cache=True)
    
    # 注册模型加载函数
    @factory.register("dummy_model")
    def load_dummy_model(model_path, **kwargs):
        size_mb = kwargs.get("size_mb", 10)
        return DummyModel(f"DummyModel-{size_mb}MB", size_mb=size_mb)
    
    # 加载模型
    print("\n2. 通过模型工厂加载模型")
    model1 = factory.get_model("dummy_model", "dummy_path", size_mb=10)
    print(f"模型1信息: {model1.get_model_info()}")
    
    # 再次加载相同模型（应该从缓存获取）
    print("\n3. 再次加载相同模型（从缓存获取）")
    model1_again = factory.get_model("dummy_model", "dummy_path", size_mb=10)
    print(f"是否为同一个对象: {model1 is model1_again}")
    
    # 加载不同参数的模型
    print("\n4. 加载不同参数的模型")
    model2 = factory.get_model("dummy_model", "dummy_path", size_mb=20)
    model3 = factory.get_model("dummy_model", "dummy_path", size_mb=30)
    print(f"模型2信息: {model2.get_model_info()}")
    print(f"模型3信息: {model3.get_model_info()}")
    
    # 查看缓存的模型
    print("\n5. 查看缓存的模型")
    cached_models = factory.get_cached_models()
    for model_info in cached_models:
        print(f"模型: {model_info['key']}, 类型: {model_info['type']}")
    
    # 加载超出缓存容量的模型
    print("\n6. 加载超出缓存容量的模型")
    model4 = factory.get_model("dummy_model", "dummy_path", size_mb=40)
    print(f"模型4信息: {model4.get_model_info()}")
    
    # 再次查看缓存的模型
    print("\n加载模型4后的缓存模型:")
    cached_models = factory.get_cached_models()
    for model_info in cached_models:
        print(f"模型: {model_info['key']}, 类型: {model_info['type']}")
    
    # 清空缓存
    print("\n7. 清空模型缓存")
    factory.clear_model_cache()
    
    # 再次查看缓存的模型
    print("\n清空后的缓存模型:")
    cached_models = factory.get_cached_models()
    print(f"缓存模型数量: {len(cached_models)}")
    
    print("\n===== 模型缓存管理器与模型工厂集成示例结束 =====\n")


if __name__ == "__main__":
    # 演示LRU缓存
    demonstrate_lru_cache()
    
    # 演示模型缓存管理器
    demonstrate_model_cache_manager()
    
    # 演示与模型工厂的集成
    demonstrate_with_model_factory()