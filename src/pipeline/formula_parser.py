"""
公式解析模块 - 简化版
使用PaddleX PP-FormulaNet-L模型进行数学公式识别和LaTeX格式输出
"""

from typing import List, Dict, Any, Optional
import tempfile
import os
from PIL import Image

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from ..config.settings import FormulaParserConfig
from ..models.document import FormulaRegion, FormulaData


class FormulaParser:
    """基于PaddleX PP-FormulaNet-L的公式解析器 - 简化版"""
    
    def __init__(self, config: FormulaParserConfig):
        """
        初始化公式解析器
        
        Args:
            config: 公式解析器配置
        """
        self.config = config
        self.formula_model = None
        self._init_parser()
        logger.info("公式解析器初始化完成")
    
    def _init_parser(self) -> None:
        """初始化PaddleX PP-FormulaNet模型"""
        try:
            from paddlex import create_model
            
            # 使用默认的Large版本
            model_name = "PP-FormulaNet-L"
            
            # 创建模型
            self.formula_model = create_model(model_name=model_name)
            logger.info(f"PaddleX {model_name} 公式识别模型初始化成功")
            
        except ImportError as e:
            logger.error("PaddleX未安装，请运行: pip install paddlex")
            self.formula_model = None
        except Exception as e:
            logger.error(f"PP-FormulaNet模型初始化失败: {str(e)}")
            self.formula_model = None
    
    def parse(self, formula_region: FormulaRegion) -> List[FormulaData]:
        """
        解析公式区域
        
        Args:
            formula_region: 公式区域对象
            
        Returns:
            List[FormulaData]: 解析后的公式数据列表
        """
        try:
            if self.formula_model is None:
                logger.warning("PP-FormulaNet模型未初始化，跳过公式解析")
                return []
            
            return self._parse_with_pp_formulanet(formula_region)
                
        except Exception as e:
            logger.error(f"公式解析失败: {str(e)}")
            return []
    
    def _parse_with_pp_formulanet(self, formula_region: FormulaRegion) -> List[FormulaData]:
        """使用PP-FormulaNet-L解析公式"""
        logger.debug(f"解析公式区域: {formula_region.bbox}")
        
        try:
            # 提取公式图像
            formula_image = self._extract_formula_image(formula_region)
            if formula_image is None:
                return []
            
            # 保存临时图像文件
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                formula_image.save(temp_file.name)
                temp_path = temp_file.name
            
            try:
                # 使用模型预测
                output = self.formula_model.predict(input=temp_path, batch_size=1)
                output_list = list(output) if output else []
                
                formulas = []
                for res in output_list:
                    # 提取LaTeX结果
                    latex_formula = self._extract_latex_from_result(res)
                    if latex_formula:
                        confidence = self._extract_confidence_from_result(res)
                        
                        formula_data = FormulaData(
                            latex=self._clean_latex(latex_formula),
                            confidence=confidence
                        )
                        formulas.append(formula_data)
                        logger.debug(f"识别公式: {latex_formula[:50]}...")
                
                return formulas
                
            finally:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            
        except Exception as e:
            logger.error(f"公式解析错误: {str(e)}")
            return []
    
    def _extract_formula_image(self, formula_region: FormulaRegion) -> Optional[Image.Image]:
        """从公式区域提取图像"""
        try:
            # 获取页面图像
            page_image = None
            if hasattr(formula_region, 'page_image') and formula_region.page_image:
                page_image = formula_region.page_image
            elif hasattr(formula_region, 'page_path') and formula_region.page_path:
                page_image = Image.open(formula_region.page_path)
            else:
                logger.warning("无法获取页面图像")
                return None
            
            # 获取边界框
            bbox = formula_region.bbox
            
            # 基本边距
            padding = 10
            crop_box = (
                max(0, int(bbox.x1 - padding)),
                max(0, int(bbox.y1 - padding)),
                min(page_image.width, int(bbox.x2 + padding)),
                min(page_image.height, int(bbox.y2 + padding))
            )
            
            formula_image = page_image.crop(crop_box)
            
            # 基本验证
            if formula_image.width < 10 or formula_image.height < 10:
                logger.warning("公式图像太小")
                return None
            
            # 转换为RGB模式
            if formula_image.mode != 'RGB':
                formula_image = formula_image.convert('RGB')
            
            return formula_image
            
        except Exception as e:
            logger.error(f"公式图像提取失败: {str(e)}")
            return None
    
    def _extract_latex_from_result(self, result) -> Optional[str]:
        """从PP-FormulaNet结果中提取LaTeX公式"""
        try:
            latex_result = None
            
            # 尝试多种可能的属性名
            if hasattr(result, 'rec_formula'):
                latex_result = result.rec_formula
            elif hasattr(result, 'latex'):
                latex_result = result.latex
            elif hasattr(result, 'formula'):
                latex_result = result.formula
            elif hasattr(result, 'text'):
                latex_result = result.text
            elif isinstance(result, dict):
                latex_result = (result.get('rec_formula') or 
                               result.get('latex') or 
                               result.get('formula') or 
                               result.get('text'))
            else:
                # 尝试字符串转换
                latex_str = str(result)
                if latex_str and not latex_str.startswith('<'):
                    latex_result = latex_str
            
            return latex_result if latex_result else None
            
        except Exception as e:
            logger.error(f"LaTeX提取失败: {str(e)}")
            return None
    
    def _extract_confidence_from_result(self, result) -> float:
        """从PP-FormulaNet结果中提取置信度"""
        try:
            if hasattr(result, 'confidence'):
                return float(result.confidence)
            elif hasattr(result, 'score'):
                return float(result.score)
            elif isinstance(result, dict):
                conf = result.get('confidence') or result.get('score')
                if conf is not None:
                    return float(conf)
            
            # 默认置信度
            return 0.85
            
        except Exception:
            return 0.85
    
    def _clean_latex(self, latex: str) -> str:
        """返回原始LaTeX公式，不进行清理"""
        return latex if latex else ""
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的输出格式"""
        return ['latex']
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            'name': 'PP-FormulaNet-L',
            'framework': 'PaddleX',
            'task': 'Formula Recognition',
            'model_loaded': self.formula_model is not None
        }
