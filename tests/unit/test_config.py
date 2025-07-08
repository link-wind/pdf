#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置模块单元测试
"""

import os
import tempfile
import unittest
from pathlib import Path

import yaml

from src.config import load_config, create_default_config


class TestConfig(unittest.TestCase):
    """配置模块测试类"""

    def setUp(self):
        """测试前准备"""
        # 创建临时目录
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.temp_dir.name, "test_config.yaml")

    def tearDown(self):
        """测试后清理"""
        # 清理临时目录
        self.temp_dir.cleanup()

    def test_load_config_nonexistent(self):
        """测试加载不存在的配置文件"""
        # 加载不存在的配置文件应该返回空字典
        config = load_config("nonexistent_file.yaml")
        self.assertEqual(config, {})

    def test_load_config_valid(self):
        """测试加载有效的配置文件"""
        # 创建测试配置
        test_config = {
            "pdf_converter": {"dpi": 300},
            "layout_analyzer": {"confidence_threshold": 0.5},
        }

        # 写入测试配置文件
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(test_config, f)

        # 加载配置文件
        config = load_config(self.config_path)

        # 验证配置内容
        self.assertEqual(config["pdf_converter"]["dpi"], 300)
        self.assertEqual(config["layout_analyzer"]["confidence_threshold"], 0.5)

    def test_create_default_config(self):
        """测试创建默认配置"""
        # 创建默认配置
        config = create_default_config()

        # 验证默认配置包含必要的部分
        self.assertIn("pdf_converter", config.__dict__)
        self.assertIn("layout_analyzer", config.__dict__)
        self.assertIn("ocr_processor", config.__dict__)
        self.assertIn("table_parser", config.__dict__)
        self.assertIn("formula_parser", config.__dict__)


if __name__ == "__main__":
    unittest.main()