# Copyright (c) Opendatalab. All rights reserved.
from loguru import logger
from openai import OpenAI
import json

try:
    import json_repair
    HAS_JSON_REPAIR = True
except ImportError:
    HAS_JSON_REPAIR = False
    logger.warning("json_repair模块未安装，将使用标准json解析")


def llm_aided_title(page_info_list, llm_config):
    """LLM辅助标题优化函数
    
    Args:
        page_info_list: 页面信息列表，包含regions结构
        llm_config: LLM配置信息（字典格式）
        
    Returns:
        dict: 优化后的结果，包含pages和regions信息
    """
    # 验证配置
    if not llm_config:
        logger.error("LLM配置为空")
        return None
        
    api_key = llm_config.get("api_key")
    if not api_key:
        logger.error("LLM API密钥未配置")
        return None
        
    base_url = llm_config.get("base_url", "https://api.deepseek.com")
    model = llm_config.get("model", "deepseek-chat")
    temperature = llm_config.get("temperature", 0.7)
    max_retries = llm_config.get("max_retries", 3)
    timeout = llm_config.get("timeout", 30)
    provider = llm_config.get("provider", "deepseek")
    
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout
        )
    except Exception as e:
        logger.error(f"创建OpenAI客户端失败: {e}")
        return None
    title_dict = {}
    region_mapping = {}  # 用于映射region_id到region对象
    i = 0
    
    for page_info in page_info_list:
        regions = page_info.get("regions", [])
        for region in regions:
            if region.get("region_type") == "title":
                region_mapping[i] = {
                    'region_id': region.get('region_id'),
                    'page_id': page_info.get('page_id', 0)
                }
                
                title_text = region.get('text', '')
                try:
                    line_avg_height = float(region.get('avg_line_height', 12))
                except (ValueError, TypeError):
                    line_avg_height = 12.0
                page_id = page_info.get('page_id', 0)
                try:
                    page_num = int(page_id) + 1
                except (ValueError, TypeError):
                    # 如果page_id不是数字，使用默认值
                    page_num = 1
                
                title_dict[f"{i}"] = [title_text, line_avg_height, page_num]
                i += 1
    # logger.info(f"Title list: {title_dict}")

    title_optimize_prompt = f"""输入的内容是一篇文档中所有标题组成的字典，请根据以下指南优化标题的结果，使结果符合正常文档的层次结构：

1. 字典中每个value均为一个list，包含以下元素：
    - 标题文本
    - 文本行高是标题所在块的平均行高
    - 标题所在的页码

2. 保留原始内容：
    - 输入的字典中所有元素都是有效的，不能删除字典中的任何元素
    - 请务必保证输出的字典中元素的数量和输入的数量一致

3. 保持字典内key-value的对应关系不变

4. 优化层次结构：
    - 为每个标题元素添加适当的层次结构
    - 行高较大的标题一般是更高级别的标题
    - 标题从前至后的层级必须是连续的，不能跳过层级
    - 标题层级最多为4级，不要添加过多的层级
    - 优化后的标题只保留代表该标题的层级的整数，不要保留其他信息

5. 合理性检查与微调：
    - 在完成初步分级后，仔细检查分级结果的合理性
    - 根据上下文关系和逻辑顺序，对不合理的分级进行微调
    - 确保最终的分级结果符合文档的实际结构和逻辑
    - 字典中可能包含被误当成标题的正文，你可以通过将其层级标记为 0 来排除它们

IMPORTANT: 
请直接返回优化过的由标题层级组成的字典，格式为{{标题id:标题层级}}，如下：
{{
  0:1,
  1:2,
  2:2,
  3:3
}}
不需要对字典格式化，不需要返回任何其他信息。

Input title list:
{title_dict}

Corrected title list:
"""

    retry_count = 0
    dict_completion = None

    while retry_count < max_retries:
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {'role': 'user', 'content': title_optimize_prompt}],
                temperature=temperature,
                stream=True,
            )
            content_pieces = []
            for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    content_pieces.append(chunk.choices[0].delta.content)
            content = "".join(content_pieces).strip()
            # logger.info(f"Title completion: {content}")
            if "</think>" in content:
                idx = content.index("</think>") + len("</think>")
                content = content[idx:].strip()
            
            # 尝试解析JSON
            if HAS_JSON_REPAIR:
                dict_completion = json_repair.loads(content)
            else:
                dict_completion = json.loads(content)
            
            dict_completion = {int(k): int(v) for k, v in dict_completion.items()}

            # logger.info(f"len(dict_completion): {len(dict_completion)}, len(title_dict): {len(title_dict)}")
            if len(dict_completion) == len(title_dict):
                # 构建返回结果
                result = {'pages': []}
                page_results = {}
                
                for i, level in dict_completion.items():
                    if i in region_mapping:
                        region_info = region_mapping[i]
                        page_id = region_info['page_id']
                        region_id = region_info['region_id']
                        
                        if page_id not in page_results:
                            page_results[page_id] = {'page_id': page_id, 'regions': []}
                        
                        page_results[page_id]['regions'].append({
                            'region_id': region_id,
                            'level': level
                        })
                
                # 转换为列表格式
                result['pages'] = list(page_results.values())
                return result
            else:
                logger.warning(
                    "The number of titles in the optimized result is not equal to the number of titles in the input.")
                retry_count += 1
        except Exception as e:
            logger.exception(e)
            retry_count += 1

    if dict_completion is None:
        logger.error("Failed to decode dict after maximum retries.")
        return None
