"""PDF转换器模块

使用pdf2image将PDF文件转换为图像文件
"""

import os
from typing import List, Optional, Dict, Any
from pathlib import Path
from PIL import Image
from loguru import logger

try:
    from pdf2image import convert_from_path
    HAS_PDF2IMAGE = True
except ImportError:
    HAS_PDF2IMAGE = False
    logger.warning("pdf2image未安装，请使用: pip install pdf2image")

try:
    import fitz  # PyMuPDF作为备选
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False


class PDFConverter:
    """PDF转图像转换器"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化PDF转换器
        
        Args:
            config: 配置字典，包含以下可选参数：
                - dpi: 输出图像DPI (默认300)
                - format: 输出格式 'PNG', 'JPEG', 'TIFF' (默认'PNG')
                - quality: JPEG质量 1-100 (默认95)
                - poppler_path: Poppler工具路径 (Windows需要)
                - use_cairo: 是否使用Cairo后端 (默认False)
                - single_thread: 是否单线程处理 (默认True)
        """
        self.config = config
        self.dpi = getattr(config, 'dpi', 300)
        self.format = getattr(config, 'format', 'PNG')
        self.quality = getattr(config, 'quality', 95)
        self.poppler_path = getattr(config, 'poppler_path', None)
        self.use_cairo = getattr(config, 'use_cairo', False)
        self.single_thread = getattr(config, 'single_thread', True)
        
        self._validate_config()
        self._init_converter()
        
    def _validate_config(self) -> None:
        """验证配置参数"""
        if self.dpi < 50 or self.dpi > 600:
            logger.warning(f"DPI值 {self.dpi} 可能不合适，建议使用 100-300")
            
        if self.format not in ['PNG', 'JPEG', 'TIFF', 'BMP', 'PPM']:
            logger.warning(f"不支持的格式 {self.format}，使用PNG")
            self.format = 'PNG'
            
        if self.quality < 1 or self.quality > 100:
            logger.warning(f"质量值 {self.quality} 无效，使用95")
            self.quality = 95
            
    def _init_converter(self) -> None:
        """初始化转换器"""
        if not HAS_PDF2IMAGE and not HAS_PYMUPDF:
            raise ImportError("需要安装pdf2image或PyMuPDF: pip install pdf2image 或 pip install pymupdf")
        
        if HAS_PDF2IMAGE:
            self.converter_type = 'pdf2image'
            logger.info("使用pdf2image转换引擎")
        elif HAS_PYMUPDF:
            self.converter_type = 'pymupdf'
            logger.info("使用PyMuPDF转换引擎")
            
        logger.info(f"PDF转换器初始化完成 - DPI: {self.dpi}, 格式: {self.format}")
    
    def convert_pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """将PDF转换为图像列表
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            List[Image.Image]: 转换后的图像列表
            
        Raises:
            FileNotFoundError: PDF文件不存在
            ValueError: 文件格式不正确
            Exception: 转换过程中的其他错误
        """
        pdf_path = Path(pdf_path)
        
        # 验证文件
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
            
        if not pdf_path.suffix.lower() == '.pdf':
            raise ValueError(f"不是有效的PDF文件: {pdf_path}")
            
        logger.info(f"开始转换PDF: {pdf_path}")
        
        try:
            if self.converter_type == 'pdf2image':
                images = self._convert_with_pdf2image(pdf_path)
            else:
                images = self._convert_with_pymupdf(pdf_path)
                
            logger.info(f"PDF转换完成，共 {len(images)} 页")
            return images
            
        except Exception as e:
            logger.error(f"PDF转换失败: {e}")
            raise
    
    def _convert_with_pdf2image(self, pdf_path: Path) -> List[Image.Image]:
        """使用pdf2image转换PDF"""
        try:
            # 构建转换参数
            convert_kwargs = {
                'dpi': self.dpi,
                'fmt': self.format.lower(),
                'thread_count': 1 if self.single_thread else None,
                'use_pdftocairo': self.use_cairo,
            }
            
            # 添加poppler路径（Windows需要）
            if self.poppler_path:
                convert_kwargs['poppler_path'] = self.poppler_path
                
            # 添加质量设置（仅JPEG）
            if self.format.upper() == 'JPEG':
                convert_kwargs['jpegopt'] = {'quality': self.quality}
                
            # 转换PDF
            logger.debug(f"转换参数: {convert_kwargs}")
            images = convert_from_path(str(pdf_path), **convert_kwargs)
            
            return images
            
        except Exception as e:
            logger.error(f"pdf2image转换失败: {e}")
            raise
    
    def _convert_with_pymupdf(self, pdf_path: Path) -> List[Image.Image]:
        """使用PyMuPDF转换PDF（备选方案）"""
        import io
        
        try:
            doc = fitz.open(str(pdf_path))
            images = []
            
            # 计算缩放矩阵
            zoom = self.dpi / 72.0  # 72是PDF默认DPI
            mat = fitz.Matrix(zoom, zoom)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # 渲染页面
                pix = page.get_pixmap(matrix=mat)
                
                # 转换为PIL Image
                if self.format.upper() == 'PNG':
                    img_data = pix.tobytes("png")
                elif self.format.upper() == 'JPEG':
                    img_data = pix.tobytes("jpeg", jpg_quality=self.quality)
                else:
                    img_data = pix.tobytes("png")  # 默认PNG
                    
                img = Image.open(io.BytesIO(img_data))
                images.append(img)
                
                # 清理内存
                pix = None
                
            doc.close()
            return images
            
        except Exception as e:
            logger.error(f"PyMuPDF转换失败: {e}")
            raise
    
    def convert_single_page(self, pdf_path: str, page_number: int) -> Image.Image:
        """转换PDF的单个页面
        
        Args:
            pdf_path: PDF文件路径
            page_number: 页码（从0开始）
            
        Returns:
            Image.Image: 转换后的图像
        """
        if self.converter_type == 'pdf2image':
            return self._convert_single_page_pdf2image(pdf_path, page_number)
        else:
            return self._convert_single_page_pymupdf(pdf_path, page_number)
    
    def _convert_single_page_pdf2image(self, pdf_path: str, page_number: int) -> Image.Image:
        """使用pdf2image转换单页"""
        try:
            convert_kwargs = {
                'dpi': self.dpi,
                'fmt': self.format.lower(),
                'first_page': page_number + 1,
                'last_page': page_number + 1,
                'use_pdftocairo': self.use_cairo,
            }
            
            if self.poppler_path:
                convert_kwargs['poppler_path'] = self.poppler_path
                
            images = convert_from_path(pdf_path, **convert_kwargs)
            return images[0] if images else None
            
        except Exception as e:
            logger.error(f"单页转换失败: {e}")
            raise
    
    def _convert_single_page_pymupdf(self, pdf_path: str, page_number: int) -> Image.Image:
        """使用PyMuPDF转换单页"""
        import io
        
        try:
            doc = fitz.open(pdf_path)
            if page_number >= len(doc):
                raise IndexError(f"页码 {page_number} 超出范围，文档共 {len(doc)} 页")
                
            page = doc[page_number]
            zoom = self.dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            
            pix = page.get_pixmap(matrix=mat)
            
            if self.format.upper() == 'PNG':
                img_data = pix.tobytes("png")
            elif self.format.upper() == 'JPEG':
                img_data = pix.tobytes("jpeg", jpg_quality=self.quality)
            else:
                img_data = pix.tobytes("png")
                
            img = Image.open(io.BytesIO(img_data))
            
            pix = None
            doc.close()
            return img
            
        except Exception as e:
            logger.error(f"PyMuPDF单页转换失败: {e}")
            raise
    
    def get_page_count(self, pdf_path: str) -> int:
        """获取PDF页数
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            int: 页数
        """
        try:
            if HAS_PYMUPDF:
                doc = fitz.open(pdf_path)
                count = len(doc)
                doc.close()
                return count
            else:
                # 使用pdf2image获取页数（需要实际转换第一页）
                images = convert_from_path(pdf_path, dpi=72, first_page=1, last_page=1)
                # 这里需要其他方法获取总页数，pdf2image没有直接方法
                # 可以使用PyPDF2或其他库
                logger.warning("无法直接获取页数，建议安装PyMuPDF")
                return 1
                
        except Exception as e:
            logger.error(f"获取页数失败: {e}")
            return 0
    
    def save_images(self, images: List[Image.Image], output_dir: str, 
                   filename_prefix: str = "page") -> List[str]:
        """保存图像列表到文件
        
        Args:
            images: 图像列表
            output_dir: 输出目录
            filename_prefix: 文件名前缀
            
        Returns:
            List[str]: 保存的文件路径列表
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        saved_paths = []
        
        for i, img in enumerate(images):
            filename = f"{filename_prefix}_{i+1:03d}.{self.format.lower()}"
            output_path = output_dir / filename
            
            # 保存图像
            if self.format.upper() == 'JPEG':
                img.save(output_path, format='JPEG', quality=self.quality)
            else:
                img.save(output_path, format=self.format)
                
            saved_paths.append(str(output_path))
            
        logger.info(f"已保存 {len(saved_paths)} 个图像到 {output_dir}")
        return saved_paths
    
    def get_info(self) -> Dict[str, Any]:
        """获取转换器信息
        
        Returns:
            Dict[str, Any]: 转换器信息
        """
        return {
            'converter_type': self.converter_type,
            'dpi': self.dpi,
            'format': self.format,
            'quality': self.quality,
            'use_cairo': self.use_cairo,
            'single_thread': self.single_thread,
            'has_pdf2image': HAS_PDF2IMAGE,
            'has_pymupdf': HAS_PYMUPDF,
        }


# 保持向后兼容性
__all__ = ['PDFConverter']