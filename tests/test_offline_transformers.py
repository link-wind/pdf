#!/usr/bin/env python3
"""
360LayoutAnalysis 离线Transformers模型测试
演示如何在没有网络连接的情况下使用预下载的模型
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


def test_offline_transformers():
    """测试离线Transformers模型使用"""
    
    logger.info("360LayoutAnalysis 离线Transformers模型测试")
    logger.info("=" * 60)
    
    # 演示如何设置本地模型路径
    local_model_paths = [
        "./models/360LayoutAnalysis",  # 本地模型目录
        "./360LayoutAnalysis",         # 当前目录下的模型
        "360LayoutAnalysis",           # 默认缓存位置
    ]
    
    logger.info("本地模型路径检查:")
    for path in local_model_paths:
        exists = Path(path).exists()
        logger.info(f"  {path}: {'✅ 存在' if exists else '❌ 不存在'}")
    
    # 提供下载指南
    logger.info("\n📥 如何下载360LayoutAnalysis模型:")
    logger.info("1. 使用git clone:")
    logger.info("   git clone https://huggingface.co/qihoo360/360LayoutAnalysis")
    logger.info("2. 使用huggingface-hub:")
    logger.info("   pip install huggingface-hub")
    logger.info("   python -c \"from huggingface_hub import snapshot_download; snapshot_download('qihoo360/360LayoutAnalysis')\"")
    logger.info("3. 使用transformers:")
    logger.info("   python -c \"from transformers import AutoModel; AutoModel.from_pretrained('qihoo360/360LayoutAnalysis')\"")
    
    # 当前系统状态
    logger.info(f"\n🔧 当前系统状态:")
    logger.info(f"  Python版本: {sys.version}")
    logger.info(f"  PyTorch版本: {torch.__version__}")
    logger.info(f"  CUDA可用: {torch.cuda.is_available()}")
    
    # 测试当前可用的模型
    logger.info(f"\n🧪 测试当前可用的模型:")
    
    # 配置1: 默认配置（应该使用本地YOLO模型）
    logger.info("\n配置1: 默认配置")
    test_config_1 = LayoutAnalyzerConfig()
    test_configuration(test_config_1, "默认配置")
    
    # 配置2: 强制使用Transformers
    logger.info("\n配置2: 强制使用Transformers")
    test_config_2 = LayoutAnalyzerConfig()
    test_config_2.model_path = None  # 强制使用Transformers
    test_config_2.model_type = "transformers"
    test_configuration(test_config_2, "强制Transformers")
    
    # 配置3: 指定本地Transformers路径
    logger.info("\n配置3: 指定本地Transformers路径")
    test_config_3 = LayoutAnalyzerConfig()
    test_config_3.model_path = None
    test_config_3.hf_model_name = "./360LayoutAnalysis"  # 假设的本地路径
    test_configuration(test_config_3, "本地Transformers路径")


def test_configuration(config: LayoutAnalyzerConfig, config_name: str):
    """测试特定配置"""
    try:
        logger.info(f"正在测试 {config_name}...")
        
        # 尝试初始化分析器
        analyzer = LayoutAnalyzer(config)
        
        # 获取模型信息
        model_info = analyzer.get_model_info()
        
        logger.info(f"✅ {config_name} 成功!")
        logger.info(f"  模型类型: {model_info.get('model_type', 'unknown')}")
        logger.info(f"  设备: {model_info.get('device', 'unknown')}")
        logger.info(f"  类别数: {len(model_info.get('category_mapping', {}))}")
        
        # 快速功能测试
        test_image = Image.new('RGB', (800, 600), color='white')
        
        import time
        start_time = time.time()
        page_layout = analyzer.analyze(test_image, page_num=0)
        end_time = time.time()
        
        processing_time = end_time - start_time
        logger.info(f"  处理时间: {processing_time:.3f}秒")
        logger.info(f"  检测区域: {len(page_layout.all_regions)}个")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ {config_name} 失败: {str(e)}")
        return False


def create_model_download_script():
    """创建模型下载脚本"""
    
    download_script = '''#!/usr/bin/env python3
"""
360LayoutAnalysis 模型下载脚本
"""

import os
import sys
from pathlib import Path

def download_with_git():
    """使用git下载模型"""
    print("使用git下载360LayoutAnalysis模型...")
    
    cmd = "git clone https://huggingface.co/qihoo360/360LayoutAnalysis"
    
    try:
        os.system(cmd)
        print("✅ git下载完成!")
        return True
    except Exception as e:
        print(f"❌ git下载失败: {e}")
        return False

def download_with_huggingface_hub():
    """使用huggingface-hub下载模型"""
    print("使用huggingface-hub下载360LayoutAnalysis模型...")
    
    try:
        from huggingface_hub import snapshot_download
        
        # 下载到指定目录
        local_dir = "./360LayoutAnalysis"
        snapshot_download(
            repo_id="qihoo360/360LayoutAnalysis",
            local_dir=local_dir,
            local_dir_use_symlinks=False
        )
        
        print(f"✅ huggingface-hub下载完成，保存到: {local_dir}")
        return True
        
    except ImportError:
        print("❌ huggingface-hub未安装，请先安装: pip install huggingface-hub")
        return False
    except Exception as e:
        print(f"❌ huggingface-hub下载失败: {e}")
        return False

def download_with_transformers():
    """使用transformers下载模型"""
    print("使用transformers下载360LayoutAnalysis模型...")
    
    try:
        from transformers import AutoModel
        
        # 这会自动下载并缓存模型
        model = AutoModel.from_pretrained("qihoo360/360LayoutAnalysis")
        
        print("✅ transformers下载完成!")
        print("模型已缓存到默认位置，可以离线使用")
        return True
        
    except Exception as e:
        print(f"❌ transformers下载失败: {e}")
        return False

def main():
    """主函数"""
    print("360LayoutAnalysis 模型下载工具")
    print("=" * 50)
    
    methods = [
        ("Git Clone", download_with_git),
        ("HuggingFace Hub", download_with_huggingface_hub),
        ("Transformers", download_with_transformers)
    ]
    
    for name, method in methods:
        print(f"\\n尝试方法: {name}")
        print("-" * 30)
        
        if method():
            print(f"🎉 {name} 下载成功!")
            break
        else:
            print(f"⚠️  {name} 下载失败，尝试下一种方法...")
    else:
        print("\\n💥 所有下载方法都失败了!")
        print("请检查网络连接或手动下载模型文件")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''
    
    # 保存下载脚本
    script_path = project_root / "download_360_model.py"
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(download_script)
    
    logger.info(f"模型下载脚本已创建: {script_path}")
    logger.info("使用方法: python download_360_model.py")
    
    return script_path


def create_usage_examples():
    """创建使用示例"""
    
    examples = '''
# 360LayoutAnalysis 使用示例

## 1. 基本使用（自动选择模型）

```python
from src.config.settings import LayoutAnalyzerConfig
from src.pipeline.layout_analyzer import LayoutAnalyzer
from PIL import Image

# 创建配置（自动选择可用模型）
config = LayoutAnalyzerConfig()
analyzer = LayoutAnalyzer(config)

# 加载图像
image = Image.open("document.png")

# 进行版式分析
page_layout = analyzer.analyze(image, page_num=0)

# 获取结果
print(f"检测到 {len(page_layout.all_regions)} 个区域")
```

## 2. 强制使用YOLO模型

```python
config = LayoutAnalyzerConfig()
config.model_path = "paper-8n.pt"  # 指定YOLO模型
config.model_type = "yolo"         # 强制使用YOLO
analyzer = LayoutAnalyzer(config)
```

## 3. 强制使用Transformers模型

```python
config = LayoutAnalyzerConfig()
config.model_path = None           # 不使用本地YOLO
config.model_type = "transformers" # 强制使用Transformers
config.hf_model_name = "qihoo360/360LayoutAnalysis"
analyzer = LayoutAnalyzer(config)
```

## 4. 使用本地Transformers模型

```python
config = LayoutAnalyzerConfig()
config.model_path = None
config.hf_model_name = "./360LayoutAnalysis"  # 本地模型路径
analyzer = LayoutAnalyzer(config)
```

## 5. 性能优化配置

```python
config = LayoutAnalyzerConfig()
config.use_gpu = True              # 启用GPU
config.batch_size = 4              # 批处理大小
config.confidence_threshold = 0.6   # 置信度阈值
config.enable_mixed_precision = True  # 混合精度
analyzer = LayoutAnalyzer(config)
```

## 6. 可视化结果

```python
# 生成可视化图像
vis_image = analyzer.visualize_layout(image, page_layout, "result.png")

# 提取特定区域
for region in page_layout.text_regions:
    region_image = analyzer.extract_region_image(image, region)
    region_image.save(f"region_{region.reading_order}.png")
```

## 7. 批量处理

```python
import os
from pathlib import Path

# 批量处理文件夹中的图像
image_folder = Path("documents")
output_folder = Path("results")
output_folder.mkdir(exist_ok=True)

for image_file in image_folder.glob("*.png"):
    image = Image.open(image_file)
    page_layout = analyzer.analyze(image)
    
    # 保存可视化结果
    vis_path = output_folder / f"{image_file.stem}_layout.png"
    analyzer.visualize_layout(image, page_layout, str(vis_path))
    
    # 保存分析结果
    result_path = output_folder / f"{image_file.stem}_analysis.txt"
    with open(result_path, 'w') as f:
        f.write(f"图像: {image_file.name}\\n")
        f.write(f"区域数: {len(page_layout.all_regions)}\\n")
        for i, region in enumerate(page_layout.all_regions):
            f.write(f"区域{i+1}: {region.region_type.value}\\n")
```

## 8. 错误处理

```python
try:
    analyzer = LayoutAnalyzer(config)
    page_layout = analyzer.analyze(image)
    
except Exception as e:
    print(f"分析失败: {e}")
    
    # 获取模型信息进行诊断
    if hasattr(analyzer, 'get_model_info'):
        model_info = analyzer.get_model_info()
        print(f"模型信息: {model_info}")
```
'''
    
    # 保存使用示例
    examples_path = project_root / "docs" / "usage_examples.md"
    examples_path.parent.mkdir(exist_ok=True)
    
    with open(examples_path, 'w', encoding='utf-8') as f:
        f.write(examples)
    
    logger.info(f"使用示例已创建: {examples_path}")
    
    return examples_path


def main():
    """主函数"""
    test_offline_transformers()
    
    # 创建辅助文件
    logger.info(f"\n📁 创建辅助文件...")
    
    script_path = create_model_download_script()
    examples_path = create_usage_examples()
    
    logger.info(f"\n✅ 离线测试完成!")
    logger.info(f"📋 创建的文件:")
    logger.info(f"  - 下载脚本: {script_path}")
    logger.info(f"  - 使用示例: {examples_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
