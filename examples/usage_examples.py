"""
PDF Pipeline 使用示例
"""

from pathlib import Path
import sys

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src import PDFPipeline


def example_basic_usage():
    """基本使用示例"""
    print("=== 基本使用示例 ===")
    
    # 初始化Pipeline
    pipeline = PDFPipeline()
    
    # 模拟处理（需要实际的PDF文件）
    # result = pipeline.process("sample.pdf", "output.md", "general")
    # print(f"处理完成，耗时: {result.processing_time:.2f}秒")
    
    print("Pipeline初始化成功")


def example_with_config():
    """使用配置文件的示例"""
    print("=== 使用配置文件示例 ===")
    
    # 使用自定义配置
    config_path = Path(__file__).parent.parent / "config.yaml"
    pipeline = PDFPipeline(str(config_path))
    
    print(f"使用配置文件: {config_path}")
    print(f"OCR引擎: {pipeline.settings.ocr_processor.engine}")
    print(f"表格解析方法: {pipeline.settings.table_parser.method}")


def example_different_document_types():
    """不同文档类型的处理示例"""
    print("=== 不同文档类型处理示例 ===")
    
    pipeline = PDFPipeline()
    
    document_types = ["scientific", "dev_doc", "general"]
    
    for doc_type in document_types:
        print(f"文档类型: {doc_type}")
        # 这里会根据文档类型使用不同的处理策略
        # result = pipeline.process("sample.pdf", f"output_{doc_type}.md", doc_type)
        print(f"  - 针对{doc_type}文档的特殊处理逻辑")


def example_api_usage():
    """API使用示例"""
    print("=== API使用示例 ===")
    
    # 导入API函数
    from main import api_process
    
    try:
        # 使用API函数
        # result = api_process(
        #     pdf_path="sample.pdf",
        #     output_path="api_output.md",
        #     doc_type="scientific"
        # )
        # print(f"API处理完成: {result.processing_time:.2f}秒")
        print("API函数导入成功")
    except Exception as e:
        print(f"API调用示例: {e}")


def example_batch_processing():
    """批量处理示例"""
    print("=== 批量处理示例 ===")
    
    pipeline = PDFPipeline()
    
    # 模拟批量处理多个PDF文件
    pdf_files = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
    
    for pdf_file in pdf_files:
        print(f"处理文件: {pdf_file}")
        # result = pipeline.process(pdf_file, f"{pdf_file}.md")
        # print(f"  完成，耗时: {result.processing_time:.2f}秒")


def main():
    """运行所有示例"""
    print("PDF Pipeline 使用示例")
    print("=" * 60)
    
    try:
        example_basic_usage()
        print()
        
        example_with_config()
        print()
        
        example_different_document_types()
        print()
        
        example_api_usage()
        print()
        
        example_batch_processing()
        print()
        
        print("所有示例运行完成！")
        print()
        print("注意：实际使用时需要提供真实的PDF文件")
        
    except Exception as e:
        print(f"示例运行错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
