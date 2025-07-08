# PDF文档解析系统

一个基于机器学习的PDF文档解析系统，支持科技文献、开发文档和通用文档的智能解析与转换。

## 功能特性

- **多场景支持**：针对科技文献、开发文档和通用文档进行了优化
- **高精度版式分析**：使用先进的机器学习模型进行版式元素识别
- **智能表格解析**：自动识别和结构化表格内容
- **公式识别与解析**：支持数学公式的识别和转换
- **阅读顺序分析**：智能分析文档的阅读顺序，保证输出内容的连贯性
- **Markdown输出**：将PDF内容转换为结构化的Markdown格式

## 解析流程

1. **PDF转图片**：将PDF文档转换为高质量图片
2. **版式分析**：识别文档中的标题、段落、表格、图片等元素
3. **多元素解析**：针对不同类型的元素进行专门处理
4. **阅读顺序分析**：确定文档内容的逻辑顺序
5. **Markdown输出**：生成结构化的Markdown文档

## 项目结构

```
pdf_pipeline/
├── .github/                # GitHub相关配置
├── .vscode/                # VS Code配置
├── data/                   # 数据目录
│   ├── input/              # 输入数据
│   │   ├── samples/        # 示例PDF文件（从dataset_A迁移）
│   │   └── test/           # 测试用PDF文件
│   └── output/             # 输出数据
│       ├── markdown/       # 生成的Markdown文件
│       └── temp/           # 临时文件
├── docs/                   # 文档
│   ├── api/                # API文档
│   ├── guides/             # 使用指南
│   ├── development/        # 开发文档
│   └── examples/           # 示例文档
├── src/                    # 源代码
│   ├── config/             # 配置模块
│   ├── models/             # 数据模型
│   ├── pipeline/           # 处理管道
│   ├── processors/         # 处理器模块
│   └── utils/              # 工具函数
├── tests/                  # 测试
│   ├── unit/               # 单元测试
│   ├── integration/        # 集成测试
│   └── resources/          # 测试资源
├── examples/               # 示例代码
├── scripts/                # 脚本工具
│   ├── setup/              # 环境设置脚本
│   └── tools/              # 辅助工具脚本
├── .gitignore              # Git忽略文件
├── LICENSE                 # 许可证文件
├── README.md               # 项目说明
├── CHANGELOG.md            # 变更日志
├── CONTRIBUTING.md         # 贡献指南
├── requirements.txt        # 项目依赖
├── setup.py                # 安装脚本
└── main.py                 # 主程序入口
│       ├── md_generator.py     # Markdown生成器
│       └── pdf_pipeline.py     # 主处理管道
├── tests/                 # 测试
│   ├── unit/              # 单元测试
│   ├── integration/       # 集成测试
│   └── resources/         # 测试资源
├── .gitignore             # Git忽略文件
├── config.yaml            # 配置文件
├── main.py                # 主程序入口
├── pyproject.toml         # 项目构建配置
├── requirements.txt       # 依赖列表
├── setup.py               # 安装脚本
└── README.md              # 项目说明
```

## 安装

### 前提条件

- Python 3.8+
- 适用于深度学习的GPU（可选，但推荐用于加速处理）

### 安装步骤

1. 克隆仓库

```bash
git clone https://github.com/yourusername/pdf-parser.git
cd pdf-parser
```

2. 创建虚拟环境（推荐）

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/MacOS
source venv/bin/activate
```

3. 安装依赖

```bash
pip install -r requirements.txt
```

4. 安装开发依赖（可选，用于开发）

```bash
pip install -e ".[dev]"
```

### 快速安装

我们提供了自动化的环境设置脚本来简化安装过程：

**Windows用户：**
```bash
# 运行环境设置脚本
scripts\setup\setup_env.bat
```

**Linux/Mac用户：**
```bash
# 赋予执行权限并运行脚本
chmod +x scripts/setup/setup_env.sh
./scripts/setup/setup_env.sh
```

### 手动安装

## 快速开始

### 命令行使用

```bash
# 基本用法
python main.py --input path/to/your.pdf --output path/to/output.md

# 指定场景
python main.py --input path/to/your.pdf --output path/to/output.md --scene academic

# 使用自定义配置
python main.py --input path/to/your.pdf --output path/to/output.md --config path/to/config.yaml
```

可选场景(scene)：
- `academic`: 学术论文
- `development`: 开发文档
- `general`: 通用文档

### Python API使用

```python
from src import PDFPipeline, load_config

# 加载配置
config = load_config("config.yaml")

# 初始化管道
pipeline = PDFPipeline(config)

# 处理PDF文件
result = pipeline.process(
    pdf_path="path/to/your.pdf",
    output_path="path/to/output.md",
    scene="academic"
)

print(f"处理完成，输出文件：{result['output_path']}")
```

## 配置

系统使用YAML格式的配置文件，可以自定义各个处理器的参数。默认配置文件为`config.yaml`。

```yaml
# 配置示例（部分）
pdf_converter:
  dpi: 300
  format: "png"
  use_poppler: true

ocr_processor:
  engine: "paddleocr"
  language: "ch"
  use_gpu: true
  confidence_threshold: 0.8
```

详细配置选项请参考[配置指南](docs/guides/configuration.md)。

## 文档

- [快速入门](docs/guides/getting_started.md)
- [配置指南](docs/guides/configuration.md)
- [API文档](docs/api/README.md)
- [使用示例](docs/examples/README.md)
- [开发指南](docs/development/README.md)

## 开发指南

详细的开发指南请参考 [docs/development/](docs/development/) 目录下的文档。

## 许可证

本项目采用 MIT 许可证 - 详情请参阅 LICENSE 文件。
