"""
PDF Pipeline 测试
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil
import os

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

try:
    from src import PDFPipeline
    from src.config.settings import Settings
    from src.models.document import Document, DocumentType
except ImportError as e:
    print(f"导入错误: {e}")
    print(f"当前路径: {os.getcwd()}")
    print(f"Python路径: {sys.path}")
    raise


class TestPDFPipeline(unittest.TestCase):
    """PDF Pipeline 测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_pdf = self.test_dir / "test.pdf"
        # 创建一个假的PDF文件
        self.test_pdf.write_bytes(b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<</Size 1/Root 1 0 R>>\nstartxref\n9\n%%EOF")
        
    def tearDown(self):
        """测试后清理"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_pipeline_initialization(self):
        """测试Pipeline初始化"""
        pipeline = PDFPipeline()
        
        # 验证所有组件都已初始化
        self.assertIsNotNone(pipeline.pdf_converter)
        self.assertIsNotNone(pipeline.layout_analyzer)
        self.assertIsNotNone(pipeline.ocr_processor)
        self.assertIsNotNone(pipeline.table_parser)
        self.assertIsNotNone(pipeline.formula_parser)
        self.assertIsNotNone(pipeline.reading_order)
        self.assertIsNotNone(pipeline.md_generator)
        self.assertIsNotNone(pipeline.settings)
    
    def test_pipeline_with_config(self):
        """测试使用配置的Pipeline初始化"""
        # 创建临时配置文件
        config_file = self.test_dir / "test_config.yaml"
        config_content = """
pdf_converter:
  dpi: 200
  format: 'PNG'
  
ocr_processor:
  confidence_threshold: 0.8
  language: 'ch'
  
layout_analyzer:
  model_path: 'test_model'
"""
        config_file.write_text(config_content, encoding='utf-8')
        
        pipeline = PDFPipeline(str(config_file))
        
        # 验证配置被正确加载
        self.assertEqual(pipeline.settings.pdf_converter.dpi, 200)
        self.assertEqual(pipeline.settings.ocr_processor.confidence_threshold, 0.8)
    
    def test_file_not_found_error(self):
        """测试文件不存在的错误处理"""
        pipeline = PDFPipeline()
        
        with self.assertRaises(FileNotFoundError):
            pipeline.process("nonexistent_file.pdf")
    
    @patch('src.pipeline.md_generator.MarkdownGenerator.generate')
    @patch('src.pipeline.reading_order.ReadingOrderAnalyzer.analyze')
    @patch('src.pipeline.formula_parser.FormulaParser.parse')
    @patch('src.pipeline.table_parser.TableParser.parse')
    @patch('src.pipeline.ocr_processor.OCRProcessor.process')
    @patch('src.pipeline.layout_analyzer.LayoutAnalyzer.analyze')
    @patch('src.pipeline.pdf_converter.PDFConverter.convert')
    def test_complete_pipeline_flow(self, mock_convert, mock_analyze, mock_ocr, 
                                   mock_table, mock_formula, 
                                   mock_reading_order, mock_md_gen):
        """测试完整的Pipeline流程"""
        # 设置Mock返回值
        mock_image_obj = MagicMock()
        mock_image_obj.size = (1000, 1000)
        mock_convert.return_value = [mock_image_obj]
        
        mock_layout = MagicMock()
        mock_layout.text_regions = []
        mock_layout.table_regions = []
        mock_layout.formula_regions = []
        mock_layout.image_regions = []
        mock_analyze.return_value = mock_layout
        
        mock_ocr.return_value = []
        mock_table.return_value = []
        mock_formula.return_value = []
        mock_reading_order.return_value = None
        mock_md_gen.return_value = "# Test Document\n\nThis is a test."
        
        pipeline = PDFPipeline()
        
        # 处理文档
        result = pipeline.process(str(self.test_pdf), doc_type="general")
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.document)
        self.assertIsNotNone(result.markdown)
        self.assertGreater(result.processing_time, 0)
        self.assertEqual(result.metadata["doc_type"], "general")
        self.assertEqual(result.metadata["pages_count"], 1)
        
        # 验证所有组件都被调用
        mock_convert.assert_called_once()
        mock_analyze.assert_called()
        mock_md_gen.assert_called_once()
    
    def test_different_document_types(self):
        """测试不同文档类型的处理"""
        pipeline = PDFPipeline()
        
        with patch.object(pipeline, '_process_document_core') as mock_process:
            mock_process.return_value = MagicMock()
            
            # 测试科技文献
            pipeline.process(str(self.test_pdf), doc_type="scientific")
            
            # 测试开发文档
            pipeline.process(str(self.test_pdf), doc_type="dev_doc")
            
            # 测试通用文档
            pipeline.process(str(self.test_pdf), doc_type="general")
            
            # 验证被调用了3次
            self.assertEqual(mock_process.call_count, 3)
    
    def test_output_file_saving(self):
        """测试输出文件保存"""
        output_file = self.test_dir / "output.md"
        
        pipeline = PDFPipeline()
        
        with patch.object(pipeline, '_process_document_core') as mock_process:
            mock_doc = MagicMock()
            mock_process.return_value = mock_doc
            
            with patch.object(pipeline.md_generator, 'generate') as mock_gen:
                mock_gen.return_value = "# Test Output\n\nContent here."
                
                result = pipeline.process(str(self.test_pdf), str(output_file))
                
                # 验证文件被保存
                self.assertTrue(output_file.exists())
                content = output_file.read_text(encoding='utf-8')
                self.assertIn("Test Output", content)
    
    def test_performance_metadata(self):
        """测试性能元数据收集"""
        pipeline = PDFPipeline()
        
        with patch.object(pipeline, '_process_document_core') as mock_process:
            mock_doc = MagicMock()
            mock_doc.pages = [MagicMock()]  # 模拟一页
            mock_process.return_value = mock_doc
            
            with patch.object(pipeline.md_generator, 'generate') as mock_gen:
                mock_gen.return_value = "# Performance Test"
                
                result = pipeline.process(str(self.test_pdf))
                
                # 验证性能元数据
                self.assertIn("processing_time", result.metadata)
                self.assertIn("pages_count", result.metadata)
                self.assertIn("doc_type", result.metadata)
                self.assertIn("source_file", result.metadata)


class TestPipelineIntegration(unittest.TestCase):
    """Pipeline集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = Path(tempfile.mkdtemp())
        
    def tearDown(self):
        """测试后清理"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_error_handling(self):
        """测试错误处理机制"""
        pipeline = PDFPipeline()
        
        # 测试无效文件路径
        with self.assertRaises(FileNotFoundError):
            pipeline.process("/invalid/path/file.pdf")
        
        # 测试无效文档类型
        test_pdf = self.test_dir / "test.pdf"
        test_pdf.write_bytes(b"fake pdf")
        
        with patch.object(pipeline.pdf_converter, 'convert') as mock_convert:
            mock_convert.side_effect = Exception("转换失败")
            
            with self.assertRaises(Exception):
                pipeline.process(str(test_pdf))


if __name__ == "__main__":
    # 设置测试运行器
    unittest.main(verbosity=2, buffer=True)
