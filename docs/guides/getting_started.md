# 快速入门指南

本指南将帮助您快速上手PDF解析系统，包括安装、配置和基本使用方法。

## 安装

### 前提条件

- Python 3.8 或更高版本
- 足够的磁盘空间（至少 2GB）用于安装依赖和模型
- 对于GPU加速（可选）：CUDA 11.0+ 和兼容的NVIDIA GPU

### 安装步骤

1. 克隆仓库

```bash
git clone https://github.com/yourusername/pdf-parser.git
cd pdf-parser
```

2. 创建虚拟环境（推荐）

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
```

3. 安装依赖

```bash
pip install -r requirements.txt
```

4. 设置开发环境（可选，仅开发人员需要）

```bash
python scripts/setup/setup_dev_env.py
```

## 基本使用

### 命令行使用

PDF解析系统提供了简单的命令行接口，可以直接将PDF文件转换为Markdown格式。

```bash
# 基本用法
python -m src.main input.pdf

# 指定输出目录
python -m src.main input.pdf --output output_dir

# 使用自定义配置文件
python -m src.main input.pdf --config custom_config.yaml

# 显示帮助信息
python -m src.main --help
```

如果您已经通过`pip install`安装了本项目，也可以直接使用`pdf-parser`命令：

```bash
# 基本用法
pdf-parser input.pdf

# 指定输出目录
pdf-parser input.pdf --output output_dir
```

### Python API使用

您也可以在Python代码中使用PDF解析系统的API：

```python
from src import PDFPipeline, load_config

# 加载配置（可选，如果不指定则使用默认配置）
config = load_config("config.yaml")

# 初始化处理流程
pipeline = PDFPipeline(config)

# 处理PDF文件
output_path = pipeline.process("input.pdf", "output_dir")

print(f"Markdown文件已生成：{output_path}")
```

## 配置

PDF解析系统使用YAML格式的配置文件。默认配置文件路径为项目根目录下的`config.yaml`。

您可以创建自定义配置文件，并通过命令行参数`--config`或API中的`load_config`函数指定。

详细的配置选项请参考[配置指南](configuration.md)。

## 示例

### 处理单个PDF文件

```bash
python -m src.main examples/sample.pdf
```

### 批量处理PDF文件

```python
import os
from src import PDFPipeline, load_config

# 加载配置
config = load_config()

# 初始化处理流程
pipeline = PDFPipeline(config)

# 输入和输出目录
input_dir = "data/input/samples"
output_dir = "data/output/markdown"

# 确保输出目录存在
os.makedirs(output_dir, exist_ok=True)

# 批量处理PDF文件
for filename in os.listdir(input_dir):
    if filename.endswith(".pdf"):
        pdf_path = os.path.join(input_dir, filename)
        print(f"处理文件：{pdf_path}")
        try:
            output_path = pipeline.process(pdf_path, output_dir)
            print(f"处理完成：{output_path}")
        except Exception as e:
            print(f"处理失败：{e}")
```

### 自定义处理流程

如果您需要更精细地控制处理流程，可以直接使用各个处理器：

```python
from src.config import create_default_config
from src.processors.pdf_converter import PDFConverter
from src.processors.layout_analyzer import LayoutAnalyzer
from src.processors.ocr_processor import OCRProcessor
from src.processors.markdown_generator import MarkdownGenerator

# 创建配置
config = create_default_config()

# 初始化各个处理器
pdf_converter = PDFConverter(config.pdf_converter)
layout_analyzer = LayoutAnalyzer(config.layout_analyzer)
ocr_processor = OCRProcessor(config.ocr_processor)
markdown_generator = MarkdownGenerator(config.markdown_generator)

# 处理PDF
pdf_path = "input.pdf"
output_dir = "output"

# 1. 将PDF转换为图像
images = pdf_converter.convert_to_images(pdf_path)

# 2. 分析版式
layout_results = layout_analyzer.analyze(images)

# 3. OCR识别文本
text_results = ocr_processor.process(images, layout_results)

# 4. 生成Markdown（简化版，实际使用可能需要更多处理器）
output_path = markdown_generator.generate(
    os.path.join(output_dir, "output.md"),
    layout_results,
    text_results
)

print(f"处理完成：{output_path}")
```

## 常见问题

### 1. 安装依赖时出错

如果在安装依赖时遇到问题，可以尝试以下解决方案：

- 确保您的Python版本为3.8或更高
- 对于Windows用户，某些依赖可能需要安装Visual C++ Build Tools
- 对于特定的依赖问题，请查阅相应的文档或提交Issue

### 2. GPU加速不工作

如果GPU加速不工作，请检查：

- 确保您已安装CUDA和兼容的GPU驱动
- 在配置文件中将相应处理器的`use_gpu`设置为`true`
- 检查CUDA版本与安装的PyTorch和PaddlePaddle版本是否兼容

### 3. 处理结果不理想

如果处理结果不理想，可以尝试：

- 调整配置文件中的参数，如提高DPI、调整置信度阈值等
- 对于特定类型的PDF（如扫描文档、复杂表格等），可能需要专门的配置
- 查看日志文件（默认在`logs/pdf_parser.log`）以获取更多信息

## 下一步

- [配置指南](configuration.md) - 了解详细的配置选项
- [API文档](../api/README.md) - 了解系统的API接口
- [开发指南](../development/README.md) - 了解如何参与开发