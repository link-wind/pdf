"""模型工厂使用示例
展示如何使用模型工厂加载和管理模型
"""

import os
import sys
import torch
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import ModelFactory
from src.config.settings import (
    LayoutAnalyzerConfig, 
    ReadingOrderConfig,
    FormulaParserConfig,
    TableParserConfig,
    OCRProcessorConfig
)


def example_doclayout_model():
    """DocLayout模型加载示例"""
    print("\n=== DocLayout模型加载示例 ===")
    
    # 创建配置
    config = LayoutAnalyzerConfig()
    config.model_path = "doclayout.pt"  # 指定模型路径
    
    try:
        # 使用模型工厂加载模型
        model = ModelFactory.get_model(
            model_type="doclayout",
            model_path=config.model_path
        )
        
        # 获取模型信息
        print(f"模型加载成功: {model.__class__.__name__}")
        print(f"模型路径: {config.model_path}")
        
        # 查看缓存的模型
        cached_models = ModelFactory.get_cached_models()
        print(f"当前缓存模型数量: {len(cached_models)}")
        
    except Exception as e:
        print(f"模型加载失败: {e}")


def example_layoutreader_model():
    """LayoutReader模型加载示例"""
    print("\n=== LayoutReader模型加载示例 ===")
    
    # 创建配置
    config = ReadingOrderConfig()
    config.layout_reader_model_path = "hantian/layoutreader"  # 使用默认模型
    
    try:
        # 使用模型工厂加载模型
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = ModelFactory.get_model(
            model_type="layoutreader",
            model_path=config.layout_reader_model_path,
            device=device
        )
        
        # 获取模型信息
        print(f"模型加载成功: {model.__class__.__name__}")
        print(f"模型路径: {config.layout_reader_model_path}")
        print(f"模型设备: {next(model.parameters()).device}")
        
        # 查看缓存的模型
        cached_models = ModelFactory.get_cached_models()
        print(f"当前缓存模型数量: {len(cached_models)}")
        
    except Exception as e:
        print(f"模型加载失败: {e}")


def example_formula_model():
    """公式识别模型加载示例"""
    print("\n=== 公式识别模型加载示例 ===")
    
    # 创建配置
    config = FormulaParserConfig()
    config.model_size = "L"  # 使用Large版本
    
    try:
        # 使用模型工厂加载模型
        model = ModelFactory.get_model(
            model_type="formula",
            model_size=config.model_size
        )
        
        # 获取模型信息
        print(f"模型加载成功")
        print(f"模型大小: {config.model_size}")
        
        # 查看缓存的模型
        cached_models = ModelFactory.get_cached_models()
        print(f"当前缓存模型数量: {len(cached_models)}")
        
    except Exception as e:
        print(f"模型加载失败: {e}")


def example_table_model():
    """表格识别模型加载示例"""
    print("\n=== 表格识别模型加载示例 ===")
    
    # 创建配置
    config = TableParserConfig()
    
    try:
        # 使用模型工厂加载模型
        model = ModelFactory.get_model(
            model_type="table",
            use_gpu=torch.cuda.is_available(),
            lang="ch"
        )
        
        # 获取模型信息
        print(f"模型加载成功")
        
        # 查看缓存的模型
        cached_models = ModelFactory.get_cached_models()
        print(f"当前缓存模型数量: {len(cached_models)}")
        
    except Exception as e:
        print(f"模型加载失败: {e}")


def example_ocr_model():
    """OCR模型加载示例"""
    print("\n=== OCR模型加载示例 ===")
    
    # 创建配置
    config = OCRProcessorConfig()
    config.language = "ch"  # 中文
    
    try:
        # 使用模型工厂加载模型
        model = ModelFactory.get_model(
            model_type="ocr",
            use_gpu=torch.cuda.is_available(),
            lang=config.language
        )
        
        # 获取模型信息
        print(f"模型加载成功")
        print(f"语言: {config.language}")
        
        # 查看缓存的模型
        cached_models = ModelFactory.get_cached_models()
        print(f"当前缓存模型数量: {len(cached_models)}")
        
    except Exception as e:
        print(f"模型加载失败: {e}")


def example_cache_management():
    """缓存管理示例"""
    print("\n=== 缓存管理示例 ===")
    
    # 配置缓存
    ModelFactory.configure_cache(
        enabled=True,
        ttl=1800,  # 30分钟
        max_size=3  # 最多缓存3个模型
    )
    print("缓存配置已更新: 启用=True, TTL=1800秒, 最大数量=3")
    
    # 查看可用的模型类型
    model_types = ModelFactory.get_available_model_types()
    print(f"可用的模型类型: {model_types}")
    
    # 清空缓存
    ModelFactory.clear_cache()
    print("缓存已清空")
    
    # 查看缓存的模型
    cached_models = ModelFactory.get_cached_models()
    print(f"当前缓存模型数量: {len(cached_models)}")


def main():
    """主函数"""
    print("模型工厂使用示例")
    print("=" * 50)
    
    # 检查环境
    print(f"Python版本: {sys.version}")
    print(f"PyTorch版本: {torch.__version__}")
    print(f"CUDA可用: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA设备: {torch.cuda.get_device_name(0)}")
    
    # 运行示例
    example_cache_management()
    
    # 根据可用性运行不同的示例
    try:
        example_doclayout_model()
    except Exception as e:
        print(f"DocLayout示例失败: {e}")
    
    try:
        example_layoutreader_model()
    except Exception as e:
        print(f"LayoutReader示例失败: {e}")
    
    try:
        example_formula_model()
    except Exception as e:
        print(f"公式识别示例失败: {e}")
    
    try:
        example_table_model()
    except Exception as e:
        print(f"表格识别示例失败: {e}")
    
    try:
        example_ocr_model()
    except Exception as e:
        print(f"OCR示例失败: {e}")


if __name__ == "__main__":
    main()