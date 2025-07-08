#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF处理流程集成测试
"""

import os
import tempfile
import unittest
from pathlib import Path

import pytest

from src import PDFPipeline, load_config
from src.config import create_default_config


@pytest.mark.skipif(not os.path.exists("tests/resources/sample.pdf"),
                    reason="测试PDF文件不存在")
class TestPDFPipeline(unittest.TestCase):
    """PDF处理流程测试类"""

    def setUp(self):
        """测试前准备"""
        # 创建临时目录
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = os.path.join(self.temp_dir.name, "output")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 创建默认配置
        self.config = create_default_config()
        self.config.pdf_converter.temp_dir = os.path.join(self.temp_dir.name, "temp")
        self.config.markdown_generator.output_dir = self.output_dir
        self.config.markdown_generator.image_dir = "images"
        
        # 初始化PDF处理流程
        self.pipeline = PDFPipeline(self.config)
        
        # 测试PDF文件路径
        self.test_pdf_path = "tests/resources/sample.pdf"
        
        # 如果测试资源目录不存在，则创建
        os.makedirs("tests/resources", exist_ok=True)

    def tearDown(self):
        """测试后清理"""
        # 清理临时目录
        self.temp_dir.cleanup()

    @pytest.mark.skipif(not os.path.exists("tests/resources/sample.pdf"),
                        reason="测试PDF文件不存在")
    def test_process_pdf(self):
        """测试PDF处理流程"""
        # 如果测试PDF文件不存在，则跳过测试
        if not os.path.exists(self.test_pdf_path):
            self.skipTest("测试PDF文件不存在")
            
        # 处理PDF
        output_path = self.pipeline.process(self.test_pdf_path, self.output_dir)
        
        # 验证输出文件存在
        self.assertTrue(os.path.exists(output_path))
        
        # 验证输出文件是Markdown格式
        self.assertTrue(output_path.endswith(".md"))
        
        # 验证输出文件内容
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # 验证Markdown内容包含基本结构
        self.assertIn("#", content)  # 标题
        
        # 验证图像目录存在
        image_dir = os.path.join(os.path.dirname(output_path), "images")
        if self.config.markdown_generator.include_images:
            self.assertTrue(os.path.exists(image_dir))

    @pytest.mark.skipif(not os.path.exists("tests/resources/sample.pdf"),
                        reason="测试PDF文件不存在")
    def test_pipeline_with_custom_config(self):
        """测试使用自定义配置的PDF处理流程"""
        # 如果测试PDF文件不存在，则跳过测试
        if not os.path.exists(self.test_pdf_path):
            self.skipTest("测试PDF文件不存在")
            
        # 创建自定义配置
        custom_config_path = os.path.join(self.temp_dir.name, "custom_config.yaml")
        with open(custom_config_path, "w", encoding="utf-8") as f:
            f.write("""pdf_converter:
  dpi: 200
  format: JPEG
  quality: 80
markdown_generator:
  output_dir: {}
  include_images: true
  image_dir: custom_images
  generate_toc: true
""".format(self.output_dir))
            
        # 加载自定义配置
        config_dict = load_config(custom_config_path)
        
        # 使用自定义配置初始化PDF处理流程
        custom_pipeline = PDFPipeline(config_dict)
        
        # 处理PDF
        output_path = custom_pipeline.process(self.test_pdf_path, self.output_dir)
        
        # 验证输出文件存在
        self.assertTrue(os.path.exists(output_path))
        
        # 验证自定义图像目录存在
        custom_image_dir = os.path.join(os.path.dirname(output_path), "custom_images")
        self.assertTrue(os.path.exists(custom_image_dir))


if __name__ == "__main__":
    unittest.main()