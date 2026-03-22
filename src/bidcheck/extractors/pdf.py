"""PDF 文档提取器"""

import hashlib
from typing import Optional

from .base import BaseExtractor
from ..core.models import FileMeta


class PdfExtractor(BaseExtractor):
    """PDF 文档提取器"""

    @property
    def supported_extensions(self) -> list[str]:
        return ['.pdf']

    def extract(self, file_path: str) -> FileMeta:
        meta = FileMeta(
            file_path=file_path,
            file_hash=self._calc_hash(file_path),
            file_size=self._get_size(file_path)
        )

        try:
            from pypdf import PdfReader

            reader = PdfReader(file_path)
            info = reader.metadata

            if info:
                meta.author = info.author
                meta.pdf_producer = info.producer
                meta.pdf_creator = info.creator
                meta.create_time = info.creation_date
                meta.modify_time = info.modification_date

                # PDF 文档 ID
                if hasattr(info, 'identifier') and info.identifier:
                    meta.pdf_document_id = info.identifier

            # XMP 元数据
            self._extract_xmp(meta, reader)

            # 嵌入字体
            self._extract_fonts(meta, reader)

            # 页数
            meta.extra['page_count'] = len(reader.pages)

        except ImportError:
            meta.extra['error'] = 'pypdf not installed'
        except Exception as e:
            meta.extra['error'] = str(e)

        return meta

    def _extract_xmp(self, meta: FileMeta, reader):
        """提取 XMP 元数据"""
        try:
            if reader.xmp_metadata:
                xmp = reader.xmp_metadata
                # 生成 XMP 指纹
                xmp_str = str(xmp)
                meta.xmp_metadata_hash = hashlib.md5(xmp_str.encode()).hexdigest()

                # 提取特定字段
                if hasattr(xmp, 'creator') and xmp.creator:
                    if not meta.author:
                        meta.author = xmp.creator

                # 提取 PDF 版本信息
                if hasattr(xmp, 'pdf_producer'):
                    if not meta.pdf_producer:
                        meta.pdf_producer = xmp.pdf_producer

        except Exception:
            pass

    def _extract_fonts(self, meta: FileMeta, reader):
        """提取嵌入字体"""
        fonts = []
        try:
            for page in reader.pages:
                if '/Resources' in page:
                    resources = page['/Resources']
                    if '/Font' in resources:
                        font_obj = resources['/Font']
                        if hasattr(font_obj, 'keys'):
                            for font_name in font_obj.keys():
                                fonts.append(str(font_name))
        except Exception:
            pass

        meta.embedded_fonts = list(set(fonts))

    def _extract_images(self, meta: FileMeta, reader):
        """提取嵌入图片信息"""
        # PDF 图片提取较复杂，这里简化处理
        pass
