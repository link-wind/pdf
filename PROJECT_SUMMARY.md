# PDF Pipeline 项目完成总结

## 项目状态
✅ **已完成**：PDF批量转Markdown功能，支持GPU加速的PaddleOCR

## 主要功能
1. **批量处理**：支持`data/input/samples`目录下所有PDF文件批量转换
2. **Markdown生成**：自动过滤[Figure]、[FigureCaption]等占位符，生成干净的Markdown文档
3. **GPU加速**：PaddleOCR支持GPU加速，提高处理速度
4. **多重初始化**：OCR处理器具有多种初始化方式，提高兼容性

## 使用方法

### 1. 环境安装
```bash
# 安装依赖
pip install -r requirements.txt

# 如果遇到PaddleOCR版本兼容问题，可以重新安装：
pip uninstall paddleocr paddlepaddle paddlepaddle-gpu -y
pip install paddlepaddle-gpu==2.6.0
pip install paddleocr==2.6.1.3
```

### 2. 批量处理
```bash
# 使用命令行工具批量处理
python main.py --batch

# 或指定输出目录
python main.py --batch --output output/custom_markdown
```

### 3. 单文件处理
```bash
# 处理单个PDF文件
python main.py -i "input.pdf" -o "output.md"
```

### 4. 测试批量处理
```bash
# 运行测试脚本
python test_batch_process.py
```

## 配置文件说明

### config.yaml 主要配置
```yaml
ocr_processor:
  confidence_threshold: 0.9
  det_db_box_thresh: 0.6
  det_db_thresh: 0.3
  engine: paddleocr
  language: ch
  use_gpu: true  # 启用GPU加速

layout_analyzer:
  use_gpu: true
  confidence_threshold: 0.6
  
md_generator:
  include_metadata: true
  preserve_formatting: false
  # 自动过滤占位符
```

## 文件结构
```
pdf/
├── data/
│   └── input/
│       └── samples/          # 批量处理输入目录
├── output/
│   └── markdown/            # 批量处理输出目录
├── src/
│   ├── pipeline/
│   │   ├── ocr_processor.py  # OCR处理器（PaddleOCR + GPU）
│   │   ├── md_generator.py   # Markdown生成器（过滤占位符）
│   │   └── layout_analyzer.py # 版式分析器
│   └── config/
├── main.py                  # 主程序（支持批量处理）
├── test_batch_process.py    # 批量处理测试脚本
├── config.yaml             # 配置文件
└── requirements.txt        # 依赖包
```

## 核心改进

### 1. OCR处理器 (ocr_processor.py)
- ✅ 支持PaddleOCR GPU加速
- ✅ 多种初始化方式，提高兼容性
- ✅ 自动检测GPU可用性
- ✅ 详细的错误处理和日志记录

### 2. 版式分析器 (layout_analyzer.py)
- ✅ 不为图片和标题区域生成占位符
- ✅ 只为需要后续处理的区域生成占位符
- ✅ 支持多种区域类型映射

### 3. Markdown生成器 (md_generator.py)
- ✅ 强化占位符过滤逻辑
- ✅ 支持正则表达式过滤多种占位符模式
- ✅ 跳过图片和标题区域，不生成任何占位符内容

### 4. 批量处理 (main.py)
- ✅ 支持批量处理模式 (`--batch`)
- ✅ 自动创建输出目录
- ✅ 处理进度跟踪和统计
- ✅ 详细的错误处理

### 5. 表格解析器 (table_parser.py)
- ✅ 支持多种解析器类型
- ✅ 降级处理：如果PPStructure不可用，使用OCR基础解析
- ✅ 错误处理和日志记录

## 使用示例

### 批量处理示例
```python
# 将PDF文件放入 data/input/samples/ 目录
# 运行批量处理
python main.py --batch

# 结果将保存在 output/markdown/ 目录
# 每个PDF文件对应一个同名的.md文件
```

### 单文件处理示例
```python
python main.py -i "太极计划星间激光通信测距的伪随机码选取.pdf" -o "output.md"
```

## 注意事项

1. **GPU支持**：确保已安装CUDA和cuDNN，PaddleOCR会自动检测GPU
2. **内存管理**：批量处理大量PDF时注意内存使用
3. **版本兼容**：如遇到PaddleOCR版本问题，请按照上述方法重新安装
4. **占位符过滤**：系统会自动过滤所有[Figure]、[FigureCaption]等占位符

## 性能优化

1. **GPU加速**：PaddleOCR支持GPU加速，大幅提升OCR处理速度
2. **批量处理**：支持批量处理多个PDF文件
3. **内存优化**：处理完成后自动清理资源
4. **缓存机制**：版式分析结果可缓存复用

## 故障排除

1. **OCR引擎初始化失败**：检查PaddleOCR和PaddlePaddle版本兼容性
2. **GPU不可用**：检查CUDA安装和环境变量
3. **内存不足**：减少批量处理的并发数量
4. **依赖冲突**：使用虚拟环境重新安装依赖

项目已完成所有核心功能，可以开始使用！
