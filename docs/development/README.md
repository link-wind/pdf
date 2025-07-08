# 开发指南

本文档提供了PDF解析系统的开发指南，包括项目结构、开发环境设置、代码规范和贡献指南。

## 项目结构

```
pdf-parser/
├── config.yaml            # 默认配置文件
├── LICENSE                # 许可证文件
├── MANIFEST.in            # 打包清单
├── pyproject.toml         # 项目构建配置
├── README.md              # 项目说明
├── requirements.txt       # 依赖列表
├── setup.cfg              # 安装配置
├── setup.py               # 安装脚本
├── data/                  # 数据目录
│   ├── input/             # 输入数据
│   │   ├── samples/       # 示例PDF文件
│   │   └── test/          # 测试PDF文件
│   └── output/            # 输出数据
│       ├── markdown/      # Markdown输出
│       └── temp/          # 临时文件
├── docs/                  # 文档
│   ├── api/               # API文档
│   ├── development/       # 开发文档
│   ├── examples/          # 示例文档
│   └── guides/            # 用户指南
├── logs/                  # 日志目录
├── scripts/               # 脚本
│   ├── setup/             # 环境设置脚本
│   └── tools/             # 工具脚本
├── src/                   # 源代码
│   ├── __init__.py        # 包初始化
│   ├── main.py            # 命令行入口
│   ├── config/            # 配置模块
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── pipeline/          # 处理流程
│   │   ├── __init__.py
│   │   └── pdf_pipeline.py
│   ├── processors/        # 处理器
│   │   ├── __init__.py
│   │   ├── pdf_converter.py
│   │   ├── layout_analyzer.py
│   │   ├── ocr_processor.py
│   │   ├── table_parser.py
│   │   ├── formula_parser.py
│   │   ├── reading_order_analyzer.py
│   │   └── markdown_generator.py
│   └── utils/             # 工具函数
│       ├── __init__.py
│       ├── logging.py
│       ├── visualization.py
│       └── io.py
└── tests/                 # 测试
    ├── __init__.py
    ├── integration/       # 集成测试
    ├── resources/         # 测试资源
    └── unit/              # 单元测试
```

## 开发环境设置

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/pdf-parser.git
cd pdf-parser
```

### 2. 创建虚拟环境

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
```

### 3. 安装开发依赖

```bash
python scripts/setup/setup_dev_env.py
```

这个脚本会自动安装所有依赖，包括开发工具（pytest, black, isort, flake8, mypy等），并设置pre-commit钩子。

### 4. 安装项目为可编辑模式

```bash
pip install -e .
```

## 代码规范

本项目遵循以下代码规范：

- **PEP 8**：Python代码风格指南
- **Black**：代码格式化工具，行长度限制为88字符
- **isort**：导入排序工具，配置为与Black兼容
- **Flake8**：代码检查工具
- **MyPy**：静态类型检查工具

### 代码风格检查和格式化

```bash
# 格式化代码
black src tests scripts

# 排序导入
isort src tests scripts

# 代码检查
flake8 src tests scripts

# 类型检查
mypy src
```

## 测试

### 运行测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit

# 运行集成测试
pytest tests/integration

# 运行带覆盖率报告的测试
pytest --cov=src tests/
```

### 添加测试

- **单元测试**：放在`tests/unit/`目录下，文件名以`test_`开头
- **集成测试**：放在`tests/integration/`目录下，文件名以`test_`开头
- **测试资源**：放在`tests/resources/`目录下

## 开发流程

### 1. 创建分支

```bash
git checkout -b feature/your-feature-name
```

### 2. 开发和测试

- 编写代码
- 添加测试
- 运行测试确保通过
- 格式化和检查代码

### 3. 提交更改

```bash
git add .
git commit -m "feat: add your feature description"
```

我们使用[约定式提交](https://www.conventionalcommits.org/)规范，常用的类型前缀：

- `feat`：新功能
- `fix`：修复bug
- `docs`：文档更改
- `style`：不影响代码含义的更改（空白、格式化等）
- `refactor`：既不修复bug也不添加功能的代码更改
- `perf`：提高性能的代码更改
- `test`：添加或修正测试
- `chore`：对构建过程或辅助工具的更改

### 4. 推送分支

```bash
git push origin feature/your-feature-name
```

### 5. 创建Pull Request

在GitHub上创建Pull Request，描述你的更改和解决的问题。

## 模块开发指南

### 添加新的处理器

1. 在`src/processors/`目录下创建新的处理器文件，例如`new_processor.py`
2. 实现处理器类，遵循现有处理器的接口模式
3. 在`src/processors/__init__.py`中导出新的处理器
4. 在`src/pipeline/pdf_pipeline.py`中集成新的处理器
5. 在`src/config/settings.py`中添加新的配置类
6. 添加单元测试和集成测试

### 示例：添加新的处理器

```python
# src/processors/new_processor.py
class NewProcessor:
    """新处理器描述"""
    
    def __init__(self, config):
        """初始化处理器
        
        Args:
            config: 处理器配置
        """
        self.config = config
        # 初始化其他属性
        
    def process(self, input_data):
        """处理数据
        
        Args:
            input_data: 输入数据
            
        Returns:
            处理结果
        """
        # 实现处理逻辑
        return result
```

## 文档

### 更新文档

- **API文档**：更新`docs/api/`目录下的文档
- **用户指南**：更新`docs/guides/`目录下的文档
- **开发文档**：更新`docs/development/`目录下的文档
- **示例**：更新`docs/examples/`目录下的文档

### 文档风格

- 使用Markdown格式
- 包含清晰的标题和小节
- 提供代码示例和使用场景
- 解释参数和返回值

## 版本控制

我们使用[语义化版本](https://semver.org/)规范：

- **主版本号**：不兼容的API更改
- **次版本号**：向后兼容的功能性新增
- **修订号**：向后兼容的问题修正

## 发布流程

1. 更新版本号（在`src/__init__.py`中）
2. 更新CHANGELOG.md
3. 创建发布分支`release/vX.Y.Z`
4. 创建Pull Request并合并到主分支
5. 创建发布标签
6. 构建和发布包

```bash
# 构建包
python -m build

# 发布到PyPI
python -m twine upload dist/*
```

## 贡献指南

我们欢迎各种形式的贡献，包括但不限于：

- 代码贡献
- 文档改进
- Bug报告
- 功能请求
- 代码审查

请确保在提交贡献之前：

1. 讨论你计划进行的更改（通过Issue或讨论）
2. 遵循代码规范和开发流程
3. 添加适当的测试和文档
4. 更新CHANGELOG.md（如适用）

## 许可证

本项目采用MIT许可证。详情请参阅[LICENSE](../../LICENSE)文件。