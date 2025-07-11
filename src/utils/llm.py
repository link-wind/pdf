import os
import dashscope
import base64
from pathlib import Path
import tempfile
from typing import List, Dict, Any, Tuple, Optional
import json
import re
import time

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# 默认API密钥
DEFAULT_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "sk-576e3801be4b445eb944b3dd79fa6f9c")

def encode_image_to_base64(image_path):
    """将图像转换为base64编码"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"图像编码失败: {e}")
        return None

def parse_table_with_llm(image_path: str, api_key: str = None) -> Tuple[List[str], List[List[str]]]:
    """
    使用大模型解析表格图像
    
    Args:
        image_path: 表格图像路径
        api_key: API密钥，如果为None则使用默认密钥
    
    Returns:
        Tuple[List[str], List[List[str]]]: 表头和数据行
    """
    try:
        if not os.path.exists(image_path):
            logger.error(f"图像文件不存在: {image_path}")
            return [], []
        
        # 使用提供的API密钥或默认密钥
        api_key = api_key or DEFAULT_API_KEY
        
        # 尝试不同的图像传递方法
        methods = [
            # 方法1: 文件路径
            lambda: {"image": f"file://{os.path.abspath(image_path)}"},
            # 方法2: base64编码
            lambda: {"image": encode_image_to_base64(image_path)},
            # 方法3: data URI格式
            lambda: {"image": f"data:image/png;base64,{encode_image_to_base64(image_path)}"}
        ]
        
        # 最大尝试次数
        max_tries = 3
        last_error = None
        
        for i, get_image_content in enumerate(methods):
            logger.info(f"尝试图像传递方法 {i+1}/{len(methods)}")
            try:
                # 准备请求消息
                messages = [
                    {
                        "role": "user",
                        "content": [
                            get_image_content(),
                            {"text": "这是一张表格图片。请识别表格内容，并以JSON格式返回。JSON格式要求：{\"headers\": [列标题数组], \"rows\": [[第一行数据], [第二行数据], ...]}。请只返回JSON格式，不要有其他描述性文字。"}
                        ]
                    }
                ]
                
                # 调用模型
                logger.info(f"正在调用大模型解析表格: {image_path}")
                response = dashscope.MultiModalConversation.call(
                    api_key=api_key,
                    model='qwen-vl-max-latest',  # 使用具备视觉能力的大模型
                    messages=messages
                )
                
                if not response or not hasattr(response, 'output') or not hasattr(response.output, 'choices'):
                    logger.error(f"大模型返回格式错误: {response}")
                    last_error = f"返回格式错误: {response}"
                    continue
                
                # 获取结果文本
                result_message = response.output.choices[0].message
                if not hasattr(result_message, 'content'):
                    logger.error("大模型返回中缺少content字段")
                    last_error = "返回中缺少content字段"
                    continue
                    
                result_text = result_message.content
                logger.info(f"大模型返回: {str(result_text)[:200]}...")
                
                # 检查返回结果类型并适当处理
                if isinstance(result_text, list):
                    # 如果是列表格式，尝试从列表中提取文本
                    text_contents = []
                    for item in result_text:
                        if isinstance(item, dict) and 'text' in item:
                            text_contents.append(item['text'])
                    result_text = "\n".join(text_contents)
                elif not isinstance(result_text, str):
                    # 如果既不是字符串也不是列表，尝试转换为字符串
                    result_text = str(result_text)
                
                # 从文本中提取JSON
                # 处理可能的markdown格式，例如 ```json {...} ```
                json_match = None
                json_pattern = r'```json\s*([\s\S]*?)\s*```'
                try:
                    matches = re.search(json_pattern, result_text)
                    if matches:
                        json_match = matches.group(1)
                    else:
                        # 尝试直接解析为JSON
                        json_match = result_text
                except TypeError as e:
                    logger.error(f"正则表达式匹配失败: {e}, 结果类型: {type(result_text)}")
                    json_match = result_text  # 尝试直接使用
                    
                # 尝试解析JSON
                try:
                    # 清理可能的不必要文本
                    json_text = json_match.strip()
                    # 移除可能的前导和尾随文本
                    if json_text.find('{') >= 0:
                        json_text = json_text[json_text.find('{'):json_text.rfind('}')+1]
                        
                    table_data = json.loads(json_text)
                    
                    # 提取表头和行
                    headers = table_data.get('headers', [])
                    rows = table_data.get('rows', [])
                    
                    # 验证结果是否有效
                    if headers or rows:  # 只要有一项不为空就返回结果
                        logger.info(f"成功解析表格: {len(headers)} 列, {len(rows)} 行")
                        return headers, rows
                    else:
                        logger.warning("解析结果为空，尝试下一种方法")
                        last_error = "解析结果为空"
                        continue
                        
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {e}, 原文本: {json_match[:200]}...")
                    last_error = f"JSON解析失败: {e}"
                    continue
                    
            except Exception as e:
                logger.error(f"尝试方法 {i+1} 失败: {e}")
                last_error = str(e)
                import traceback
                logger.error(traceback.format_exc())
                continue
        
        # 如果所有方法都失败，返回空结果
        logger.error(f"所有图像传递方法均失败，最后错误: {last_error}")
        return [], []
            
    except Exception as e:
        logger.error(f"使用大模型解析表格失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return [], []

def parse_formula_with_llm(image_path: str, api_key: str = None, max_retries: int = 3, timeout: int = 30) -> str:
    """
    使用大模型解析公式图像
    
    Args:
        image_path: 公式图像路径
        api_key: API密钥，如果为None则使用默认密钥
        max_retries: 最大重试次数
        timeout: API调用超时时间（秒）
    
    Returns:
        str: 解析后的LaTeX公式
    """
    if not os.path.exists(image_path):
        logger.error(f"图像文件不存在: {image_path}")
        return ""
    
    # 使用提供的API密钥或默认密钥
    api_key = api_key or DEFAULT_API_KEY
    
    # 尝试不同的图像格式和传递方法
    methods_to_try = [
        # 方法1: 文件路径
        lambda: {"image": f"file://{os.path.abspath(image_path)}"},
        # 方法2: base64编码
        lambda: {"image": encode_image_to_base64(image_path)},
        # 方法3: data URI格式的base64编码
        lambda: {"image": f"data:image/png;base64,{encode_image_to_base64(image_path)}"}
    ]
    
    last_error = None
    
    # 尝试各种方法
    for method_index, get_image_content in enumerate(methods_to_try):
        # 对每种方法进行多次重试
        for retry in range(max_retries):
            try:
                logger.info(f"解析公式 (方法 {method_index+1}, 尝试 {retry+1}/{max_retries})")
                
                # 准备请求消息
                messages = [
                    {
                        "role": "user",
                        "content": [
                            get_image_content(),  # 使用当前方法获取图像内容
                            {"text": "这是一张数学公式图片。请识别图中的公式，并以LaTeX格式返回。只需返回公式的LaTeX代码，不要有其他解释性文字，也不需要加上$$或其他标记。"}
                        ]
                    }
                ]
                
                # 调用模型
                response = dashscope.MultiModalConversation.call(
                    api_key=api_key,
                    model='qwen-vl-max-latest',  # 使用具备视觉能力的大模型
                    messages=messages,
                    timeout=timeout
                )
                
                # 如果成功获取响应
                if response and hasattr(response, 'output') and hasattr(response.output, 'choices'):
                    # 获取结果文本
                    result_message = response.output.choices[0].message
                    if not hasattr(result_message, 'content'):
                        logger.error("大模型返回中缺少content字段")
                        continue
                        
                    result_text = result_message.content
                    logger.info(f"大模型返回: {str(result_text)[:200]}...")
                    
                    # 检查返回结果类型并适当处理
                    if isinstance(result_text, list):
                        # 如果是列表格式，尝试从列表中提取文本
                        text_contents = []
                        for item in result_text:
                            if isinstance(item, dict) and 'text' in item:
                                text_contents.append(item['text'])
                        result_text = "\n".join(text_contents)
                    elif not isinstance(result_text, str):
                        # 如果既不是字符串也不是列表，尝试转换为字符串
                        result_text = str(result_text)
                    
                    # 清理LaTeX结果
                    latex_formula = clean_latex_result(result_text)
                    
                    if latex_formula:
                        logger.info(f"成功解析公式: {latex_formula[:50]}...")
                        return latex_formula
                    else:
                        logger.warning("解析结果为空，尝试下一种方法")
                        continue
                
                # 有响应但格式不正确
                logger.error(f"大模型返回格式错误: {response}")
                last_error = f"响应格式错误: {response}"
                
                # 如果收到明确的错误，暂停一下再重试
                if hasattr(response, 'code') and response.code:
                    time.sleep(1)  # 休息1秒再重试
                
            except Exception as e:
                logger.error(f"调用大模型时出错: {e}")
                last_error = str(e)
                import traceback
                logger.error(traceback.format_exc())
                time.sleep(1)  # 休息1秒再重试
    
    logger.error(f"所有方法均失败，最后错误: {last_error}")
    return ""


def clean_latex_result(text: str) -> str:
    """
    清理模型返回的LaTeX结果，简单处理
    """
    try:
        # 去除常见的格式标记
        text = text.strip()
        
        # 如果有markdown代码块格式，提取内部内容
        code_pattern = r"```(?:latex|math)?\s*(.*?)\s*```"
        code_matches = re.search(code_pattern, text, re.DOTALL)
        if code_matches:
            text = code_matches.group(1).strip()
        
        # 移除开头和结尾的$$ 或 $
        text = re.sub(r"^\$\$|\$\$$", "", text)
        text = re.sub(r"^\$|\$$", "", text)
        
        # 修复\Tilde为\tilde（最常见的错误）
        text = text.replace("\\Tilde", "\\tilde")
        
        return text
    except Exception as e:
        logger.error(f"清理LaTeX结果失败: {e}")
        return text

def demo_table_parsing():
    """演示表格解析功能"""
    # 示例表格图片路径
    image_path = "path/to/table_image.jpg"
    if not os.path.exists(image_path):
        logger.warning(f"示例图像不存在: {image_path}")
        return
    
    headers, rows = parse_table_with_llm(image_path)
    print(f"表头: {headers}")
    print(f"数据行: {rows[:2]}...")  # 只打印前两行
    
if __name__ == "__main__":
    # 演示表格解析
    demo_table_parsing()