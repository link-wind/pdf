#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兼容Gradio 3.x的PDF Pipeline前端界面
"""

import os
import sys
import tempfile
import traceback
from pathlib import Path
from typing import List, Tuple
from datetime import datetime

import gradio as gr

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.settings import Settings
from src.pipeline.pdf_pipeline import PDFPipeline


def init_app():
    """初始化应用数据"""
    try:
        settings = Settings()
        available_scenes = settings.get_available_scenes()
        current_scene = settings.layout_analyzer.scene_type
        
        # 初始化pipeline
        pipeline = PDFPipeline(settings)
        
        print(f"✅ 应用初始化成功")
        print(f"🎯 当前场景: {current_scene}")
        print(f"🔧 可用场景: {', '.join(available_scenes.keys())}")
        
        return settings, available_scenes, current_scene, pipeline
        
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        print(f"详细错误: {traceback.format_exc()}")
        # 返回默认值
        return None, {
            'paper': {'description': '论文场景'},
            'report': {'description': '报告场景'},
            'general': {'description': '通用场景'}
        }, 'general', None


# 全局变量
SETTINGS, AVAILABLE_SCENES, CURRENT_SCENE, PIPELINE = init_app()


def download_markdown_content(markdown_content: str) -> str:
    """生成Markdown文件供下载"""
    if not markdown_content:
        return None
    
    # 创建临时文件
    temp_dir = tempfile.mkdtemp()
    filename = f"pdf_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    filepath = os.path.join(temp_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    return filepath


def get_system_status() -> str:
    """获取系统状态信息"""
    status_info = f"""## 🔧 系统状态

**当前时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**当前场景**: {CURRENT_SCENE}
**Pipeline状态**: {'✅ 已加载' if PIPELINE else '❌ 未加载'}
**Settings状态**: {'✅ 已加载' if SETTINGS else '❌ 未加载'}

**可用场景**:
"""
    
    for scene_name, scene_info in AVAILABLE_SCENES.items():
        status_info += f"- **{scene_name}**: {scene_info.get('description', '')}\n"
    
    return status_info


def get_scene_info(scene_name: str) -> str:
    """获取场景信息"""
    if scene_name not in AVAILABLE_SCENES:
        return "未知场景"
        
    scene_info = AVAILABLE_SCENES[scene_name]
    categories = scene_info.get('categories', {})
    
    info_lines = [
        f"场景: {scene_info.get('description', scene_name)}",
        f"发布日期: {scene_info.get('release_date', '未知')}",
        f"权重文件: {scene_info.get('weight_file', '未知')}",
        f"支持类别数: {len(categories)}",
        "",
        "支持的内容类型:"
    ]
    
    for category in categories.values():
        info_lines.append(f"- {category}")
        
    return "\n".join(info_lines)


def switch_scene(scene_name: str) -> str:
    """切换场景"""
    global CURRENT_SCENE, PIPELINE
    
    try:
        print(f"🔄 开始切换场景: {CURRENT_SCENE} → {scene_name}")
        
        if scene_name not in AVAILABLE_SCENES:
            error_msg = f"❌ 场景 '{scene_name}' 不存在，可用场景: {list(AVAILABLE_SCENES.keys())}"
            print(error_msg)
            return error_msg
            
        if scene_name == CURRENT_SCENE:
            success_msg = f"✅ 已经是 {scene_name} 场景，无需切换"
            print(success_msg)
            return success_msg
            
        if SETTINGS:
            print(f"🔧 调用Settings.set_layout_scene({scene_name})")
            try:
                SETTINGS.set_layout_scene(scene_name)
                print(f"🔧 Settings切换成功")
                
                old_scene = CURRENT_SCENE
                CURRENT_SCENE = scene_name
                print(f"✅ 全局变量已更新: {old_scene} → {CURRENT_SCENE}")
                
                # 重新初始化pipeline以应用新场景
                try:
                    print("🔄 重新初始化Pipeline...")
                    old_pipeline = PIPELINE
                    PIPELINE = PDFPipeline(SETTINGS)
                    print("✅ Pipeline重新初始化成功")
                    
                    # 验证新场景设置
                    current_model = SETTINGS.layout_analyzer.model_path
                    expected_weight = AVAILABLE_SCENES[scene_name].get('weight_file', '')
                    print(f"🎯 当前模型路径: {current_model}")
                    print(f"🎯 期望权重文件: {expected_weight}")
                    
                    if expected_weight in current_model:
                        print("✅ 模型权重验证通过")
                    else:
                        print("⚠️ 模型权重可能不匹配")
                    
                    return f"✅ 已切换到 {scene_name} 场景（{AVAILABLE_SCENES[scene_name].get('description', '')}）"
                    
                except Exception as e:
                    error_msg = f"⚠️ 已切换到 {scene_name} 场景，但Pipeline初始化失败: {str(e)}"
                    print(error_msg)
                    # 即使Pipeline失败，场景也已经切换了
                    return error_msg
                    
            except Exception as e:
                error_msg = f"❌ Settings切换到 {scene_name} 场景失败: {str(e)}"
                print(error_msg)
                return error_msg
        else:
            # 模拟模式
            old_scene = CURRENT_SCENE
            CURRENT_SCENE = scene_name
            success_msg = f"✅ 已切换到 {scene_name} 场景（模拟模式）"
            print(success_msg)
            return success_msg
            
    except Exception as e:
        error_msg = f"❌ 切换场景时出错: {str(e)}"
        print(error_msg)
        print(f"详细错误: {traceback.format_exc()}")
        return error_msg


def validate_pdf_file(pdf_file) -> Tuple[bool, str]:
    """验证PDF文件是否有效（宽松模式）"""
    try:
        if pdf_file is None:
            return False, "未上传PDF文件"
        
        # 检查文件名（更宽松的检查）
        filename = ""
        if hasattr(pdf_file, 'name'):
            filename = pdf_file.name
        elif hasattr(pdf_file, 'orig_name'):  # Gradio可能使用这个属性
            filename = pdf_file.orig_name
        
        if filename and not filename.lower().endswith('.pdf'):
            return False, f"文件扩展名不是PDF格式: {filename}"
        
        # 检查文件大小（更宽松的限制）
        file_size = 0
        try:
            if hasattr(pdf_file, 'size'):
                file_size = pdf_file.size
            elif hasattr(pdf_file, 'name') and os.path.exists(pdf_file.name):
                file_size = os.path.getsize(pdf_file.name)
        except:
            pass  # 忽略大小检查错误
        
        if file_size > 0 and file_size > 200 * 1024 * 1024:  # 200MB限制
            return False, f"PDF文件太大 ({file_size / 1024 / 1024:.1f}MB)，建议小于200MB"
        
        # 更宽松的PDF文件头检查
        try:
            header_data = None
            
            # 尝试多种方式读取文件头
            if hasattr(pdf_file, 'read'):
                try:
                    # 保存当前位置
                    current_pos = pdf_file.tell() if hasattr(pdf_file, 'tell') else 0
                    # 读取更长的文件头以容错
                    header_data = pdf_file.read(50)
                    # 恢复位置
                    if hasattr(pdf_file, 'seek'):
                        pdf_file.seek(current_pos)
                except:
                    pass
            
            # 如果上面的方法失败，尝试通过文件路径读取
            if header_data is None and hasattr(pdf_file, 'name') and pdf_file.name:
                try:
                    with open(pdf_file.name, 'rb') as f:
                        header_data = f.read(50)
                except:
                    pass
            
            # 检查PDF文件头（更宽松的检查）
            if header_data is not None:
                # 检查是否包含PDF标识
                if b'%PDF-' not in header_data[:20]:
                    print(f"⚠️ 文件头检查失败，但继续处理: {header_data[:20]}")
                    # 不返回错误，允许继续处理
                else:
                    print(f"✅ PDF文件头验证通过: {header_data[:10]}")
            else:
                print("⚠️ 无法读取文件头，跳过验证")
                
        except Exception as e:
            print(f"⚠️ PDF文件头检查出错，但继续处理: {str(e)}")
            # 不返回错误，允许继续处理
        
        return True, "PDF文件验证通过（宽松模式）"
        
    except Exception as e:
        print(f"⚠️ PDF验证过程出错: {str(e)}")
        # 在宽松模式下，即使验证出错也允许继续处理
        return True, f"PDF文件验证跳过（出错但继续）: {str(e)}"


def safe_read_pdf_data(pdf_file):
    """安全地读取PDF文件数据（多种方式尝试）"""
    try:
        print(f"📖 开始读取PDF数据...")
        print(f"📖 文件对象类型: {type(pdf_file)}")
        
        # 方法1: 直接读取file-like对象
        if hasattr(pdf_file, 'read'):
            try:
                print("📖 尝试方法1: 直接读取file对象...")
                # 先检查当前位置
                current_pos = 0
                if hasattr(pdf_file, 'tell'):
                    try:
                        current_pos = pdf_file.tell()
                        print(f"📖 当前文件位置: {current_pos}")
                    except:
                        pass
                
                # 回到文件开头
                if hasattr(pdf_file, 'seek'):
                    try:
                        pdf_file.seek(0)
                        print("📖 已重置文件指针到开头")
                    except Exception as e:
                        print(f"⚠️ 重置文件指针失败: {e}")
                
                data = pdf_file.read()
                if data and len(data) > 50:  # 降低最小大小要求
                    print(f"✅ 方法1成功，数据大小: {len(data)} bytes")
                    # 检查PDF头部
                    if isinstance(data, bytes) and data.startswith(b'%PDF-'):
                        print("✅ 检测到有效的PDF文件头")
                    else:
                        print(f"⚠️ 数据头部: {data[:20] if data else 'None'}")
                    return data
                else:
                    print(f"⚠️ 方法1数据太小: {len(data) if data else 0} bytes")
            except Exception as e:
                print(f"❌ 方法1失败: {e}")
        
        # 方法2: 通过临时文件路径读取
        temp_path = None
        if hasattr(pdf_file, 'name') and pdf_file.name:
            temp_path = pdf_file.name
        elif hasattr(pdf_file, 'file') and hasattr(pdf_file.file, 'name'):
            temp_path = pdf_file.file.name
        
        if temp_path:
            try:
                print(f"📖 尝试方法2: 读取临时文件 {temp_path}...")
                if os.path.exists(temp_path):
                    file_size = os.path.getsize(temp_path)
                    print(f"📖 文件大小: {file_size} bytes")
                    
                    if file_size > 50:  # 降低最小大小要求
                        with open(temp_path, 'rb') as f:
                            data = f.read()
                        print(f"✅ 方法2成功，数据大小: {len(data)} bytes")
                        # 检查PDF头部
                        if data.startswith(b'%PDF-'):
                            print("✅ 检测到有效的PDF文件头")
                        else:
                            print(f"⚠️ 数据头部: {data[:20]}")
                        return data
                    else:
                        print(f"⚠️ 文件太小: {file_size} bytes")
                else:
                    print(f"❌ 文件不存在: {temp_path}")
            except Exception as e:
                print(f"❌ 方法2失败: {e}")
        
        # 方法3: 尝试Gradio特有的属性
        for attr in ['file', '_file', 'data', 'content', 'orig_file']:
            if hasattr(pdf_file, attr):
                try:
                    print(f"📖 尝试方法3: 读取属性 {attr}...")
                    obj = getattr(pdf_file, attr)
                    
                    if hasattr(obj, 'read'):
                        if hasattr(obj, 'seek'):
                            try:
                                obj.seek(0)
                            except:
                                pass
                        data = obj.read()
                        if data and len(data) > 50:
                            print(f"✅ 方法3成功（{attr}.read()），数据大小: {len(data)} bytes")
                            return data
                    elif isinstance(obj, bytes) and len(obj) > 50:
                        print(f"✅ 方法3成功（{attr}直接数据），数据大小: {len(obj)} bytes")
                        return obj
                    elif hasattr(obj, 'name') and obj.name and os.path.exists(obj.name):
                        print(f"📖 方法3: 通过{attr}.name读取文件 {obj.name}")
                        with open(obj.name, 'rb') as f:
                            data = f.read()
                        if data and len(data) > 50:
                            print(f"✅ 方法3成功（{attr}.name），数据大小: {len(data)} bytes")
                            return data
                except Exception as e:
                    print(f"❌ 方法3（{attr}）失败: {e}")
        
        # 方法4: 检查是否是字节数据
        if isinstance(pdf_file, bytes) and len(pdf_file) > 50:
            print(f"✅ 方法4成功: 直接字节数据，大小: {len(pdf_file)} bytes")
            return pdf_file
        
        print(f"❌ 所有读取方法都失败了")
        print(f"文件对象类型: {type(pdf_file)}")
        available_attrs = [attr for attr in dir(pdf_file) if not attr.startswith('__')][:10]
        print(f"可用属性（前10个）: {available_attrs}")
        
        return None
        
    except Exception as e:
        print(f"❌ PDF数据读取过程出现异常: {e}")
        return None


def process_pdf(
    pdf_file,
    scene_name: str,
    enable_ocr: bool,
    enable_table: bool,
    enable_formula: bool
) -> Tuple[str, str]:
    """处理PDF文件"""
    
    if pdf_file is None:
        return "❌ 请上传PDF文件", ""
    
    # 验证PDF文件
    print(f"🔍 开始验证PDF文件...")
    is_valid, validation_message = validate_pdf_file(pdf_file)
    print(f"📋 验证结果: {validation_message}")
    
    if not is_valid:
        return f"❌ {validation_message}", ""
        
    try:
        # 切换场景
        if scene_name != CURRENT_SCENE:
            switch_result = switch_scene(scene_name)
            if "❌" in switch_result:
                return switch_result, ""
        
        # 检查是否有可用的pipeline
        if PIPELINE is None:
            # 使用模拟处理
            return process_pdf_simulation(pdf_file, scene_name, enable_ocr, enable_table, enable_formula)
        
        # 真实PDF处理
        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix="pdf_pipeline_gradio_")
            
            # 保存上传的PDF文件
            input_path = os.path.join(temp_dir, f"input_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
            
            # 安全地读取PDF文件数据
            pdf_data = safe_read_pdf_data(pdf_file)
            if pdf_data is None or len(pdf_data) < 100:
                print(f"❌ PDF数据读取失败，回退到模拟模式")
                return process_pdf_simulation(pdf_file, scene_name, enable_ocr, enable_table, enable_formula)
            
            # 写入文件
            with open(input_path, 'wb') as f:
                f.write(pdf_data)
            
            # 验证保存的文件
            if not os.path.exists(input_path) or os.path.getsize(input_path) < 100:
                print(f"❌ PDF文件保存验证失败，回退到模拟模式")
                return process_pdf_simulation(pdf_file, scene_name, enable_ocr, enable_table, enable_formula)
            
            # 设置输出目录
            output_dir = os.path.join(temp_dir, "output")
            os.makedirs(output_dir, exist_ok=True)
            
            # 临时更新处理选项
            original_config = {}
            config_updates = {
                'ocr_processor.enabled': enable_ocr,
                'table_parser.enabled': enable_table,
                'formula_parser.enabled': enable_formula
            }
            
            # 保存原始配置
            for key, value in config_updates.items():
                parts = key.split('.')
                try:
                    config_obj = SETTINGS
                    for part in parts[:-1]:
                        config_obj = getattr(config_obj, part)
                    original_config[key] = getattr(config_obj, parts[-1], None)
                    setattr(config_obj, parts[-1], value)
                except:
                    pass
            
            try:
                # 执行PDF处理
                print(f"🔄 开始处理PDF: {pdf_file.name} (大小: {len(pdf_data) / 1024:.1f}KB)")
                result = PIPELINE.process(input_path, output_dir)
                
                if result.get('success', False):
                    # 读取生成的Markdown内容
                    markdown_content = result.get('markdown_content', '')
                    
                    if not markdown_content:
                        # 尝试从文件读取
                        markdown_files = list(Path(output_dir).glob("*.md"))
                        if markdown_files:
                            with open(markdown_files[0], 'r', encoding='utf-8') as f:
                                markdown_content = f.read()
                    
                    # 生成统计信息
                    stats = result.get('statistics', {})
                    processing_time = stats.get('processing_time', 0)
                    total_pages = stats.get('total_pages', 0)
                    total_regions = stats.get('total_regions', 0)
                    
                    # 添加处理信息到Markdown内容
                    if markdown_content:
                        # 在开头添加处理信息
                        header_info = f"""# PDF解析结果

## 📄 文件信息
- **文件名**: {pdf_file.name}
- **文件大小**: {round(os.path.getsize(input_path) / 1024 / 1024, 2)} MB
- **处理场景**: {scene_name}
- **处理时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## ⚙️ 处理配置
- OCR识别: {'✅ 启用' if enable_ocr else '❌ 禁用'}
- 表格解析: {'✅ 启用' if enable_table else '❌ 禁用'}
- 公式识别: {'✅ 启用' if enable_formula else '❌ 禁用'}

## 📈 处理统计
- **总页数**: {total_pages} 页
- **检测区域**: {total_regions} 个
- **处理时长**: {processing_time:.2f}秒
- **当前场景**: {scene_name}

---

"""
                        markdown_content = header_info + markdown_content
                    else:
                        markdown_content = f"""# PDF解析结果

## 📄 处理完成
- **文件名**: {pdf_file.name}
- **处理场景**: {scene_name}
- **总页数**: {total_pages} 页
- **检测区域**: {total_regions} 个
- **处理时长**: {processing_time:.2f}秒

解析成功，但未生成详细内容。请检查PDF文件或尝试其他场景。
"""
                    
                    status_message = f"✅ 真实处理完成！场景: {scene_name}, 用时: {processing_time:.2f}秒"
                    
                    # 清理临时文件
                    try:
                        import shutil
                        shutil.rmtree(temp_dir)
                    except:
                        pass
                    
                    return status_message, markdown_content
                    
                else:
                    error_info = result.get('error', '未知错误')
                    return f"❌ 处理失败: {error_info}", ""
                    
            finally:
                # 恢复原始配置
                for key, value in original_config.items():
                    if value is not None:
                        parts = key.split('.')
                        try:
                            config_obj = SETTINGS
                            for part in parts[:-1]:
                                config_obj = getattr(config_obj, part)
                            setattr(config_obj, parts[-1], value)
                        except:
                            pass
                
        except Exception as e:
            print(f"❌ 真实处理出错: {e}")
            # 回退到模拟处理
            return process_pdf_simulation(pdf_file, scene_name, enable_ocr, enable_table, enable_formula)
        
    except Exception as e:
        error_msg = f"❌ 处理失败: {str(e)}"
        return error_msg, ""


def process_pdf_with_render(
    pdf_file,
    scene_name: str,
    enable_ocr: bool,
    enable_table: bool,
    enable_formula: bool
) -> Tuple[str, str, str]:
    """处理PDF文件并返回源码和渲染结果"""
    
    # 调用原始处理函数
    status, markdown_content = process_pdf(
        pdf_file, scene_name, enable_ocr, enable_table, enable_formula
    )
    
    # 返回状态、源码和渲染内容（渲染内容与源码相同，Gradio会自动渲染）
    return status, markdown_content, markdown_content


def quick_system_test() -> str:
    """快速系统测试"""
    try:
        test_results = []
        
        # 测试配置加载
        if SETTINGS:
            test_results.append("✅ 配置系统正常")
        else:
            test_results.append("❌ 配置系统异常")
        
        # 测试Pipeline
        if PIPELINE:
            test_results.append("✅ Pipeline已加载")
            # 测试processor状态
            status = PIPELINE.get_processor_status()
            loaded_processors = [name for name, loaded in status.items() if loaded]
            test_results.append(f"✅ 已加载处理器: {', '.join(loaded_processors)}")
        else:
            test_results.append("❌ Pipeline未加载")
        
        # 测试场景
        test_results.append(f"✅ 当前场景: {CURRENT_SCENE}")
        test_results.append(f"✅ 可用场景: {len(AVAILABLE_SCENES)} 个")
        
        # 测试权重文件
        if SETTINGS:
            model_path = SETTINGS.layout_analyzer.model_path
            if os.path.exists(model_path):
                test_results.append(f"✅ 模型权重文件存在: {os.path.basename(model_path)}")
            else:
                test_results.append(f"❌ 模型权重文件不存在: {model_path}")
        
        return "\n".join(test_results)
        
    except Exception as e:
        return f"❌ 测试过程出错: {str(e)}"


def process_pdf_simulation(
    pdf_file,
    scene_name: str,
    enable_ocr: bool,
    enable_table: bool,
    enable_formula: bool
) -> Tuple[str, str]:
    """模拟PDF处理（备用方案）"""
    
    # 模拟处理
    import time
    time.sleep(2)  # 模拟处理时间
    
    # 构建Markdown结果 - 分段构建避免f-string反斜杠问题
    file_info = f"# PDF解析结果（模拟模式）\n\n## 📄 文件信息\n- **文件名**: {pdf_file.name}\n"
    if hasattr(pdf_file, 'size'):
        file_info += f"- **文件大小**: {round(pdf_file.size / 1024 / 1024, 2)} MB\n"
    else:
        file_info += "- **文件大小**: 未知\n"
    
    file_info += f"- **处理场景**: {scene_name}\n"
    file_info += f"- **处理时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    file_info += "- **处理模式**: 模拟模式（演示用）\n\n"
    
    config_info = "## ⚙️ 处理配置\n"
    config_info += f"- OCR识别: {'✅ 启用' if enable_ocr else '❌ 禁用'}\n"
    config_info += f"- 表格解析: {'✅ 启用' if enable_table else '❌ 禁用'}\n"
    config_info += f"- 公式识别: {'✅ 启用' if enable_formula else '❌ 禁用'}\n\n"
    
    content_info = """## 📊 内容摘要
这是一个模拟的解析结果示例。在实际应用中，系统会：

### 1. 文档结构分析
- 自动检测页面布局和区域
- 识别标题层级结构
- 分析段落和章节组织
- 提取页眉页脚信息

"""
    
    # OCR部分
    if enable_ocr:
        content_info += """### 2. 文本内容提取 (启用)

经过OCR识别的文本内容：
- 主要段落文本内容
- 各级标题和小标题
- 图片中的文字信息
- 表格中的文本数据

"""
    else:
        content_info += "### 2. 文本内容提取 (已禁用)\n文本识别功能已禁用\n\n"
    
    # 表格部分
    if enable_table:
        content_info += """### 3. 表格数据解析 (启用)

| 列名1 | 列名2 | 列名3 |
|-------|-------|-------|
| 数据1 | 数据2 | 数据3 |
| 数据4 | 数据5 | 数据6 |
| 数据7 | 数据8 | 数据9 |

表格说明：系统会自动识别表格结构并转换为Markdown格式

"""
    else:
        content_info += "### 3. 表格数据解析 (已禁用)\n表格解析功能已禁用\n\n"
    
    # 公式部分
    if enable_formula:
        content_info += """### 4. 数学公式识别 (启用)

识别的数学公式示例：

$$E = mc^2$$

$$\\int_0^\\infty e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}$$

$$\\sum_{i=1}^n i = \\frac{n(n+1)}{2}$$

"""
    else:
        content_info += "### 4. 数学公式识别 (已禁用)\n公式识别功能已禁用\n\n"
    
    stats_info = f"""## 📈 处理统计
- **总页数**: 模拟 5 页
- **检测区域**: 模拟 25 个区域
- **文本区域**: 15 个
- **图片区域**: 4 个
- **表格区域**: 3 个
- **公式区域**: 3 个
- **处理时长**: 2秒（模拟）
- **平均置信度**: 87.5%

## 🎯 场景信息
当前使用的 **{scene_name}** 场景针对此类文档进行了优化，能够：
- 准确识别文档结构
- 保持原有格式
- 提取关键信息
- 生成标准化输出

## ⚠️ 提示
当前为模拟模式，用于演示界面功能。要进行真实的PDF处理，请确保：
1. 所有依赖库已正确安装
2. 模型权重文件已下载
3. GPU驱动已配置（如果使用GPU）

---
*本结果由PDF Pipeline系统生成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    # 合并所有部分
    markdown_result = file_info + config_info + content_info + stats_info
    status_message = f"✅ 模拟处理完成！使用场景: {scene_name}"
    
    return status_message, markdown_result


def create_interface():
    """创建Gradio 3.x兼容的界面"""
    
    # 获取场景选项
    scene_choices = list(AVAILABLE_SCENES.keys())
    
    # 创建界面
    with gr.Blocks(title="PDF Pipeline 解析系统") as demo:
        
        # 标题
        gr.HTML("""
        <div style='text-align: center; padding: 20px; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px; margin-bottom: 20px;'>
            <h1>🔍 PDF Pipeline 解析系统</h1>
            <p>支持多场景版式分析的智能PDF文档解析平台</p>
            <p>当前版本: Gradio 3.x 兼容版</p>
        </div>
        """)
        
        # 主界面标签页
        with gr.Tab("📄 文档解析"):
            with gr.Row():
                # 左侧输入区域
                with gr.Column(scale=1):
                    # 文件上传
                    pdf_input = gr.File(
                        label="📎 上传PDF文件",
                        file_types=[".pdf"]
                    )
                    
                    # 场景选择
                    scene_dropdown = gr.Dropdown(
                        choices=scene_choices,
                        value=CURRENT_SCENE,
                        label="🎯 选择解析场景"
                    )
                    
                    # 场景信息显示
                    scene_info_display = gr.Textbox(
                        label="场景信息",
                        value=get_scene_info(CURRENT_SCENE),
                        lines=8,
                        interactive=False
                    )
                    
                    # 处理选项
                    gr.Markdown("### ⚙️ 处理选项")
                    enable_ocr = gr.Checkbox(label="启用OCR文字识别", value=True)
                    enable_table = gr.Checkbox(label="启用表格解析", value=True)
                    enable_formula = gr.Checkbox(label="启用公式识别", value=True)
                    
                    # 处理按钮
                    process_btn = gr.Button("🚀 开始解析", variant="primary")
                    
                    # 文件信息按钮
                    pdf_info_btn = gr.Button("🔍 查看文件信息", variant="secondary", size="sm")
                
                # 右侧输出区域
                with gr.Column(scale=2):
                    # 状态输出
                    status_output = gr.Textbox(
                        label="📊 处理状态",
                        lines=2,
                        interactive=False
                    )
                    
                    # 输出结果标签页
                    with gr.Tab("📝 Markdown源码"):
                        markdown_output = gr.Textbox(
                            label="解析结果（Markdown格式）",
                            lines=25,
                            max_lines=30,
                            interactive=False
                        )
                        
                        # 下载按钮区域
                        with gr.Row():
                            download_markdown_btn = gr.Button("💾 下载Markdown文件", size="sm")
                            copy_markdown_btn = gr.Button("📋 复制结果", size="sm")
                    
                    # 渲染的Markdown显示
                    with gr.Tab("🎨 渲染预览"):
                        markdown_rendered = gr.Markdown(
                            label="渲染后的文档内容",
                            value="等待处理结果..."
                        )
                    
                    # PDF文件信息显示
                    pdf_info_output = gr.Textbox(
                        label="📄 PDF文件信息",
                        lines=10,
                        interactive=False,
                        visible=False
                    )
        
        # 场景管理标签页
        with gr.Tab("🔧 场景管理"):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 📋 可用场景列表")
                    
                    # 构建场景信息文本
                    scene_list_lines = ["**可用场景:**", ""]
                    for scene_name, scene_info in AVAILABLE_SCENES.items():
                        scene_list_lines.append(f"**{scene_name}**: {scene_info.get('description', '')}")
                        scene_list_lines.append(f"  - 权重: {scene_info.get('weight_file', '未知')}")
                        scene_list_lines.append(f"  - 类别数: {len(scene_info.get('categories', {}))}")
                        scene_list_lines.append("")
                    
                    scene_list_text = "\n".join(scene_list_lines)
                    gr.Markdown(scene_list_text)
                
                with gr.Column():
                    gr.Markdown("### 🎛️ 场景切换")
                    
                    # 当前场景显示
                    current_scene_text = gr.Textbox(
                        label="当前场景",
                        value=f"{CURRENT_SCENE}",
                        interactive=False
                    )
                    
                    # 场景切换
                    scene_switch_dropdown = gr.Dropdown(
                        choices=scene_choices,
                        value=CURRENT_SCENE,
                        label="选择要切换的场景"
                    )
                    
                    switch_btn = gr.Button("切换场景", variant="secondary")
                    
                    switch_result = gr.Textbox(
                        label="切换结果",
                        lines=3,
                        interactive=False
                    )
        
        # 系统状态标签页
        with gr.Tab("📊 系统状态"):
            with gr.Row():
                with gr.Column():
                    system_status_display = gr.Markdown(
                        value=get_system_status(),
                        label="系统状态信息"
                    )
                    
                    refresh_status_btn = gr.Button("🔄 刷新状态", variant="secondary")
                
                with gr.Column():
                    gr.Markdown("""
                    ### 💡 系统说明
                    
                    **处理模式:**
                    - ✅ 真实模式: 使用完整的PDF Pipeline进行处理
                    - ⚠️ 模拟模式: 演示界面功能，返回模拟结果
                    
                    **状态指示:**
                    - Pipeline已加载: 可以进行真实PDF处理
                    - Pipeline未加载: 仅能进行模拟演示
                    
                    **场景切换:**
                    - 每次切换场景会重新加载相应的模型权重
                    - 不同场景适用于不同类型的文档
                    
                    **性能优化:**
                    - 建议在GPU环境下运行以获得最佳性能
                    - 大文档处理可能需要较长时间
                    """)
                    
                    gr.Markdown("### 🔧 快速操作")
                    
                    quick_test_btn = gr.Button("🧪 快速测试", variant="primary")
                    test_result = gr.Textbox(
                        label="测试结果",
                        lines=3,
                        interactive=False
                    )
        
        # 使用说明标签页
        with gr.Tab("📚 使用说明"):
            gr.Markdown("""
            # 📖 使用指南
            
            ## 🚀 快速开始
            1. **上传PDF文件**: 点击"上传PDF文件"按钮选择要处理的PDF
            2. **选择场景**: 根据文档类型选择适合的解析场景
            3. **配置选项**: 根据需要启用或禁用特定功能
            4. **开始解析**: 点击"开始解析"按钮处理文档
            
            ## 🎯 场景选择指南
            
            ### 📄 paper (论文场景)
            - **适用**: 中文学术论文、研究报告
            - **特色**: 针对学术论文的复杂版式优化
            - **支持**: 标题、正文、图片、表格、公式、参考文献
            
            ### 📊 report (研报场景)
            - **适用**: 研究报告、分析报告、白皮书
            - **特色**: 适合商业报告的版式分析
            - **支持**: 标题、正文、图表、目录
            
            ### 🌐 general (通用场景)
            - **适用**: 通用文档、混合类型文档
            - **特色**: 适合各种类型的文档
            - **支持**: 基本的文本、标题、图表、公式
            
            ## ⚙️ 功能说明
            
            - **OCR文字识别**: 从图片和扫描文档中提取文字
            - **表格解析**: 识别并转换表格为Markdown格式
            - **公式识别**: 识别数学公式并转换为LaTeX格式
            - **图片分析**: 提取图片并进行内容分类描述
            
            ## 💡 使用技巧
            
            1. **选择合适的场景**: 根据文档类型选择最匹配的场景
            2. **按需启用功能**: 可以禁用不需要的功能来加快处理速度
            3. **文件大小限制**: 建议单个PDF文件不超过50MB
            4. **格式支持**: 目前仅支持PDF格式文件
            
            ## 🔧 技术信息
            
            - **前端框架**: Gradio 3.x
            - **后端引擎**: PDF Pipeline
            - **支持格式**: PDF
            - **运行环境**: Python 3.9+
            
            ## 🆘 故障排除
            
            如遇到问题，请检查：
            1. PDF文件是否完整无损坏
            2. 文件大小是否在限制范围内
            3. 网络连接是否稳定
            4. 浏览器是否支持文件上传
            """)
        
        # 事件绑定
        scene_dropdown.change(
            fn=get_scene_info,
            inputs=[scene_dropdown],
            outputs=[scene_info_display]
        )
        
        process_btn.click(
            fn=process_pdf_with_render,
            inputs=[
                pdf_input,
                scene_dropdown,
                enable_ocr,
                enable_table,
                enable_formula
            ],
            outputs=[status_output, markdown_output, markdown_rendered]
        )
        
        switch_btn.click(
            fn=switch_scene,
            inputs=[scene_switch_dropdown],
            outputs=[switch_result]
        )
        
        # 更新当前场景显示
        switch_btn.click(
            fn=lambda x: x,
            inputs=[scene_switch_dropdown],
            outputs=[current_scene_text]
        )
        
        # 系统状态相关事件
        refresh_status_btn.click(
            fn=get_system_status,
            outputs=[system_status_display]
        )
        
        quick_test_btn.click(
            fn=quick_system_test,
            outputs=[test_result]
        )
        
        # PDF信息查看功能
        pdf_info_btn.click(
            fn=show_pdf_info,
            inputs=[pdf_input],
            outputs=[pdf_info_output]
        )
        
        # 显示/隐藏PDF信息
        pdf_info_btn.click(
            fn=lambda: gr.update(visible=True),
            outputs=[pdf_info_output]
        )
        
        # 下载功能（暂时禁用，Gradio 3.x不完全支持）
        # download_markdown_btn.click(
        #     fn=download_markdown_content,
        #     inputs=[markdown_output],
        #     outputs=[]
        # )
    
    return demo


def show_pdf_info(pdf_file) -> str:
    """显示PDF文件信息用于调试"""
    if pdf_file is None:
        return "❌ 未上传文件"
    
    info_lines = ["## 📄 PDF文件信息", ""]
    
    try:
        # 基本信息
        info_lines.append(f"**文件对象类型**: {type(pdf_file)}")
        
        # 文件名
        if hasattr(pdf_file, 'name'):
            info_lines.append(f"**文件名**: {pdf_file.name}")
        if hasattr(pdf_file, 'orig_name'):
            info_lines.append(f"**原始文件名**: {pdf_file.orig_name}")
            
        # 文件大小
        if hasattr(pdf_file, 'size'):
            info_lines.append(f"**文件大小**: {pdf_file.size} bytes ({pdf_file.size / 1024:.1f} KB)")
            
        # 文件路径
        if hasattr(pdf_file, 'name') and pdf_file.name and os.path.exists(pdf_file.name):
            actual_size = os.path.getsize(pdf_file.name)
            info_lines.append(f"**实际文件大小**: {actual_size} bytes ({actual_size / 1024:.1f} KB)")
            info_lines.append(f"**文件路径**: {pdf_file.name}")
            
        # 文件属性
        info_lines.append("", "**可用属性**:")
        attrs = [attr for attr in dir(pdf_file) if not attr.startswith('_')]
        info_lines.append(f"{', '.join(attrs[:10])}")  # 只显示前10个属性
        
        # 尝试读取文件头
        try:
            data = safe_read_pdf_data(pdf_file)
            if data:
                info_lines.append("", "**文件头信息**:")
                info_lines.append(f"数据长度: {len(data)} bytes")
                header = data[:50] if len(data) >= 50 else data
                info_lines.append(f"文件头(前50字节): {header}")
                
                # 检查PDF格式
                if b'%PDF-' in header:
                    info_lines.append("✅ 检测到PDF格式标识")
                else:
                    info_lines.append("⚠️ 未检测到PDF格式标识")
            else:
                info_lines.append("", "❌ 无法读取文件数据")
        except Exception as e:
            info_lines.append("", f"❌ 读取文件头失败: {str(e)}")
            
    except Exception as e:
        info_lines.append(f"❌ 获取文件信息失败: {str(e)}")
    
    return "\n".join(info_lines)


def main():
    """主函数"""
    try:
        print("🚀 启动PDF Pipeline Gradio 3.x应用...")
        
        demo = create_interface()
        
        # 启动参数
        launch_kwargs = {
            'server_name': 'localhost',
            'server_port': 7862,  # 使用不同的端口避免冲突
            'share': False,
            'debug': False,
            'inbrowser': True
        }
        
        print("📍 访问地址: http://localhost:7862")
        print("🎯 版本: Gradio 3.x 兼容版")
        print("🔧 功能: PDF解析、场景切换、结果展示")
        
        demo.launch(**launch_kwargs)
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print("💡 尝试解决方案:")
        print("1. 检查Gradio版本是否正确")
        print("2. 检查端口7860是否被占用")
        print("3. 尝试重启Python环境")
        traceback.print_exc()


if __name__ == "__main__":
    main()
