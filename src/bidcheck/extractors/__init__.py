"""文件提取器"""

from .base import BaseExtractor
from .docx import DocxExtractor, DocExtractor
from .xlsx import XlsxExtractor
from .pdf import PdfExtractor

_EXTRACTORS = [
    DocxExtractor(),
    DocExtractor(),
    XlsxExtractor(),
    PdfExtractor(),
]


def get_extractor(file_path: str) -> BaseExtractor | None:
    """根据文件路径获取合适的提取器"""
    for extractor in _EXTRACTORS:
        if extractor.can_extract(file_path):
            return extractor
    return None


__all__ = [
    "BaseExtractor",
    "get_extractor",
    "DocxExtractor",
    "DocExtractor",
    "XlsxExtractor",
    "PdfExtractor",
]
