# PDF解析系统使用示例

本文档提供了PDF解析系统的使用示例，帮助您了解如何在不同场景下使用本系统。

## 基本示例

### 命令行使用

将单个PDF文件转换为Markdown：

```bash
# 基本用法
python -m src.main path/to/document.pdf

# 指定输出目录
python -m src.main path/to/document.pdf --output path/to/output

# 使用自定义配置
python -m src.main path/to/document.pdf --config path/to/config.yaml
```

### Python API使用

```python
from src import PDFPipeline, load_config

# 加载配置
config = load_config("config.yaml")

# 初始化处理流程
pipeline = PDFPipeline(config)

# 处理PDF文件
output_path = pipeline.process("path/to/document.pdf", "path/to/output")

print(f"Markdown文件已生成：{output_path}")
```

## 高级示例

### 批量处理PDF文件

```python
import os
from pathlib import Path
from src import PDFPipeline, load_config

# 加载配置
config = load_config()

# 初始化处理流程
pipeline = PDFPipeline(config)

# 输入和输出目录
input_dir = Path("data/input/samples")
output_dir = Path("data/output/markdown")

# 确保输出目录存在
output_dir.mkdir(parents=True, exist_ok=True)

# 批量处理PDF文件
for pdf_file in input_dir.glob("*.pdf"):
    print(f"处理文件：{pdf_file}")
    try:
        output_path = pipeline.process(str(pdf_file), str(output_dir))
        print(f"处理完成：{output_path}")
    except Exception as e:
        print(f"处理失败：{e}")
```

### 自定义处理流程

如果您需要更精细地控制处理流程，可以直接使用各个处理器：

```python
import os
from pathlib import Path

from src.config import create_default_config
from src.processors.pdf_converter import PDFConverter
from src.processors.layout_analyzer import LayoutAnalyzer
from src.processors.ocr_processor import OCRProcessor
from src.processors.table_parser import TableParser
from src.processors.formula_parser import FormulaParser
from src.processors.reading_order_analyzer import ReadingOrderAnalyzer
from src.processors.markdown_generator import MarkdownGenerator

# 创建配置
config = create_default_config()

# 初始化各个处理器
pdf_converter = PDFConverter(config.pdf_converter)
layout_analyzer = LayoutAnalyzer(config.layout_analyzer)
ocr_processor = OCRProcessor(config.ocr_processor)
table_parser = TableParser(config.table_parser)
formula_parser = FormulaParser(config.formula_parser)
reading_order_analyzer = ReadingOrderAnalyzer(config.reading_order)
markdown_generator = MarkdownGenerator(config.markdown_generator)

# 处理PDF
pdf_path = "path/to/document.pdf"
output_dir = Path("path/to/output")
output_dir.mkdir(parents=True, exist_ok=True)

# 1. 将PDF转换为图像
images = pdf_converter.convert_to_images(pdf_path)

# 2. 分析版式
layout_results = layout_analyzer.analyze(images)

# 3. OCR识别文本
text_results = ocr_processor.process(images, layout_results)

# 4. 解析表格
table_results = table_parser.parse(images, layout_results)

# 5. 解析公式
formula_results = formula_parser.parse(images, layout_results)

# 6. 分析阅读顺序
ordered_results = reading_order_analyzer.analyze(
    layout_results, text_results
)

# 7. 生成Markdown
output_filename = os.path.basename(pdf_path).replace(".pdf", ".md")
output_path = markdown_generator.generate(
    str(output_dir / output_filename),
    ordered_results,
    text_results,
    table_results,
    formula_results
)

print(f"处理完成：{output_path}")
```

### 使用不同的OCR引擎

```python
from src import PDFPipeline, load_config
from src.config import create_default_config

# 创建默认配置
config = create_default_config()

# 修改OCR配置，使用EasyOCR引擎
config.ocr_processor.engine = "easyocr"
config.ocr_processor.language = "en"  # 英文识别

# 初始化处理流程
pipeline = PDFPipeline(config)

# 处理PDF文件
output_path = pipeline.process("path/to/english_document.pdf", "path/to/output")

print(f"Markdown文件已生成：{output_path}")
```

### 处理扫描文档

对于扫描的PDF文档，可能需要调整OCR和版式分析的参数：

```python
from src import PDFPipeline, load_config
from src.config import create_default_config

# 创建默认配置
config = create_default_config()

# 调整PDF转换器配置
config.pdf_converter.dpi = 400  # 提高DPI以获取更清晰的图像

# 调整OCR配置
config.ocr_processor.confidence_threshold = 0.7  # 降低置信度阈值以捕获更多文本

# 调整版式分析器配置
config.layout_analyzer.confidence_threshold = 0.3  # 降低置信度阈值

# 初始化处理流程
pipeline = PDFPipeline(config)

# 处理PDF文件
output_path = pipeline.process("path/to/scanned_document.pdf", "path/to/output")

print(f"Markdown文件已生成：{output_path}")
```

### 处理包含复杂表格的文档

```python
from src import PDFPipeline, load_config
from src.config import create_default_config

# 创建默认配置
config = create_default_config()

# 调整表格解析器配置
config.table_parser.method = "PPStructure"  # 使用PaddleOCR的表格结构识别
config.table_parser.confidence_threshold = 0.6  # 调整置信度阈值
config.table_parser.merge_threshold = 0.2  # 调整单元格合并阈值

# 调整Markdown生成器配置
config.markdown_generator.table_format = "html"  # 使用HTML格式输出表格以保持复杂结构

# 初始化处理流程
pipeline = PDFPipeline(config)

# 处理PDF文件
output_path = pipeline.process("path/to/document_with_tables.pdf", "path/to/output")

print(f"Markdown文件已生成：{output_path}")
```

### 处理包含数学公式的文档

```python
from src import PDFPipeline, load_config
from src.config import create_default_config

# 创建默认配置
config = create_default_config()

# 调整公式解析器配置
config.formula_parser.engine = "pp_formulanet"  # 使用PaddleOCR的公式识别
config.formula_parser.model_size = "L"  # 使用大模型以提高准确率
config.formula_parser.confidence_threshold = 0.8  # 提高置信度阈值以减少错误识别

# 调整Markdown生成器配置
config.markdown_generator.formula_format = "latex"  # 使用LaTeX格式输出公式

# 初始化处理流程
pipeline = PDFPipeline(config)

# 处理PDF文件
output_path = pipeline.process("path/to/document_with_formulas.pdf", "path/to/output")

print(f"Markdown文件已生成：{output_path}")
```

### 使用GPU加速

```python
from src import PDFPipeline, load_config
from src.config import create_default_config

# 创建默认配置
config = create_default_config()

# 启用GPU加速
config.layout_analyzer.use_gpu = True
config.ocr_processor.use_gpu = True
config.table_parser.use_gpu = True
config.formula_parser.use_gpu = True

# 初始化处理流程
pipeline = PDFPipeline(config)

# 处理PDF文件
output_path = pipeline.process("path/to/document.pdf", "path/to/output")

print(f"Markdown文件已生成：{output_path}")
```

### 自定义输出格式

```python
from src import PDFPipeline, load_config
from src.config import create_default_config

# 创建默认配置
config = create_default_config()

# 调整Markdown生成器配置
config.markdown_generator.include_images = True  # 包含图像
config.markdown_generator.image_format = "png"  # 图像格式
config.markdown_generator.include_metadata = True  # 包含元数据
config.markdown_generator.include_page_breaks = True  # 包含分页符
config.markdown_generator.line_break_style = "double"  # 换行风格
config.markdown_generator.generate_toc = True  # 生成目录

# 初始化处理流程
pipeline = PDFPipeline(config)

# 处理PDF文件
output_path = pipeline.process("path/to/document.pdf", "path/to/output")

print(f"Markdown文件已生成：{output_path}")
```

## 集成示例

### 与Web应用集成

```python
from flask import Flask, request, jsonify, send_file
import os
from pathlib import Path
import tempfile
from src import PDFPipeline, load_config

app = Flask(__name__)

# 加载配置
config = load_config()

# 初始化处理流程
pipeline = PDFPipeline(config)

@app.route("/convert", methods=["POST"])
def convert_pdf():
    # 检查是否有文件上传
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files["file"]
    
    # 检查文件名
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    
    # 检查文件类型
    if not file.filename.endswith(".pdf"):
        return jsonify({"error": "File must be a PDF"}), 400
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        # 保存上传的文件
        pdf_path = os.path.join(temp_dir, "input.pdf")
        file.save(pdf_path)
        
        # 处理PDF
        try:
            output_path = pipeline.process(pdf_path, temp_dir)
            
            # 返回生成的Markdown文件
            return send_file(
                output_path,
                as_attachment=True,
                download_name=os.path.basename(output_path)
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
```

### 与命令行工具集成

```python
import click
from pathlib import Path
from src import PDFPipeline, load_config

@click.group()
def cli():
    """PDF解析工具"""
    pass

@cli.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="输出目录")
@click.option("--config", "-c", type=click.Path(exists=True), help="配置文件路径")
@click.option("--gpu/--no-gpu", default=False, help="是否使用GPU")
def convert(input_path, output, config, gpu):
    """将PDF转换为Markdown"""
    # 加载配置
    if config:
        config_obj = load_config(config)
    else:
        config_obj = load_config()
    
    # 设置GPU选项
    if gpu:
        config_obj.layout_analyzer.use_gpu = True
        config_obj.ocr_processor.use_gpu = True
        config_obj.table_parser.use_gpu = True
        config_obj.formula_parser.use_gpu = True
    
    # 初始化处理流程
    pipeline = PDFPipeline(config_obj)
    
    # 处理PDF
    input_path = Path(input_path)
    
    if input_path.is_file():
        # 处理单个文件
        output_path = pipeline.process(str(input_path), output)
        click.echo(f"处理完成：{output_path}")
    elif input_path.is_dir():
        # 处理目录中的所有PDF文件
        output_dir = Path(output) if output else Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for pdf_file in input_path.glob("*.pdf"):
            click.echo(f"处理文件：{pdf_file}")
            try:
                output_path = pipeline.process(str(pdf_file), str(output_dir))
                click.echo(f"处理完成：{output_path}")
            except Exception as e:
                click.echo(f"处理失败：{e}")

if __name__ == "__main__":
    cli()
```

## 更多示例

更多示例和用例请参考[开发指南](../development/README.md)和[API文档](../api/README.md)。