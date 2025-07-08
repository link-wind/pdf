<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# PDF Pipeline 解析系统 - Copilot 指令

## 项目概述
这是一个Pipeline式PDF文档解析系统，用于处理科技文献、开发文档和通用文档。

## 架构原则
- 采用模块化设计，每个处理步骤独立成模块
- 使用Pipeline模式串联各个处理环节
- 支持配置驱动的参数调整
- 遵循单一职责原则

## 核心流程
1. PDF → 图片转换
2. 版式分析和区域检测
3. 多元素并行解析：OCR、表格、公式、图片
4. 阅读顺序重构
5. Markdown文档生成

## 代码规范
- 使用类型提示（Type Hints）
- 遵循PEP 8代码风格
- 使用Loguru进行日志记录
- 异常处理要具体和有意义
- 文档字符串使用Google风格

## 依赖管理
- 核心依赖：PyMuPDF, PaddleOCR, PyTorch
- 图像处理：OpenCV, Pillow, scikit-image  
- 机器学习：transformers, ultralytics
- 数据处理：pandas, numpy

## 性能考虑
- 支持批量处理
- GPU加速（当可用时）
- 内存优化处理大文档
- 缓存中间结果

## 测试策略
- 单元测试覆盖核心算法
- 集成测试验证Pipeline流程
- 性能测试确保处理效率
- 使用真实PDF样本进行测试
