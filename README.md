# PDF文档解析系统

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)

一个基于深度学习的智能PDF文档解析系统，能够将PDF文档高质量地转换为结构化的Markdown格式，支持公式解析、表格识别、版式分析等多种复杂场景。

## 🌟 主要特性

### 🔥 核心功能
- **高精度OCR文本识别** - 基于PaddleOCR和RapidOCR，支持中英文识别
- **智能版式分析** - 使用YOLO模型进行文档区域检测和布局理解
- **公式解析** - 专业数学公式识别，支持LaTeX格式输出
- **表格识别** - 复杂表格结构分析，支持多层表头和跨行跨列表格
- **阅读顺序分析** - 基于LayoutReader的智能阅读顺序排序
- **大模型辅助** - 集成LLM进行公式错误修复和标题优化
- **Web界面** - 提供Gradio Web界面，支持实时预览
- **批量处理** - 支持多进程并行批量处理PDF文件

### 🚀 技术优势
- **模块化设计** - 组件化架构，易于扩展和维护
- **多场景支持** - 学术论文、技术文档、通用文档等多种场景优化
- **GPU加速** - 支持GPU加速处理，大幅提升处理速度
- **智能修复** - 自动检测和修复解析错误
- **多格式输出** - 支持Markdown、HTML等多种输出格式

## 📦 系统要求

- Python 3.8+
- CUDA 11.x (推荐，用于GPU加速)
- 内存: 建议16GB以上
- 存储: 建议10GB以上可用空间

## 🚀 快速开始

### 1. 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd pdf-parser

# 安装Python依赖
pip install -r requirements.txt
```

### 2. 配置系统

编辑 `config.yaml` 文件，设置相关参数：

```yaml
# 核心配置
formula_parser:
  use_llm: true                   # 启用大模型公式解析
  llm_fallback: true              # 失败时启用大模型备用方案
  engine: pp_formulanet           # 公式解析引擎

# LLM配置
llm:
  api_key: "your-api-key"         # API密钥
  base_url: "https://api.deepseek.com"  # API地址
  model: "deepseek-chat"          # 模型名称
  enabled: true                   # 启用LLM功能
```

### 3. 使用方法

#### 命令行模式

```bash
# 处理单个PDF文件
python main.py -i input.pdf -o output.md

# 批量处理目录中的PDF文件
python main.py -b -o output/markdown

# 使用4个进程并行处理
python main.py -b -w 4 -o output/markdown

# 学术场景优化处理
python main.py -i academic.pdf -o output.md -s academic

# 查看详细输出
python main.py -i input.pdf -o output.md -v
```

#### Web界面模式

```bash
# 启动Web界面
python gradio3_final.py

# 访问 http://localhost:7860
```

## 🏗️ 项目架构

```
pdf-parser/
├── src/                          # 核心源代码
│   ├── pipeline/                 # 处理管道
│   │   ├── pdf_pipeline.py      # 主处理管道
│   │   ├── layout_analyzer.py   # 版式分析器
│   │   ├── ocr_processor.py     # OCR处理器
│   │   ├── formula_parser.py    # 公式解析器
│   │   ├── table_parser.py      # 表格解析器
│   │   └── md_generator.py      # Markdown生成器
│   ├── models/                   # 数据模型
│   ├── config/                   # 配置管理
│   └── utils/                    # 工具函数
├── config.yaml                   # 主配置文件
├── requirements.txt              # 依赖列表
├── main.py                      # 命令行入口
├── gradio3_final.py             # Web界面
└── logs/                        # 日志目录
```

## 🔧 核心组件

### 1. 版式分析器 (LayoutAnalyzer)
- 使用DocLayout YOLO模型进行区域检测
- 支持文本、标题、表格、图片、公式等多种区域类型
- 高置信度阈值确保检测准确性

### 2. OCR处理器 (OCRProcessor)
- 集成PaddleOCR和RapidOCR
- 支持GPU加速处理
- 多语言文本识别支持

### 3. 公式解析器 (FormulaParser)
- 基于FormulaNet的数学公式识别
- 集成大模型进行错误检测和修复
- 支持复杂的LaTeX公式解析

### 4. 表格解析器 (TableParser)
- 基于RapidTable的高精度表格识别
- 支持复杂表格结构分析
- 大模型备用方案处理复杂表格

### 5. 阅读顺序分析器 (ReadingOrderAnalyzer)
- 基于LayoutReader的智能排序
- 支持多栏文档的阅读顺序分析
- 保持文档的逻辑结构

## ⚙️ 配置选项

### 全局配置
```yaml
layout_analyzer:
  confidence_threshold: 0.45       # 置信度阈值
  use_gpu: true                   # 启用GPU加速

ocr_processor:
  confidence_threshold: 0.75      # OCR置信度阈值
  language: en                    # 识别语言
  use_gpu: true                   # 启用GPU加速

formula_parser:
  confidence_threshold: 0.7      # 公式解析置信度
  use_llm: true                   # 启用大模型辅助

table_parser:
  confidence_threshold: 0.6       # 表格解析置信度
  use_gpu: true                   # 启用GPU加速
```

### LLM配置
```yaml
llm:
  api_key: "your-api-key"         # API密钥
  base_url: "https://api.deepseek.com"  # API地址
  model: "deepseek-chat"          # 模型名称
  temperature: 0.7                # 生成温度
  max_tokens: 4096                # 最大token数
  timeout: 30                     # 超时时间(秒)
  max_retries: 3                  # 最大重试次数
```

## 📊 性能优化

### 多进程处理
```bash
# 使用8个进程并行处理
python main.py -b -w 8 -o output/markdown
```

### GPU加速
确保安装了CUDA版本的PyTorch和相关依赖：
```bash
# 安装CUDA版本依赖
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### 内存优化
- 使用批处理减少内存占用
- 及时释放不需要的资源
- 优化图像处理流程

## 🎯 使用场景

### 1. 学术论文
- 复杂数学公式识别
- 多栏版式处理
- 参考文献格式化

### 2. 技术文档
- 代码块识别
- 表格结构分析
- 技术图表处理

### 3. 商业报告
- 数据表格提取
- 图表标题识别
- 版面布局保持

### 4. 通用文档
- 混合内容处理
- 多语言支持
- 灵活的输出格式

## 🔍 故障排除

### 常见问题

1. **CUDA内存不足**
   - 减少批处理大小
   - 降低输入图像分辨率
   - 使用CPU模式

2. **OCR识别准确率低**
   - 检查图像质量
   - 调整置信度阈值
   - 尝试不同的OCR引擎

3. **公式解析失败**
   - 启用大模型备用方案
   - 检查公式复杂度
   - 更新模型权重

4. **处理速度慢**
   - 启用GPU加速
   - 使用多进程处理
   - 优化配置参数

### 日志分析
系统会自动生成详细的处理日志：
```bash
# 查看最新日志
tail -f logs/pdf_parser_*.log

# 查看错误日志
grep ERROR logs/pdf_parser_*.log
```

## 🤝 贡献指南

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) - OCR引擎
- [RapidOCR](https://github.com/RapidAI/RapidOCR) - 高效OCR引擎
- [DocLayout YOLO](https://github.com/VikParuchuri/detectron2) - 版式分析模型
- [LayoutReader](https://github.com/microsoft/unilm) - 阅读顺序分析
- [FormulaNet](https://github.com-forumattention) - 公式解析模型
- [Gradio](https://github.com/gradio-app/gradio) - Web界面框架

## 📞 联系我们

如有问题或建议，请通过以下方式联系：

- 创建 Issue
- 发送邮件至项目维护者
- 查看项目文档和Wiki

---

**⭐ 如果这个项目对您有帮助，请给我们一个Star！**