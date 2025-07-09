# 配置指南

本文档提供了PDF解析系统的配置选项详细说明，帮助您根据需求自定义系统行为。

## 配置文件格式

PDF解析系统使用YAML格式的配置文件。默认配置文件路径为项目根目录下的`config.yaml`。

## 加载配置

您可以通过以下方式加载配置：

```python
from src import load_config

# 加载默认配置文件
config = load_config()

# 加载指定配置文件
config = load_config("path/to/your/config.yaml")
```

## 配置选项

### PDF转换器配置

```yaml
pdf_converter:
  # 图像DPI设置，影响输出图像的质量和大小
  dpi: 300
  # 输出图像格式 (PNG, JPEG)
  format: PNG
  # 图像质量 (1-100)，仅对JPEG格式有效
  quality: 95
  # 是否使用单线程模式
  single_thread: true
  # 是否使用Cairo渲染器
  use_cairo: true
  # Poppler路径，如果为null则使用系统路径
  poppler_path: null
```

### 版式分析器配置

```yaml
layout_analyzer:
  # 模型配置
  model_path: "doclayout.pt"        # DocLayout模型权重文件路径
  model_type: "doclayout"           # 模型类型
  
  # 推理配置
  confidence_threshold: 0.4         # 置信度阈值
  iou_threshold: 0.45               # IoU阈值用于NMS
  use_gpu: false                    # 是否使用GPU
  batch_size: 1                     # 批处理大小
  max_det: 300                      # 最大检测数量
  input_size: 1280                  # 输入图像尺寸
  
  # 后处理配置
  min_region_area: 50.0             # 最小区域面积
  merge_nearby_regions: true        # 合并相邻区域
  
  # 可视化配置
  visualization_enabled: true       # 启用可视化
  show_confidence: true             # 显示置信度
  show_class_names: true            # 显示类别名称
  bbox_thickness: 2                 # 边界框粗细
```

### OCR处理器配置

```yaml
ocr_processor:
  # OCR引擎 (paddleocr, easyocr, tesseract)
  engine: paddleocr
  # 语言设置 (ch: 中文, en: 英文, etc.)
  language: ch
  # 是否使用GPU加速
  use_gpu: false
  # 置信度阈值
  confidence_threshold: 0.9
  # PaddleOCR检测模型参数
  det_db_thresh: 0.3
  det_db_box_thresh: 0.6
```

### 表格解析器配置

```yaml
table_parser:
  # 表格解析方法 (PPStructure, TableNet, etc.)
  method: PPStructure
  # 置信度阈值
  confidence_threshold: 0.8
  # 单元格合并阈值
  merge_threshold: 0.3
  # 最小表格大小（行数）
  min_table_size: 2
```

### 公式解析器配置

```yaml
formula_parser:
  # 公式解析引擎 (pp_formulanet, etc.)
  engine: pp_formulanet
  # 模型大小 (S, M, L)
  model_size: L
  # 置信度阈值
  confidence_threshold: 0.7
  # 是否启用LaTeX验证
  enable_latex_validation: true
  # 最大公式宽度
  max_formula_width: 1000
  # 最大公式高度
  max_formula_height: 500
```

### 阅读顺序分析器配置

```yaml
reading_order:
  # 仅支持LayoutLMv3模型
  use_layoutlmv3: true
  # LayoutLMv3模型路径
  layoutlmv3_model_path: "microsoft/layoutlmv3-base"
  # 批处理大小
  batch_size: 1
  # 最大序列长度
  max_sequence_length: 1024
  # 阅读标签数量
  num_reading_labels: 10
  # 置信度阈值
  confidence_threshold: 0.6
```

### Markdown生成器配置

```yaml
md_generator:
  # 公式格式 (latex, mathml)
  formula_format: latex
  # 图像格式 (png, jpg)
  image_format: png
  # 是否包含元数据
  include_metadata: true
  # 是否包含分页符
  include_page_breaks: true
  # 换行风格 (single, double)
  line_break_style: double
  # 最大行长度
  max_line_length: 80
  # 是否保留原始格式
  preserve_formatting: false
  # 表格格式 (markdown, html)
  table_format: markdown
  # 标题级别阈值
  title_level_thresholds:
    level_1: 18
    level_2: 16
    level_3: 14
    level_4: 12
    level_5: 10
```

## 配置示例

以下是一个完整的配置文件示例：

```yaml
pdf_converter:
  dpi: 300
  format: PNG
  quality: 95
  single_thread: true
  use_cairo: true
  poppler_path: null

layout_analyzer:
  model_path: "doclayout.pt"
  model_type: "doclayout"
  confidence_threshold: 0.4
  iou_threshold: 0.45
  use_gpu: false
  batch_size: 1
  max_det: 300
  input_size: 1280
  min_region_area: 50.0
  merge_nearby_regions: true
  visualization_enabled: true
  show_confidence: true
  show_class_names: true
  bbox_thickness: 2

ocr_processor:
  engine: paddleocr
  language: ch
  use_gpu: false
  confidence_threshold: 0.9
  det_db_thresh: 0.3
  det_db_box_thresh: 0.6

table_parser:
  method: PPStructure
  confidence_threshold: 0.8
  merge_threshold: 0.3
  min_table_size: 2

formula_parser:
  engine: pp_formulanet
  model_size: L
  confidence_threshold: 0.7
  enable_latex_validation: true
  max_formula_width: 1000
  max_formula_height: 500

reading_order:
  algorithm: layoutreader
  use_layoutreader: true
  layout_reader_model_path: hantian/layoutreader
  use_layoutlmv3: true
  column_detection: true
  use_deep_learning_for_columns: true
  fallback_to_spatial: true
  batch_size: 1
  max_sequence_length: 1024
  num_reading_labels: 10
  confidence_threshold: 0.6

md_generator:
  formula_format: latex
  image_format: png
  include_metadata: true
  include_page_breaks: true
  line_break_style: double
  max_line_length: 80
  preserve_formatting: false
  table_format: markdown
  title_level_thresholds:
    level_1: 18
    level_2: 16
    level_3: 14
    level_4: 12
    level_5: 10
```

## 配置优先级

配置的优先级从高到低为：

1. 通过API直接传递的参数
2. 用户指定的配置文件
3. 默认配置文件（项目根目录下的`config.yaml`）
4. 内置默认配置

## 环境变量

您也可以通过环境变量来覆盖配置文件中的设置。环境变量的格式为`PDF_PARSER_{SECTION}_{OPTION}`，例如：

```bash
# 设置PDF转换器的DPI
export PDF_PARSER_PDF_CONVERTER_DPI=600

# 启用GPU加速
export PDF_PARSER_LAYOUT_ANALYZER_USE_GPU=true
```

## 配置验证

系统会在加载配置时自动验证配置的有效性，如果发现无效的配置选项，将会记录警告并使用默认值。