import os
import dashscope
from loguru import logger

# 检查dashscope库安装和API密钥配置
def test_dashscope_config():
    """测试dashscope配置是否正确"""
    try:
        # 检查API密钥
        api_key = os.environ.get("DASHSCOPE_API_KEY", "sk-576e3801be4b445eb944b3dd79fa6f9c")
        if not api_key:
            logger.error("未设置DASHSCOPE_API_KEY环境变量")
            return False
            
        logger.info(f"使用API密钥: {api_key[:8]}...")
        
        # 获取dashscope版本
        dashscope_version = getattr(dashscope, "__version__", "未知")
        logger.info(f"dashscope版本: {dashscope_version}")
        
        # 测试简单调用 - 仅发送文本请求
        logger.info("测试文本模型调用...")
        response = dashscope.Generation.call(
            model="qwen-max",
            api_key=api_key,
            prompt="你好，测试一下API连接"
        )
        
        logger.info(f"模型响应状态码: {getattr(response, 'status_code', 'N/A')}")
        logger.info(f"响应内容: {getattr(response, 'output', {}).get('text', '')[:100]}...")
        
        return True
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("开始测试dashscope配置...")
    success = test_dashscope_config()
    if success:
        logger.info("配置测试成功")
    else:
        logger.error("配置测试失败") 