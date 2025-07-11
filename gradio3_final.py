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
        logger.info("开始处理PDF文件...")
        
        # 首先尝试提取PDF页面图像
        # 这样即使处理失败，也可以看到PDF内容
        logger.info("提取PDF页面图像...")
        pdf_images = get_pdf_images(pdf_file)
        if pdf_images:
            logger.info(f"成功提取 {len(pdf_images)} 页PDF图像")
        else:
            logger.warning("未能提取PDF页面图像")
        
        # 保存上传的文件到临时目录
        logger.info("保存PDF到临时目录...")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_path = temp_file.name
            # 获取上传文件的字节内容
            if hasattr(pdf_file, "name"):
                # gradio 3.x - 处理上传的文件对象
                file_path = pdf_file.name
                logger.info(f"从文件对象读取PDF: {file_path}")
                with open(file_path, 'rb') as f:
                    temp_file.write(f.read())
            else:
                # 直接处理字节内容
                logger.info("从字节数据保存PDF")
            temp_file.write(pdf_file)
            
            logger.info(f"PDF保存到临时文件: {temp_path}")
        
        # 初始化Pipeline
        logger.info("初始化处理管道...")
        pipeline = init_pipeline()
        if pipeline is None:
            logger.error("初始化处理管道失败")
            # 即使管道初始化失败，我们仍然可以展示PDF的图像
            if pdf_images:
                return pdf_images, None, "初始化处理管道失败，但可以查看PDF内容", None
            else:
            return None, None, "初始化处理管道失败", None
        
        # 处理PDF文件
        logger.info(f"开始处理PDF: {temp_path}")
        start_time = time.time()
        result = pipeline.process(pdf_path=temp_path)
        processing_time = time.time() - start_time
        logger.info(f"PDF处理完成，耗时: {processing_time:.2f}秒")
        
        # 记录处理结果，帮助调试
        logger.info(f"PDF处理结果: {result}")
        
        # 清理临时文件
        try:
            os.unlink(temp_path)
            logger.info(f"临时文件已删除: {temp_path}")
        except Exception as e:
            logger.warning(f"删除临时文件失败: {e}")
        
        if result['success']:
            # 检查输出路径是否存在
            output_path = result.get('output_path')
            if not output_path or not os.path.exists(output_path):
                logger.error(f"输出文件不存在: {output_path}")
                # 即使Markdown生成失败，仍然返回PDF图像
                if pdf_images:
                    return pdf_images, None, f"处理成功但输出文件不存在: {output_path}", None
                else:
                    return None, None, f"处理成功但输出文件不存在: {output_path}", None
            
            # 读取生成的Markdown文件
            try:
                with open(output_path, 'r', encoding='utf-8') as f:
                markdown_text = f.read()
                
                # 检查Markdown内容是否为空
                if not markdown_text:
                    logger.warning(f"生成的Markdown内容为空: {output_path}")
                    markdown_text = "# 处理结果\n\n*生成的内容为空，可能需要检查处理管道。*"
                
                logger.info(f"成功读取Markdown文件，长度: {len(markdown_text)} 字符")
            except Exception as e:
                logger.error(f"读取Markdown文件失败: {e}")
                # 即使Markdown读取失败，仍然返回PDF图像
                if pdf_images:
                    return pdf_images, None, f"读取输出文件失败: {str(e)}", None
                else:
                    return None, None, f"读取输出文件失败: {str(e)}", None
            
            # 将Markdown转换为HTML以便显示
            try:
            html_content = markdown.markdown(markdown_text, extensions=['tables', 'fenced_code'])
            
                # 添加MathJax支持，包装HTML内容
                html_content = f"""
                <div id="markdown-content">
                    {html_content}
                </div>
                
                <script type="text/x-mathjax-config">
                    MathJax.Hub.Config({{
                        tex2jax: {{
                            inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                            displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
                            processEscapes: true
                        }},
                        "HTML-CSS": {{ 
                            availableFonts: ["TeX"],
                            scale: 100
                        }}
                    }});
                </script>
                <script type="text/javascript" async
                    src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.7/MathJax.js?config=TeX-MML-AM_CHTML">
                </script>
                """
                logger.info("Markdown成功转换为HTML，添加了MathJax支持")
            except Exception as e:
                logger.error(f"Markdown转HTML失败: {e}")
                html_content = f"<p>Markdown渲染失败: {str(e)}</p>"
            
            # 获取处理结果信息
            info_text = f"处理成功！\n"
            
            # 检查metadata是否存在
            if 'metadata' in result:
            info_text += f"页数: {result['metadata'].get('pages_count', 'N/A')}\n"
            info_text += f"识别区域: {result['metadata'].get('total_regions', 'N/A')}个\n"
            else:
                info_text += f"页数: {len(pdf_images)}\n"
                info_text += "识别区域: N/A\n"
                
            info_text += f"处理时间: {processing_time:.2f}秒\n"
            info_text += f"Markdown内容长度: {len(markdown_text)} 字符"
            
            return pdf_images, markdown_text, info_text, html_content
        else:
            error_msg = result.get('error', '未知错误')
            logger.error(f"处理失败: {error_msg}")
            # 即使处理失败，仍然返回PDF图像
            if pdf_images:
                return pdf_images, None, f"处理失败: {error_msg}", None
            else:
            return None, None, f"处理失败: {error_msg}", None
    
    except Exception as e:
        logger.error(f"处理PDF文件时出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None, f"处理出错: {str(e)}", None


# 获取PDF页面图像
def get_pdf_images(pdf_file):
    """从PDF文件中提取页面图像"""
    try:
        # 将上传的文件内容转换为字节流
        pdf_bytes = None
        if isinstance(pdf_file, str):
            # 如果是文件路径
            logger.info(f"从文件路径读取PDF: {pdf_file}")
            with open(pdf_file, 'rb') as f:
                pdf_bytes = f.read()
        elif hasattr(pdf_file, "name"):
            # gradio 3.x - 处理上传的文件对象
            logger.info(f"从Gradio文件对象读取PDF: {pdf_file.name}")
            with open(pdf_file.name, 'rb') as f:
                pdf_bytes = f.read()
        else:
            # 如果是上传的文件内容
            logger.info("从字节数据读取PDF")
            pdf_bytes = pdf_file
        
        if not pdf_bytes:
            logger.error("未能获取PDF字节内容")
            return []

        # 使用临时文件保存PDF以确保PyMuPDF可以正确处理
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(pdf_bytes)
            temp_path = temp_file.name
        
        try:
            # 使用PyMuPDF打开PDF
            logger.info(f"使用PyMuPDF打开PDF文件: {temp_path}")
            pdf_document = fitz.open(temp_path)
            page_count = len(pdf_document)
            logger.info(f"PDF页数: {page_count}")
        
        # 提取所有页面的图像
        images = []
            for page_num in range(page_count):
                logger.info(f"处理PDF页面 {page_num+1}/{page_count}")
            page = pdf_document[page_num]
            # 渲染页面为图像
                try:
                    # 尝试更高分辨率
                    zoom_factor = 2.0  # 2x缩放以提高清晰度
                    mat = fitz.Matrix(zoom_factor, zoom_factor)
                    pix = page.get_pixmap(matrix=mat)
            
            # 将pixmap转换为PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
                    # 保存图像到本地文件，以便直接使用文件路径而非base64
                    img_path = os.path.join(tempfile.gettempdir(), f"pdf_page_{page_num+1}.png")
                    img.save(img_path)
                    logger.info(f"页面图像保存到: {img_path}")
                    
                    # 将页面信息和图像路径添加到列表
                    images.append((page_num + 1, img_path))
                    logger.info(f"页面 {page_num+1} 成功转换为图像")
                except Exception as e:
                    logger.error(f"页面 {page_num+1} 渲染失败: {e}")
                    continue
            
            # 关闭PDF文档
            pdf_document.close()
            
            # 清理临时文件
            try:
                os.unlink(temp_path)
            except:
                pass
        
        return images
        except Exception as e:
            logger.error(f"打开PDF文件失败: {e}")
            # 清理临时文件
            try:
                os.unlink(temp_path)
            except:
                pass
            return []
    
    except Exception as e:
        logger.error(f"提取PDF页面图像时出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


# 显示指定页面
def display_page(pdf_images, page_number):
    """显示指定页码的PDF页面"""
    if not pdf_images:
        logger.warning("没有PDF图像可显示")
        return None
    
    # 确保页码是整数
    if isinstance(page_number, str):
        try:
            page_number = int(page_number)
        except (ValueError, TypeError):
            logger.warning(f"无效的页码: {page_number}, 使用默认值1")
            page_number = 1
    
    # 确保页码在有效范围内
    page_number = max(1, min(page_number, len(pdf_images)))
    logger.info(f"显示PDF页面: {page_number}/{len(pdf_images)}")
    
    # 返回对应页码的图像路径
    return pdf_images[page_number - 1][1]


# 创建Gradio界面
def create_interface():
    """创建Gradio Web界面"""
    # 自定义CSS样式
    custom_css = """
#html_preview {
    padding: 15px;
    overflow-y: auto;
    height: 500px;
    max-height: 500px;
    border: 1px solid #ddd;
    border-radius: 5px;
    background-color: #fff;
    margin-bottom: 50px;  /* 添加底部间距，避免被按钮挡住 */
}
#html_preview table {
    border-collapse: collapse;
    width: 100%;
    margin: 15px 0;
}
#html_preview th, #html_preview td {
    border: 1px solid #ddd;
    padding: 8px;
    text-align: left;
}
#html_preview th {
    background-color: #f2f2f2;
}
#html_preview img {
    max-width: 100%;
}
#markdown_output {
    font-family: monospace;
}
.footer-space {
    height: 60px;  /* 为底部按钮留出空间 */
}
.container {
    display: flex;
    flex-direction: column;
    height: 100%;
}
.content-area {
    flex: 1;
    overflow-y: auto;
    padding-bottom: 20px;
}
.button-area {
    margin-top: 15px;
}
/* 数学公式样式调整 */
.MathJax {
    overflow-x: auto;
    overflow-y: hidden;
    max-width: 100%;
}
.MathJax_Display {
    overflow-x: auto;
    overflow-y: hidden;
    max-width: 100%;
    padding: 10px 0;
}
#markdown-content {
    overflow-x: hidden;
    width: 100%;
    padding-right: 10px;
}
"""
    
    with gr.Blocks(title="PDF文档解析系统", theme=gr.themes.Soft(), css=custom_css) as demo:
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
                with gr.Tabs() as tabs:
                    with gr.TabItem("Markdown源码"):
                        # 增加行数并启用自动滚动
                        markdown_text = gr.Textbox(
                            label="Markdown内容", 
                            lines=30, 
                            max_lines=50, 
                            autoscroll=True,
                            elem_id="markdown_output"
                        )
                    with gr.TabItem("渲染预览"):
                        # 创建一个容器来包装HTML预览和按钮，确保正确的布局
                        with gr.Column(elem_classes="container"):
                            with gr.Column(elem_classes="content-area"):
                                # 增加HTML渲染高度，添加可滚动容器
                                html_view = gr.HTML(label="HTML预览", elem_id="html_preview")
                            
                            # 添加一个空白区域，确保底部有足够空间
                            gr.HTML("<div class='footer-space'></div>")
                
                # 按钮放在Tabs外面，这样不会挡住内容
                with gr.Column(elem_classes="button-area"):
                    download_btn = gr.Button("下载Markdown文件", variant="primary", size="lg")
                markdown_file = gr.File(label="下载文件")
        
        # 处理PDF上传
        pdf_file.upload(
            fn=process_pdf,
            inputs=[pdf_file],
            outputs=[pdf_images_state, markdown_text, info_text, html_view]
        )
        
        # 更新页面显示
        def update_page_display(pdf_images, page_number):
            """更新页面显示的函数"""
            if not pdf_images:
                return None, 1, "0"
                
            # 确保页码是整数
            try:
                page_number = int(page_number) if page_number else 1
            except (ValueError, TypeError):
                page_number = 1
                
            # 确保页码在有效范围内
            page_number = max(1, min(page_number, len(pdf_images)))
            
            # 返回对应页码的图像、页码和总页数
            return display_page(pdf_images, page_number), page_number, str(len(pdf_images))
        
        # 监听页码变化
        page_num.change(
            fn=update_page_display,
            inputs=[pdf_images_state, page_num],
            outputs=[pdf_display, page_num, total_pages]
        )
        
        # 上一页按钮
        def prev_page(current):
            """返回上一页的页码"""
            # 确保是整数
            try:
                current = int(current) if current else 1
            except (ValueError, TypeError):
                current = 1
                
            return max(1, current - 1)
        
        prev_btn.click(
            fn=prev_page,
            inputs=[page_num],
            outputs=[page_num]
        )
        
        # 下一页按钮
        def next_page(current, pdf_images):
            """返回下一页的页码"""
            # 确保是整数
            try:
                current = int(current) if current else 1
            except (ValueError, TypeError):
                current = 1
                
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
                try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as temp_file:
                    temp_file.write(markdown_content.encode('utf-8'))
                    return temp_file.name
                except Exception as e:
                    logger.error(f"创建Markdown下载文件失败: {e}")
            return None
        
        download_btn.click(
            fn=create_markdown_file,
            inputs=[markdown_text],
            outputs=[markdown_file]
        )
        
        # PDF上传后自动更新页面显示
        def init_page_display(images):
            """初始化页面显示"""
            return update_page_display(images, 1)
        
        pdf_file.upload(
            fn=init_page_display,
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
    demo.launch(server_name="0.0.0.0", share=False)


if __name__ == "__main__":
    main()
