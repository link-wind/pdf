"""
测试套件主文件
"""

import unittest
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from test_pipeline import TestPDFPipeline


def create_test_suite():
    """创建测试套件"""
    suite = unittest.TestSuite()
    
    # 添加各个模块的测试
    suite.addTest(unittest.makeSuite(TestPDFConverter))
    suite.addTest(unittest.makeSuite(TestLayoutAnalyzer))
    suite.addTest(unittest.makeSuite(TestOCRProcessor))
    suite.addTest(unittest.makeSuite(TestPDFPipeline))
    
    return suite


def run_tests():
    """运行所有测试"""
    runner = unittest.TextTestRunner(verbosity=2)
    suite = create_test_suite()
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
