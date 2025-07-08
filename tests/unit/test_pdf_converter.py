#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF转换器单元测试
"""

import os
import tempfile
import unittest
from pathlib import Path

import pytest

from src.config import create_default_config
from src.processors.pdf_converter import PDFConverter


@pytest.mark.skipif(not os.path.exists("tests/resources/sample.pdf"),
                    reason="测试PDF文件不存在")
class TestPDFConverter(unittest.TestCase):
    """PDF转换器测试类"""

    def setUp(self):
        """测试前准备"""
        # 创建临时目录
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = self.temp_dir.name
        
        # 创建默认配置
        config = create_default_config()
        config.pdf_converter.temp_dir = self.output_dir
        
        # 初始化PDF转换器
        self.converter = PDFConverter(config.pdf_converter)
        
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
    def test_convert_to_images(self):
        """测试PDF转换为图像"""
        # 如果测试PDF文件不存在，则跳过测试
        if not os.path.exists(self.test_pdf_path):
            self.skipTest("测试PDF文件不存在")
            
        # 转换PDF为图像
        images = self.converter.convert_to_images(self.test_pdf_path)
        
        # 验证转换结果
        self.assertIsNotNone(images)
        self.assertGreater(len(images), 0)
        
        # 验证图像格式
        for img in images:
            self.assertIsNotNone(img)
            # 验证图像尺寸
            self.assertGreater(img.width, 0)
            self.assertGreater(img.height, 0)

    @pytest.mark.skipif(not os.path.exists("tests/resources/sample.pdf"),
                        reason="测试PDF文件不存在")
    def test_get_pdf_metadata(self):
        """测试获取PDF元数据"""
        # 如果测试PDF文件不存在，则跳过测试
        if not os.path.exists(self.test_pdf_path):
            self.skipTest("测试PDF文件不存在")
            
        # 获取PDF元数据
        metadata = self.converter.get_pdf_metadata(self.test_pdf_path)
        
        # 验证元数据
        self.assertIsNotNone(metadata)
        self.assertIsInstance(metadata, dict)
        
        # 验证元数据包含基本信息
        self.assertIn("page_count", metadata)
        self.assertGreater(metadata["page_count"], 0)


if __name__ == "__main__":
    unittest.main()