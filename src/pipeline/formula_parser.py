"""
公式解析模块 - 简化版
使用PaddleX PP-FormulaNet-L模型进行数学公式识别和LaTeX格式输出
"""

from typing import List, Dict, Any, Optional
import tempfile
import os
import re
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
    from ..utils.llm_aided import correct_formula_with_llm
    llm_available = True
    logger.info("LLM公式解析功能可用")
except ImportError:
    llm_available = False
    logger.warning("无法导入LLM工具，不使用大模型解析公式")


class FormulaParser:
    """基于PaddleX PP-FormulaNet-L的公式解析器 - 简化版"""
    
    def __init__(self, full_config: object):
        """
        初始化公式解析器
        
        Args:
            full_config: 完整的应用配置对象
        """
        self.full_config = full_config
        self.config = getattr(full_config, 'formula_parser', FormulaParserConfig())
        self.formula_model = None
        
        # 大模型配置
        self.use_llm = getattr(self.config, 'use_llm', False)
        self.llm_fallback = getattr(self.config, 'llm_fallback', True)  # 当其他方法失败时是否使用LLM
        self.llm_priority = getattr(self.config, 'llm_priority', False)  # 是否优先使用LLM
        
        # 从全局配置获取LLM详细信息
        self.llm_config = getattr(full_config, 'llm', None)
        if not self.llm_config:
            logger.warning("全局LLM配置未找到，LLM相关功能可能无法正常使用")

        # 如果设置了优先使用LLM但LLM不可用，打印警告
        if self.use_llm and not llm_available:
            logger.warning("配置了使用LLM但LLM模块不可用，将使用其他方法解析公式")
        llm_settings = getattr(full_config, 'llm', {})
        self.llm_api_key = getattr(llm_settings, 'api_key', None)
        self.llm_timeout = getattr(llm_settings, 'timeout', 30)
        self.llm_max_retries = getattr(llm_settings, 'max_retries', 3)
        
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
            model_name = "PP-FormulaNet_plus-S"
            
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
        """检查LaTeX公式是否有严重错误（简化版检查）"""
        for formula in formula_list:
            latex = formula.latex
            if not latex:
                continue
                
            # 基本的语法检查
            try:
                # 检查基本的花括号平衡
                if latex.count('{') != latex.count('}'):
                    logger.warning("检测到花括号不平衡")
                    return True
                    
                # 检查是否包含明显的错误标记
                error_markers = ['ERROR', 'UNKNOWN', 'INVALID']
                for marker in error_markers:
                    if marker in latex.upper():
                        logger.warning(f"检测到错误标记: {marker}")
                        return True
                        
            except Exception as e:
                logger.error(f"LaTeX错误检查异常: {e}")
                return True
                    
        return False
        
    # MinerU LaTeX后处理优化函数
    
    def _is_escaped(self, text: str, pos: int) -> bool:
        """检查指定位置的字符是否被反斜杠转义"""
        if pos == 0:
            return False
        
        # 计算前面连续反斜杠的数量
        backslash_count = 0
        i = pos - 1
        while i >= 0 and text[i] == '\\':
            backslash_count += 1
            i -= 1
        
        # 奇数个反斜杠表示被转义
        return backslash_count % 2 == 1
    
    def _fix_unbalanced_braces(self, latex_formula: str) -> str:
        """修复LaTeX公式中花括号不平衡问题"""
        if not latex_formula:
            return latex_formula
            
        stack = []  # 存储左括号的索引
        unmatched = set()  # 存储不匹配括号的索引
        
        # 遍历字符串，检查每个花括号
        for i, char in enumerate(latex_formula):
            if char in ['{', '}']:
                # 检查是否被转义
                if not self._is_escaped(latex_formula, i):
                    if char == '{':
                        stack.append(i)
                    else:  # char == '}'
                        if stack:
                            stack.pop()
                        else:
                            unmatched.add(i)
        
        # 未匹配的左括号也加入删除列表
        unmatched.update(stack)
        
        # 构建新字符串，删除不匹配的括号
        result = ''.join(char for i, char in enumerate(latex_formula) if i not in unmatched)
        
        if unmatched:
            logger.debug(f"修复花括号不平衡: 删除了 {len(unmatched)} 个不匹配的括号")
        
        return result
    
    def _fix_left_right_pairs(self, latex_formula: str) -> str:
        """修复LaTeX公式中\left和\right配对问题"""
        if not latex_formula or '\\left' not in latex_formula:
            return latex_formula
            
        # 简化版实现：确保\left和\right成对出现
        left_pattern = re.compile(r'\\left([\(\[\{\|\.])')
        right_pattern = re.compile(r'\\right([\)\]\}\|\.])')
        
        left_matches = list(left_pattern.finditer(latex_formula))
        right_matches = list(right_pattern.finditer(latex_formula))
        
        # 如果数量不匹配，尝试简单修复
        if len(left_matches) != len(right_matches):
            logger.debug(f"检测到\\left和\\right数量不匹配: {len(left_matches)} vs {len(right_matches)}")
            
            # 简单策略：如果left多于right，在末尾添加right
            if len(left_matches) > len(right_matches):
                missing_rights = len(left_matches) - len(right_matches)
                latex_formula += ' \\right.' * missing_rights
            # 如果right多于left，在开头添加left
            elif len(right_matches) > len(left_matches):
                missing_lefts = len(right_matches) - len(left_matches)
                latex_formula = '\\left. ' * missing_lefts + latex_formula
        
        return latex_formula
    
    def _fix_latex_environments(self, latex_formula: str) -> str:
        """修复LaTeX环境标签配对问题"""
        if not latex_formula or '\\begin{' not in latex_formula:
            return latex_formula
            
        # 支持的环境列表
        environments = ['array', 'matrix', 'pmatrix', 'bmatrix', 'vmatrix', 'Bmatrix', 'Vmatrix', 'cases', 'aligned', 'gathered']
        
        for env in environments:
            begin_pattern = f'\\begin{{{env}}}'
            end_pattern = f'\\end{{{env}}}'
            
            begin_count = latex_formula.count(begin_pattern)
            end_count = latex_formula.count(end_pattern)
            
            if begin_count != end_count:
                logger.debug(f"修复环境 {env}: begin={begin_count}, end={end_count}")
                
                # 如果begin多于end，在末尾添加end
                if begin_count > end_count:
                    missing_ends = begin_count - end_count
                    latex_formula += f' \\end{{{env}}}' * missing_ends
                # 如果end多于begin，在开头添加begin
                elif end_count > begin_count:
                    missing_begins = end_count - begin_count
                    latex_formula = f'\\begin{{{env}}} ' * missing_begins + latex_formula
        
        return latex_formula
    
    def _process_latex(self, input_string: str) -> str:
        """处理LaTeX公式中的反斜杠和特殊字符"""
        if not input_string:
            return input_string
            
        def replace_func(match):
            next_char = match.group(1)
            
            # 特殊字符或空格，保持不变
            if next_char in "#$%&~_^|\\{} \t\n\r\v\f":
                return match.group(0)
            
            # 检查是否为LaTeX命令（两个连续字母）
            if next_char.isalpha():
                pos = match.start() + 2
                if pos < len(input_string) and input_string[pos].isalpha():
                    return match.group(0)  # 保持LaTeX命令不变
            
            # 其他情况添加空格
            return '\\' + ' ' + next_char
        
        return re.sub(r'\\(.)', replace_func, input_string)
    
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
                    
                # 构建FormulaData对象，应用LaTeX后处理优化
                formula_data = FormulaData(
                    latex=self._clean_latex(latex_formula),
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
    
    def _latex_rm_whitespace(self, latex_formula: str) -> str:
        """综合LaTeX后处理优化函数"""
        if not latex_formula:
            return latex_formula
            
        # 1. 修复\left和\right配对问题
        latex_formula = self._fix_left_right_pairs(latex_formula)
        
        # 2. 修复花括号不平衡问题
        latex_formula = self._fix_unbalanced_braces(latex_formula)
        
        # 3. 修复LaTeX环境配对问题
        latex_formula = self._fix_latex_environments(latex_formula)
        
        # 4. 处理反斜杠和特殊字符
        latex_formula = self._process_latex(latex_formula)
        
        # 5. 清理多余空格
        latex_formula = re.sub(r'\s+', ' ', latex_formula)
        latex_formula = latex_formula.strip()
        
        # 6. 移除空的花括号
        latex_formula = re.sub(r'\{\s*\}', '', latex_formula)
        
        # 7. 修复常见的LaTeX错误
        latex_formula = re.sub(r'\\\\+', '\\\\', latex_formula)  # 多个换行符
        latex_formula = re.sub(r'\s*\\\\\s*', '\\\\', latex_formula)  # 换行符周围的空格
        
        # 8. 移除空的数学环境
        latex_formula = re.sub(r'\$\s*\$', '', latex_formula)
        latex_formula = re.sub(r'\\\(\s*\\\)', '', latex_formula)
        latex_formula = re.sub(r'\\\[\s*\\\]', '', latex_formula)
        
        # 9. 命令替换和清理
         # 替换常见的错误命令
        replacements = {
             '\\mathrm{d}': '\\,\\mathrm{d}',  # 微分符号前加间距
             '\\text{ }': '\\,',  # 空文本替换为间距
             '\\left.\\right.': '',  # 移除空的left-right对
             '\\left(\\right)': '()',  # 简化空括号
             '\\left[\\right]': '[]',  # 简化空方括号
             '\\left\{\\right\}': '\{\}',  # 简化空花括号
             '\\,\\,': '\\,',  # 合并重复的间距
             '\\;\\;': '\\;',  # 合并重复的中等间距
             '\\!\\!': '\\!',  # 合并重复的负间距
         }
         
        for old, new in replacements.items():
            latex_formula = latex_formula.replace(old, new)
        
        # 10. 数学符号标准化
        latex_formula = self._normalize_math_symbols(latex_formula)
        
        # 11. 最终清理
        latex_formula = latex_formula.strip()
         
        return latex_formula
    
    def _normalize_math_symbols(self, latex_formula: str) -> str:
        """标准化数学符号"""
        if not latex_formula:
            return latex_formula
            
        # 标准化常见数学符号
        symbol_replacements = {
            # 希腊字母标准化
            '\\Alpha': 'A',
            '\\Beta': 'B', 
            '\\Epsilon': 'E',
            '\\Zeta': 'Z',
            '\\Eta': 'H',
            '\\Iota': 'I',
            '\\Kappa': 'K',
            '\\Mu': 'M',
            '\\Nu': 'N',
            '\\Omicron': 'O',
            '\\Rho': 'P',
            '\\Tau': 'T',
            '\\Chi': 'X',
            
            # 运算符标准化
            '\\times': '\\cdot',  # 统一使用点乘
            '\\ast': '\\cdot',   # 统一使用点乘
            '\\div': '/',        # 除号简化
            
            # 函数名标准化
            '\\sin': '\\sin',
            '\\cos': '\\cos', 
            '\\tan': '\\tan',
            '\\log': '\\log',
            '\\ln': '\\ln',
            '\\exp': '\\exp',
            
            # 括号标准化
            '\\lbrace': '\\{',
            '\\rbrace': '\\}',
            '\\langle': '\\langle',
            '\\rangle': '\\rangle',
        }
        
        for old, new in symbol_replacements.items():
            latex_formula = latex_formula.replace(old, new)
            
        return latex_formula
    
    def _validate_latex(self, latex: str) -> bool:
        """使用pylatexenc验证LaTeX语法"""
        from pylatexenc.latex2text import LatexNodes2Text
        from pylatexenc.latexwalker import LatexWalker
        
        if not latex:
            return True
        
        try:
            # 创建LatexWalker实例来解析LaTeX代码
            walker = LatexWalker(latex)
            # 尝试获取语法树节点，如果语法有误会抛出异常
            walker.get_latex_nodes()
            
            # 尝试将LaTeX转换为文本，这会进一步验证语法
            converter = LatexNodes2Text()
            converter.latex_to_text(latex)
            
            return True
        except Exception as e:
            logger.warning(f"LaTeX验证失败: {str(e)}")
            return False

    def _clean_latex(self, latex_str: str) -> str:
        """清理和验证LaTeX字符串"""
        # 移除多余的$$标记
        cleaned_str = latex_str.strip().strip('$')

        # 检查是否启用LLM校正
        if self.config.use_llm == True:
            logger.info(f"使用LLM校正公式: {cleaned_str[:50]}...")
            # 确保llm_config是一个对象，而不是字典
            llm_config_obj = self.llm_config
            corrected_str = correct_formula_with_llm(cleaned_str, llm_config=llm_config_obj)
            
            # 验证校正后的LaTeX
            if self._validate_latex(corrected_str):
                logger.info(f"LLM校正成功: {corrected_str[:50]}...")
                return corrected_str
            else:
                logger.warning(f"LLM校正后的LaTex无效，返回原始版本: {cleaned_str[:50]}...")
                # 如果校正后仍然无效，则回退到清理后的版本
                # 并验证原始清理后的版本
                if self._validate_latex(cleaned_str):
                    return cleaned_str
                else:
                    logger.warning(f"清理后的LaTex也无效，返回原始字符串: {latex_str[:50]}...")
                    return latex_str # 或者 cleaned_str，取决于策略

        # 如果不使用LLM或LLM校正失败，则验证清理后的字符串
        if self._validate_latex(cleaned_str):
            return cleaned_str
        
        logger.warning(f"清理后的LaTeX无效，返回原始字符串: {latex_str[:50]}...")
        return latex_str
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的输出格式"""
        return ['latex']
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            'name': 'PP-FormulaNet_plus-S',
            'framework': 'PaddleX',
            'task': 'Formula Recognition',
            'model_loaded': self.formula_model is not None
        }
