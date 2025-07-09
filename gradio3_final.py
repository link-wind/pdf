#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF文档解析系统 - Gradio Web界面

提供一个简单的Web界面，用于将PDF文档转换为结构化的Markdown格式。
左侧显示PDF页面，右侧显示渲染后的Markdown。
"""

import os
import sys
import time
import tempfile
from pathlib import Path
import base64

import gradio as gr
import markdown
import fitz  # PyMuPDF
from PIL import Image
import io

from loguru import logger

# 确保可以导入项目模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src import PDFPipeline, load_config


# 配置日志记录器
def setup_logger():
    """配置日志记录器"""
    logger.remove()  # 移除默认处理器
    logger.add(sys.stderr, level="INFO")
    logger.add("logs/pdf_parser_web_{time}.log", rotation="10 MB", level="DEBUG")


# 加载配置并初始化Pipeline
def init_pipeline():
    """初始化PDF处理管道"""
    try:
        # 加载配置
        config = load_config("config.yaml")
        # 初始化处理管道
        pipeline = PDFPipeline(settings=config)
        return pipeline
    except Exception as e:
        logger.error(f"初始化处理管道失败: {e}")
        return None


# 处理PDF文件
def process_pdf(pdf_file, page_number=1):
    """处理PDF文件并返回结果"""
    if pdf_file is None:
        return None, None, "请上传PDF文件", None
    
    try:
        # 保存上传的文件到临时目录
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_path = temp_file.name
            temp_file.write(pdf_file)
        
        # 初始化Pipeline
        pipeline = init_pipeline()
        if pipeline is None:
            return None, None, "初始化处理管道失败", None
        
        # 处理PDF文件
        start_time = time.time()
        result = pipeline.process(pdf_path=temp_path)
        processing_time = time.time() - start_time
        
        # 清理临时文件
        try:
            os.unlink(temp_path)
        except:
            pass
        
        if result['success']:
            # 读取生成的Markdown文件
            with open(result['output_path'], 'r', encoding='utf-8') as f:
                markdown_text = f.read()
            
            # 将Markdown转换为HTML以便显示
            html_content = markdown.markdown(markdown_text, extensions=['tables', 'fenced_code'])
            
            # 获取PDF页面图像
            pdf_images = get_pdf_images(pdf_file)
            
            # 获取处理结果信息
            info_text = f"处理成功！\n"
            info_text += f"页数: {result['metadata'].get('pages_count', 'N/A')}\n"
            info_text += f"识别区域: {result['metadata'].get('total_regions', 'N/A')}个\n"
            info_text += f"处理时间: {processing_time:.2f}秒"
            
            return pdf_images, markdown_text, info_text, html_content
        else:
            error_msg = result.get('error', '未知错误')
            return None, None, f"处理失败: {error_msg}", None
    
    except Exception as e:
        logger.error(f"处理PDF文件时出错: {e}")
        import traceback
        traceback.print_exc()
        return None, None, f"处理出错: {str(e)}", None


# 获取PDF页面图像
def get_pdf_images(pdf_file):
    """从PDF文件中提取页面图像"""
    try:
        # 将上传的文件内容转换为字节流
        if isinstance(pdf_file, str):
            # 如果是文件路径
            with open(pdf_file, 'rb') as f:
                pdf_bytes = f.read()
        else:
            # 如果是上传的文件内容
            pdf_bytes = pdf_file
        
        # 使用PyMuPDF打开PDF
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # 提取所有页面的图像
        images = []
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            # 渲染页面为图像
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x缩放以提高清晰度
            
            # 将pixmap转换为PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # 将图像转换为base64编码的数据URL
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            images.append((page_num + 1, f"data:image/png;base64,{img_str}"))
        
        return images
    
    except Exception as e:
        logger.error(f"提取PDF页面图像时出错: {e}")
        return []


# 显示指定页面
def display_page(pdf_images, page_number):
    """显示指定页码的PDF页面"""
    if not pdf_images or page_number <= 0:
        return None
    
    # 确保页码在有效范围内
    page_number = max(1, min(page_number, len(pdf_images)))
    
    # 返回对应页码的图像
    return pdf_images[page_number - 1][1]


# 创建Gradio界面
def create_interface():
    """创建Gradio Web界面"""
    with gr.Blocks(title="PDF文档解析系统", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# PDF文档解析系统")
        gr.Markdown("上传PDF文件，将自动解析为结构化Markdown格式。左侧显示PDF页面，右侧显示渲染后的Markdown。")
        
        # 状态变量
        pdf_images_state = gr.State(None)
        current_page = gr.State(1)
        
        with gr.Row():
            # 左侧：PDF上传和显示
            with gr.Column():
                pdf_file = gr.File(label="上传PDF文件", file_types=[".pdf"])
                
                with gr.Row():
                    prev_btn = gr.Button("上一页")
                    page_num = gr.Number(value=1, label="页码", precision=0)
                    next_btn = gr.Button("下一页")
                    total_pages = gr.Textbox(label="总页数", value="0")
                
                pdf_display = gr.Image(label="PDF预览", height=600)
                info_text = gr.Textbox(label="处理信息", lines=4)
            
            # 右侧：Markdown显示
            with gr.Column():
                with gr.Tabs():
                    with gr.TabItem("Markdown源码"):
                        markdown_text = gr.Textbox(label="Markdown内容", lines=25)
                    with gr.TabItem("渲染预览"):
                        html_view = gr.HTML(label="HTML预览")
                
                download_btn = gr.Button("下载Markdown文件")
                markdown_file = gr.File(label="下载文件")
        
        # 处理PDF上传
        pdf_file.upload(
            fn=process_pdf,
            inputs=[pdf_file],
            outputs=[pdf_images_state, markdown_text, info_text, html_view]
        )
        
        # 更新页面显示
        def update_page_display(pdf_images, page):
            if pdf_images:
                return display_page(pdf_images, page), str(page), str(len(pdf_images))
            return None, "1", "0"
        
        # 监听页码变化
        page_num.change(
            fn=update_page_display,
            inputs=[pdf_images_state, page_num],
            outputs=[pdf_display, page_num, total_pages]
        )
        
        # 上一页按钮
        def prev_page(current):
            return max(1, current - 1)
        
        prev_btn.click(
            fn=prev_page,
            inputs=[page_num],
            outputs=[page_num]
        )
        
        # 下一页按钮
        def next_page(current, pdf_images):
            if pdf_images:
                return min(len(pdf_images), current + 1)
            return current
        
        next_btn.click(
            fn=next_page,
            inputs=[page_num, pdf_images_state],
            outputs=[page_num]
        )
        
        # 下载Markdown文件
        def create_markdown_file(markdown_content):
            if markdown_content:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as temp_file:
                    temp_file.write(markdown_content.encode('utf-8'))
                    return temp_file.name
            return None
        
        download_btn.click(
            fn=create_markdown_file,
            inputs=[markdown_text],
            outputs=[markdown_file]
        )
        
        # PDF上传后自动更新页面显示
        pdf_file.upload(
            fn=lambda images: update_page_display(images, 1),
            inputs=[pdf_images_state],
            outputs=[pdf_display, page_num, total_pages]
        )
    
    return demo


# 主函数
def main():
    """主函数"""
    # 配置日志
    setup_logger()
    
    # 创建Gradio界面
    demo = create_interface()
    
    # 启动服务
    demo.launch(server_name="0.0.0.0", share=True)


if __name__ == "__main__":
    main()
