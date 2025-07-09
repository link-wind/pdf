"""
配置管理模块
支持YAML配置文件和默认配置
"""

from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
import yaml

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class PDFConverterConfig:
    """PDF转换器配置"""
    dpi: int = 300
    format: str = 'PNG'  # PNG, JPEG, TIFF, BMP, PPM
    quality: int = 95  # JPEG质量设置
    poppler_path: Optional[str] = None  # poppler工具路径
    use_cairo: bool = True  # 使用cairo后端
    single_thread: bool = True  # 单线程处理
    
    
@dataclass
class LayoutAnalyzerConfig:
    """版式分析器配置"""
    # 模型加载配置
    model_path: Optional[str] = "doclayout.pt"  # 本地模型路径
    model_type: str = "doclayout"  # 只支持 "doclayout"
    
    # 统一的类别映射
    category_mapping: Dict[int, str] = field(default_factory=lambda: {
        0: 'Title',          # 标题
        1: 'PlainText',      # 普通文本
        2: 'Abandon',        # 页眉页脚等舍弃内容
        3: 'Figure',         # 图片
        4: 'FigureCaption',  # 图片标题
        5: 'Table',          # 表格
        6: 'TableCaption',   # 表格标题
        7: 'TableFootnote',  # 表格脚注
        8: 'IsolateFormula', # 行间公式
        9: 'FormulaCaption'  # 公式标号
    })
    
    # 推理配置
    confidence_threshold: float = 0.4
    nms_threshold: float = 0.4
    iou_threshold: float = 0.45  # IoU阈值，用于NMS去除重复检测
    use_gpu: bool = True
    batch_size: int = 1
    
    # 模型推理配置
    input_size: int = 1024  # 输入图像尺寸
    max_det: int = 300  # 最大检测数量
    
    # 后处理配置
    min_region_area: float = 50.0  # 最小区域面积
    
    # 可视化配置
    visualization_enabled: bool = True
    show_confidence: bool = True
    show_class_names: bool = True
    bbox_thickness: int = 2
    
    # 性能优化配置
    enable_mixed_precision: bool = True  # 混合精度
    optimize_for_inference: bool = True  # 推理优化
    cache_model: bool = True  # 缓存模型
    

@dataclass
class OCRProcessorConfig:
    """OCR处理器配置"""
    engine: str = 'paddleocr'  # paddleocr, easyocr, tesseract
    language: str = 'ch'  # ch, en, ch_en
    confidence_threshold: float = 0.8
    use_gpu: bool = True
    det_db_thresh: float = 0.3
    det_db_box_thresh: float = 0.6
    

@dataclass
class TableParserConfig:
    """表格解析器配置"""
    use_gpu: bool = True  # 是否使用GPU加速
    confidence_threshold: float = 0.8  # 置信度阈值
    # LLM相关配置
    use_llm: bool = False  # 是否使用LLM解析表格
    llm_api_key: Optional[str] = None  # LLM API密钥，为None时使用默认值
    llm_fallback: bool = True  # 当其他方法失败时是否使用LLM作为后备
    llm_priority: bool = False  # 是否优先使用LLM（如果为True，会在其他方法之前先尝试LLM）
    

@dataclass
class FormulaParserConfig:
    """公式解析器配置"""
    engine: str = 'pp_formulanet'  # pp_formulanet
    model_size: str = "L"          # S, M, L 三个版本
    confidence_threshold: float = 0.7
    max_formula_width: int = 1000
    max_formula_height: int = 200
    enable_latex_validation: bool = True
    

@dataclass
class ReadingOrderConfig:
    """阅读顺序分析器配置"""
    algorithm: str = 'layoutreader'  # spatial, ml_based, layoutreader
    column_detection: bool = True
    merge_threshold: float = 0.1
    
    # LayoutLMv3深度学习模型配置（仅支持该模型）
    layout_reader_model_path: str = "hantian/layoutreader"
    num_reading_labels: int = 10  # 阅读顺序标签数量
    max_sequence_length: int = 512
    batch_size: int = 1
    confidence_threshold: float = 0.5
    
    # 深度学习增强配置
    use_layoutlmv3: bool = True
    

@dataclass
class MarkdownGeneratorConfig:
    """Markdown生成器配置"""
    include_metadata: bool = True
    include_page_breaks: bool = True
    table_format: str = 'markdown'  # markdown, html
    formula_format: str = 'latex'  # latex, text
    image_format: str = 'png'  # png, jpg
    line_break_style: str = 'double'  # single, double
    max_line_length: int = 80
    preserve_formatting: bool = False
    # 标题级别判断阈值（基于字体大小）
    title_level_thresholds: Dict[str, int] = field(default_factory=lambda: {
        'level_1': 28,    # 一级标题字体大小阈值
        'level_2': 22,    # 二级标题字体大小阈值  
        'level_3': 18,    # 三级标题字体大小阈值
        'level_4': 16,    # 四级标题字体大小阈值
        'level_5': 14,    # 五级标题字体大小阈值
    })


@dataclass 
class Settings:
    """全局配置设置"""
    pdf_converter: PDFConverterConfig = field(default_factory=PDFConverterConfig)
    layout_analyzer: LayoutAnalyzerConfig = field(default_factory=LayoutAnalyzerConfig)
    ocr_processor: OCRProcessorConfig = field(default_factory=OCRProcessorConfig)
    table_parser: TableParserConfig = field(default_factory=TableParserConfig)
    formula_parser: FormulaParserConfig = field(default_factory=FormulaParserConfig)
    reading_order: ReadingOrderConfig = field(default_factory=ReadingOrderConfig)
    md_generator: MarkdownGeneratorConfig = field(default_factory=MarkdownGeneratorConfig)
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化配置
        
        Args:
            config_path: 配置文件路径，如果为None则使用项目根目录下的config.yaml
        """
        # 首先设置默认值
        self.pdf_converter = PDFConverterConfig()
        self.layout_analyzer = LayoutAnalyzerConfig()
        self.ocr_processor = OCRProcessorConfig()
        self.table_parser = TableParserConfig()
        self.formula_parser = FormulaParserConfig()
        self.reading_order = ReadingOrderConfig()
        self.md_generator = MarkdownGeneratorConfig()
        
        # 如果没有指定配置文件，使用项目根目录下的config.yaml
        if config_path is None:
            default_config_path = Path(__file__).parent.parent.parent / "config.yaml"
            if default_config_path.exists():
                config_path = str(default_config_path)
                logger.info(f"使用默认配置文件: {config_path}")
        
        # 如果提供了配置文件，则加载配置
        if config_path:
            self.load_from_file(config_path)
        
        # 版式分析器配置已经在LayoutAnalyzerConfig中完成
        logger.info("配置初始化完成")
    
    def load_from_file(self, config_path: str) -> None:
        """从YAML文件加载配置
        
        Args:
            config_path: 配置文件路径
        """
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                logger.warning(f"配置文件不存在: {config_path}")
                return
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data:
                logger.warning("配置文件为空或格式错误")
                return
            
            # 更新各模块配置
            self._update_config_from_dict(config_data)
            logger.info(f"配置已从文件加载: {config_path}")
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
    
    def _update_config_from_dict(self, config_data: Dict[str, Any]) -> None:
        """从字典更新配置
        
        Args:
            config_data: 配置数据字典
        """
        try:
            # 更新PDF转换器配置
            if 'pdf_converter' in config_data:
                self._update_dataclass_from_dict(
                    self.pdf_converter, 
                    config_data['pdf_converter']
                )
            
            # 更新版式分析器配置
            if 'layout_analyzer' in config_data:
                self._update_dataclass_from_dict(
                    self.layout_analyzer, 
                    config_data['layout_analyzer']
                )
            
            # 更新OCR处理器配置
            if 'ocr_processor' in config_data:
                self._update_dataclass_from_dict(
                    self.ocr_processor, 
                    config_data['ocr_processor']
                )
            
            # 更新表格解析器配置
            if 'table_parser' in config_data:
                self._update_dataclass_from_dict(
                    self.table_parser, 
                    config_data['table_parser']
                )
            
            # 更新公式解析器配置
            if 'formula_parser' in config_data:
                self._update_dataclass_from_dict(
                    self.formula_parser, 
                    config_data['formula_parser']
                )
            
            # 更新阅读顺序配置
            if 'reading_order' in config_data:
                self._update_dataclass_from_dict(
                    self.reading_order, 
                    config_data['reading_order']
                )
            
            # 更新Markdown生成器配置
            if 'md_generator' in config_data:
                self._update_dataclass_from_dict(
                    self.md_generator, 
                    config_data['md_generator']
                )
                
        except Exception as e:
            logger.error(f"配置更新失败: {str(e)}")
    
    def _update_dataclass_from_dict(self, obj, data: Dict[str, Any]) -> None:
        """从字典更新dataclass对象
        
        Args:
            obj: 要更新的dataclass对象
            data: 配置数据字典
        """
        try:
            for key, value in data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)
                else:
                    logger.warning(f"未知配置项: {key}")
        except Exception as e:
            logger.error(f"dataclass更新失败: {str(e)}")
    
    def save_to_file(self, config_path: str) -> None:
        """保存配置到YAML文件
        
        Args:
            config_path: 配置文件路径
        """
        try:
            config_data = {
                'pdf_converter': self._dataclass_to_dict(self.pdf_converter),
                'layout_analyzer': self._dataclass_to_dict(self.layout_analyzer),
                'ocr_processor': self._dataclass_to_dict(self.ocr_processor),
                'table_parser': self._dataclass_to_dict(self.table_parser),
                'formula_parser': self._dataclass_to_dict(self.formula_parser),
                'reading_order': self._dataclass_to_dict(self.reading_order),
                'md_generator': self._dataclass_to_dict(self.md_generator),
            }
            
            config_file = Path(config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, 
                         allow_unicode=True, indent=2)
            
            logger.info(f"配置已保存到文件: {config_path}")
            
        except Exception as e:
            logger.error(f"保存配置文件失败: {str(e)}")
    
    def _dataclass_to_dict(self, obj) -> Dict[str, Any]:
        """将dataclass对象转换为字典
        
        Args:
            obj: dataclass对象
            
        Returns:
            Dict[str, Any]: 配置字典
        """
        return {k: v for k, v in obj.__dict__.items()}
    
    @classmethod
    def from_yaml(cls, config_path: str) -> 'Settings':
        """从YAML配置文件创建Settings实例
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            Settings: 配置实例
        """
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                logger.warning(f"配置文件不存在: {config_path}，使用默认配置")
                return cls()
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data:
                logger.warning("配置文件为空或格式错误，使用默认配置")
                return cls()
            
            # 创建新的Settings实例
            settings = cls()
            
            # 从字典更新配置
            settings._update_config_from_dict(config_data)
            
            logger.info(f"配置已从文件加载: {config_path}")
            return settings
            
        except Exception as e:
            logger.error(f"从YAML文件加载配置失败: {str(e)}，使用默认配置")
            return cls()
    

def load_config(config_path: Optional[str] = None) -> Settings:
    """便捷的配置加载函数
    
    Args:
        config_path: 配置文件路径，如果为None则使用默认配置
        
    Returns:
        Settings: 配置实例
    """
    if config_path is None:
        # 尝试寻找默认配置文件
        default_paths = [
            "config.yaml",
            "config.yml",
            "configs/config.yaml",
            "configs/config.yml",
        ]
        
        for path in default_paths:
            if Path(path).exists():
                config_path = path
                break
        
        if config_path is None:
            logger.info("未找到配置文件，使用默认配置")
            return Settings()
    
    return Settings.from_yaml(config_path)
