import os
import dashscope
import base64
from pathlib import Path
import tempfile
from typing import List, Dict, Any, Tuple, Optional
import json

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
        
        # 准备请求消息
        messages = [
            {
                "role": "user",
                "content": [
                    {"image": encode_image_to_base64(image_path)},
                    {"text": "这是一张表格图片。请识别表格内容，并以JSON格式返回。JSON格式要求：{\"headers\": [列标题数组], \"rows\": [[第一行数据], [第二行数据], ...]}。请只返回JSON格式，不要有其他描述性文字。"}
                ]
            }
        ]
        
        # 调用模型
        logger.info(f"正在调用大模型解析表格: {image_path}")
        response = dashscope.MultiModalConversation.call(
            api_key=api_key,
            model='qwen-vl-max',  # 使用具备视觉能力的大模型
            messages=messages
        )
        
        if not response or not hasattr(response, 'output') or not hasattr(response.output, 'choices'):
            logger.error(f"大模型返回格式错误: {response}")
            return [], []
        
        # 获取结果文本
        result_text = response.output.choices[0].message.content
        logger.info(f"大模型返回: {result_text[:200]}...")
        
        # 从文本中提取JSON
        # 处理可能的markdown格式，例如 ```json {...} ```
        json_match = None
        import re
        json_pattern = r'```json\s*([\s\S]*?)\s*```'
        matches = re.search(json_pattern, result_text)
        if matches:
            json_match = matches.group(1)
        else:
            # 尝试直接解析为JSON
            json_match = result_text
            
        # 尝试解析JSON
        try:
            table_data = json.loads(json_match)
            
            # 提取表头和行
            headers = table_data.get('headers', [])
            rows = table_data.get('rows', [])
            
            logger.info(f"成功解析表格: {len(headers)} 列, {len(rows)} 行")
            return headers, rows
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 原文本: {json_match[:200]}...")
            return [], []
            
    except Exception as e:
        logger.error(f"使用大模型解析表格失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return [], []

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