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

# 尝试导入LLM工具
try:
    from ..utils.llm import parse_formula_with_llm
    llm_available = True
    logger.info("LLM公式解析功能可用")
except ImportError:
    llm_available = False
    logger.warning("无法导入LLM工具，不使用大模型解析公式")


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
        
        # 大模型配置
        self.use_llm = getattr(self.config, 'use_llm', False)
        self.llm_api_key = getattr(self.config, 'llm_api_key', None)
        self.llm_fallback = getattr(self.config, 'llm_fallback', True)  # 当其他方法失败时是否使用LLM
        self.llm_priority = getattr(self.config, 'llm_priority', False)  # 是否优先使用LLM
        self.llm_timeout = getattr(self.config, 'llm_timeout', 30)  # API调用超时时间（秒）
        self.llm_max_retries = getattr(self.config, 'llm_max_retries', 3)  # 失败时最大重试次数
        
        # 如果设置了优先使用LLM但LLM不可用，打印警告
        if self.use_llm and not llm_available:
            logger.warning("配置了使用LLM但LLM模块不可用，将使用其他方法解析公式")
        
        self._init_parser()
        logger.info("公式解析器初始化完成")
    
    def _init_parser(self) -> None:
        """初始化PaddleX PP-FormulaNet模型"""
        # 如果优先使用LLM且LLM可用，则不初始化传统模型
        if self.use_llm and llm_available and self.llm_priority:
            logger.info("优先使用LLM解析公式，不初始化传统模型")
            self.formula_model = None
            return
        
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
            # 如果优先使用LLM，先尝试LLM解析
            if self.use_llm and llm_available and self.llm_priority:
                logger.info("使用LLM进行公式解析")
                result = self._parse_with_llm(formula_region)
                if result and len(result) > 0:
                    return result
                    
                # 如果LLM解析失败且只使用LLM，则返回空结果
                if self.formula_model is None:
                    logger.warning("LLM公式解析失败，无备选解析器")
                    return []
                    
                # 否则继续尝试传统模型
                logger.info("LLM解析失败，尝试传统模型")
                
            # 使用传统模型解析
            if self.formula_model is None:
                if not (self.use_llm and llm_available and self.llm_fallback):
                    logger.warning("公式解析模型未初始化，且无法使用LLM备用，跳过公式解析")
                    return []
                else:
                    # 使用LLM作为备选
                    logger.info("传统模型未初始化，使用LLM作为备选")
                    return self._parse_with_llm(formula_region)
            
            # 使用传统模型解析
            result = self._parse_with_pp_formulanet(formula_region)
            
            # 如果传统模型解析失败，使用LLM作为后备
            if (not result or len(result) == 0 or self._has_latex_error(result)) and self.use_llm and llm_available and self.llm_fallback:
                logger.info("传统模型解析失败或有错误，使用LLM作为后备")
                llm_result = self._parse_with_llm(formula_region)
                if llm_result and len(llm_result) > 0:
                    return llm_result
                    
            return result
                
        except Exception as e:
            logger.error(f"公式解析失败: {str(e)}")
            
            # 如果启用了LLM作为后备，即使出错也尝试使用LLM
            if self.use_llm and llm_available and self.llm_fallback:
                try:
                    logger.info("常规解析出错，尝试使用LLM作为后备")
                    return self._parse_with_llm(formula_region)
                except Exception as llm_e:
                    logger.error(f"LLM后备解析也失败: {str(llm_e)}")
                    
            return []
    
    def _has_latex_error(self, formula_list: List[FormulaData]) -> bool:
        """检查LaTeX公式是否有错误或会导致Markdown渲染失败"""
        for formula in formula_list:
            latex = formula.latex
            if not latex:
                continue
                
            # 检查常见的导致Markdown/MathJax渲染失败的错误
            
            # 1. 检查未定义的控制序列（大小写错误常见问题）
            undefined_commands = [
                "\\Tilde", "\\Alpha", "\\Beta", "\\Epsilon", "\\Zeta", "\\Eta", "\\Iota", 
                "\\Kappa", "\\Mu", "\\Nu", "\\Omicron", "\\Rho", "\\Tau", "\\Chi", "\\Vert"
            ]
            for cmd in undefined_commands:
                if cmd in latex:
                    logger.warning(f"检测到未定义的LaTeX命令: {cmd}")
                    return True
            
            # 2. 检查括号不匹配问题
            brackets = {
                '{': '}',
                '[': ']',
                '(': ')',
                '\\{': '\\}',
                '\\[': '\\]',
                '\\(': '\\)',
                '\\begin': '\\end'
            }
            
            # 简单的括号匹配检查
            stack = []
            for i in range(len(latex)):
                # 检查开括号
                for open_bracket, close_bracket in brackets.items():
                    if latex[i:].startswith(open_bracket):
                        stack.append((open_bracket, close_bracket))
                        break
                # 检查闭括号
                for open_bracket, close_bracket in brackets.items():
                    if latex[i:].startswith(close_bracket):
                        if not stack or stack[-1][1] != close_bracket:
                            logger.warning(f"检测到括号不匹配: 预期 {stack[-1][1] if stack else '无'}, 实际 {close_bracket}")
                            return True
                        stack.pop()
                        break
            
            # 如果栈不为空，说明有未闭合的括号
            if stack:
                logger.warning(f"检测到未闭合的括号: {[item[0] for item in stack]}")
                return True
            
            # 3. 检查特殊字符转义问题
            special_chars = ['%', '#', '$', '&', '_', '^']
            for char in special_chars:
                if f"\\{char}" not in latex and char in latex:
                    # 检查特殊情况：$在公式内不需要转义，_在部分环境中不需要转义
                    if char == '$' or char == '_' and ('_{}' in latex or '{_' in latex):
                        continue
                    logger.warning(f"检测到未转义的特殊字符: {char}")
                    return True
            
            # 4. 检查命令与参数之间缺少花括号的问题
            commands_requiring_braces = ['\\frac', '\\sqrt', '\\text', '\\mathbf', '\\mathit', '\\mathrm', '\\mathbb']
            for cmd in commands_requiring_braces:
                if cmd in latex:
                    idx = latex.find(cmd) + len(cmd)
                    if idx < len(latex) and latex[idx] != '{':
                        # 排除有参数的情况，如\sqrt[n]{x}
                        if cmd == '\\sqrt' and latex[idx] == '[':
                            continue
                        logger.warning(f"检测到命令后缺少花括号: {cmd}")
                        return True
            
            # 5. 检查常见的拼写错误和格式问题
            if "\\begin{" in latex and "\\end{" not in latex:
                logger.warning("检测到\\begin环境缺少对应的\\end")
                return True
                
            if "\\end{" in latex and "\\begin{" not in latex:
                logger.warning("检测到\\end环境缺少对应的\\begin")
                return True
            
            # 检查常见的丢失命令
            if latex.count('_') > latex.count('{') + latex.count('^'):
                logger.warning("检测到可能缺少下标的花括号")
                return True
                
            if latex.count('^') > latex.count('{') + latex.count('_'):
                logger.warning("检测到可能缺少上标的花括号")
                return True
                
            # 6. 检查奇怪的字符或非法字符
            illegal_chars = ['\\\\', '\n\n', '\r\r', '\t\t']
            for char in illegal_chars:
                if char in latex:
                    logger.warning(f"检测到非法字符序列: {char}")
                    return True
            
            # 7. 尝试验证公式的合法性（如果启用验证）
            if getattr(self.config, 'enable_latex_validation', False):
                try:
                    is_valid = self._validate_latex(latex)
                    if not is_valid:
                        logger.warning("LaTeX验证失败")
                        return True
                except Exception as e:
                    logger.error(f"LaTeX验证出错: {e}")
                    # 验证出错不一定意味着公式错误
                    
        return False
        
    def _validate_latex(self, latex: str) -> bool:
        """验证LaTeX公式是否有效（可渲染）"""
        try:
            # 尝试通过简单规则验证
            # 1. 检查基本平衡性
            if latex.count('{') != latex.count('}'):
                return False
            if latex.count('[') != latex.count(']'):
                return False
            if latex.count('(') != latex.count(')'):
                return False
                
            # 2. 检查常见的无效序列
            invalid_sequences = ['\\\\{', '\\\\}', '\\\\ ', '\\\\^', '\\\\_', '\\\\$']
            for seq in invalid_sequences:
                if seq in latex:
                    return False
                    
            # 3. 检查命令后是否有内容
            empty_commands = ['\\frac{}{}', '\\sqrt{}', '\\text{}', '\\mathbf{}', '\\sum_{}']
            for cmd in empty_commands:
                if cmd in latex:
                    return False
            
            # 可以添加更多验证规则
            
            # 如果有特定的LaTeX解析库，可以尝试调用库进行验证
            # 例如:
            # from pylatexenc.latex2text import LatexNodes2Text
            # LatexNodes2Text().latex_to_text(latex)
            
            return True
            
        except Exception as e:
            logger.error(f"LaTeX验证异常: {e}")
            return False
    
    def _parse_with_llm(self, formula_region: FormulaRegion) -> List[FormulaData]:
        """使用大模型解析公式"""
        if not llm_available:
            logger.warning("LLM模块不可用，无法使用LLM解析公式")
            return []
            
        try:
            # 提取公式图像
            formula_image = self._extract_formula_image(formula_region)
            if formula_image is None:
                return []
                
            # 保存到临时文件
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                    formula_image.save(tmp_file.name, 'PNG')
                    temp_path = tmp_file.name
                    
                # 调用LLM解析
                logger.info(f"使用LLM解析公式图像: {temp_path}")
                from ..utils.llm import parse_formula_with_llm
                latex_formula = parse_formula_with_llm(
                    image_path=temp_path,
                    api_key=self.llm_api_key,
                    max_retries=self.llm_max_retries,
                    timeout=self.llm_timeout
                )
                
                # 如果解析结果为空，返回空列表
                if not latex_formula:
                    logger.warning("LLM解析结果为空")
                    return []
                    
                # 构建FormulaData对象
                formula_data = FormulaData(
                    latex=latex_formula,
                    confidence=0.95  # LLM置信度，使用默认值
                )
                
                logger.info(f"LLM公式解析成功: {latex_formula[:50]}...")
                return [formula_data]
                
            finally:
                # 清理临时文件
                if temp_path and os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"LLM公式解析失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
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
