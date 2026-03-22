# Phase 2: 文件提取器实现

## 概述

本阶段实现 Word、Excel、PDF 三种文件格式的元数据提取器，负责从文件中提取所有可用的痕迹信息。

## 依赖库

```toml
# pyproject.toml
[project]
dependencies = [
    "python-docx>=0.21.0",
    "openpyxl>=3.1.0",
    "pypdf>=4.0.0",
    "oletools>=0.60.0",
    "pillow>=10.0.0",
]
```

## 提取器基类

```python
# src/bidcheck/extractors/base.py

from abc import ABC, abstractmethod
from ..core.models import FileMeta


class BaseExtractor(ABC):
    """提取器基类"""

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """支持的文件扩展名"""
        pass

    @abstractmethod
    def extract(self, file_path: str) -> FileMeta:
        """提取文件元数据"""
        pass

    def can_extract(self, file_path: str) -> bool:
        """检查是否支持该文件"""
        return any(
            file_path.lower().endswith(ext)
            for ext in self.supported_extensions
        )

    @staticmethod
    def _calc_hash(file_path: str) -> str:
        """计算文件 SHA256 哈希"""
        import hashlib
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def _get_size(file_path: str) -> int:
        """获取文件大小"""
        import os
        return os.path.getsize(file_path)
```

## Word 提取器

```python
# src/bidcheck/extractors/docx.py

import hashlib
from datetime import datetime
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from typing import Optional
from .base import BaseExtractor
from ..core.models import FileMeta

# XML 命名空间
NAMESPACES = {
    'cp': 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'dcterms': 'http://purl.org/dc/terms/',
    'dcmitype': 'http://purl.org/dc/dcmitype/',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    'ep': 'http://schemas.openxmlformats.org/officeDocument/2006/extended-properties',
    'vt': 'http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes',
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
}


class DocxExtractor(BaseExtractor):
    """Word 文档提取器 (.docx)"""

    @property
    def supported_extensions(self) -> list[str]:
        return ['.docx']

    def extract(self, file_path: str) -> FileMeta:
        meta = FileMeta(
            file_path=file_path,
            file_hash=self._calc_hash(file_path),
            file_size=self._get_size(file_path)
        )

        with ZipFile(file_path) as zf:
            # 1. 核心属性 (core.xml)
            self._extract_core_props(meta, zf)

            # 2. 扩展属性 (app.xml)
            self._extract_app_props(meta, zf)

            # 3. RSID 列表 (document.xml)
            self._extract_rsids(meta, zf)

            # 4. OLE 对象 GUID
            self._extract_ole_guids(meta, zf)

            # 5. 嵌入图片哈希
            self._extract_image_hashes(meta, zf)

            # 6. 自定义 XML 部件
            self._extract_custom_xml(meta, zf)

        return meta

    def _extract_core_props(self, meta: FileMeta, zf: ZipFile):
        """提取核心属性"""
        try:
            xml_content = zf.read('docProps/core.xml')
            root = ET.fromstring(xml_content)

            meta.author = self._get_xml_text(root, 'dc:creator', NAMESPACES)
            meta.last_modified_by = self._get_xml_text(root, 'cp:lastModifiedBy', NAMESPACES)
            meta.create_time = self._parse_datetime(
                self._get_xml_text(root, 'dcterms:created', NAMESPACES)
            )
            meta.modify_time = self._parse_datetime(
                self._get_xml_text(root, 'dcterms:modified', NAMESPACES)
            )
        except KeyError:
            pass  # 文件不存在

    def _extract_app_props(self, meta: FileMeta, zf: ZipFile):
        """提取扩展属性"""
        try:
            xml_content = zf.read('docProps/app.xml')
            root = ET.fromstring(xml_content)

            meta.company = self._get_xml_text(root, 'ep:Company', NAMESPACES)
            meta.manager = self._get_xml_text(root, 'ep:Manager', NAMESPACES)
            meta.template_path = self._get_xml_text(root, 'ep:Template', NAMESPACES)

            # 打印信息
            pages = self._get_xml_text(root, 'ep:Pages', NAMESPACES)
            if pages:
                meta.extra['pages'] = int(pages)
        except KeyError:
            pass

    def _extract_rsids(self, meta: FileMeta, zf: ZipFile):
        """提取 RSID 列表 (关键指纹)"""
        try:
            xml_content = zf.read('word/document.xml')
            root = ET.fromstring(xml_content)

            rsids = set()

            # 从文档设置中提取
            for rsid_elem in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rsid'):
                for attr in ['rsidRoot', 'rsid']:
                    val = rsid_elem.get(f'{{http://schemas.openxmlformats.org/wordprocessingml/2006/main}}{attr}')
                    if val:
                        rsids.add(val)

            # 从段落中提取
            for p_elem in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                pPr = p_elem.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr')
                if pPr is not None:
                    for rsid in pPr.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rsid'):
                        val = rsid.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')
                        if val:
                            rsids.add(val)

            meta.rsids = list(rsids)
        except KeyError:
            pass

    def _extract_ole_guids(self, meta: FileMeta, zf: ZipFile):
        """提取 OLE 对象中的 GUID"""
        guids = []

        # 检查嵌入对象
        for name in zf.namelist():
            if 'embeddings/' in name and name.endswith('.bin'):
                try:
                    content = zf.read(name)
                    # 查找 GUID 模式
                    import re
                    pattern = rb'\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}'
                    matches = re.findall(pattern, content)
                    guids.extend([m.decode('utf-8') for m in matches])
                except:
                    pass

        meta.ole_guids = list(set(guids))

    def _extract_image_hashes(self, meta: FileMeta, zf: ZipFile):
        """提取嵌入图片的哈希"""
        hashes = []
        for name in zf.namelist():
            if 'media/' in name:
                content = zf.read(name)
                hashes.append(hashlib.md5(content).hexdigest())
        meta.image_hashes = hashes

    def _extract_custom_xml(self, meta: FileMeta, zf: ZipFile):
        """提取自定义 XML 部件"""
        custom_parts = {}
        for name in zf.namelist():
            if 'customXml/' in name and name.endswith('.xml'):
                try:
                    content = zf.read(name)
                    custom_parts[name] = hashlib.md5(content).hexdigest()
                except:
                    pass
        if custom_parts:
            meta.extra['custom_xml'] = custom_parts

    @staticmethod
    def _get_xml_text(root, tag: str, ns: dict) -> Optional[str]:
        """获取 XML 元素文本"""
        elem = root.find(tag, ns)
        return elem.text if elem is not None and elem.text else None

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """解析 ISO 格式日期时间"""
        if not dt_str:
            return None
        try:
            # 处理时区
            if dt_str.endswith('Z'):
                dt_str = dt_str[:-1] + '+00:00'
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except:
            return None


class DocExtractor(BaseExtractor):
    """旧版 Word 文档提取器 (.doc) - 使用 oletools"""

    @property
    def supported_extensions(self) -> list[str]:
        return ['.doc']

    def extract(self, file_path: str) -> FileMeta:
        meta = FileMeta(
            file_path=file_path,
            file_hash=self._calc_hash(file_path),
            file_size=self._get_size(file_path)
        )

        try:
            from oletools.olevba import VBA_Parser
            from olefile import OleFileIO

            with OleFileIO(file_path) as ole:
                # 读取 \005SummaryInformation
                if ole.exists('\x005SummaryInformation'):
                    si = ole.getproperties('\x005SummaryInformation')
                    meta.author = si.get(4)  # PID_AUTHOR
                    meta.create_time = si.get(12)  # PID_CREATE_DTM
                    meta.modify_time = si.get(13)  # PID_LASTSAVE_DTM

                # 读取 \005DocumentSummaryInformation
                if ole.exists('\x005DocumentSummaryInformation'):
                    dsi = ole.getproperties('\x005DocumentSummaryInformation')
                    meta.company = dsi.get(14)  # PID_COMPANY
                    meta.manager = dsi.get(12)  # PID_MANAGER

                # 提取 OLE 流中的 GUID
                self._extract_ole_guids_ole(meta, ole)

        except ImportError:
            pass
        except Exception as e:
            meta.extra['error'] = str(e)

        return meta

    def _extract_ole_guids_ole(self, meta: FileMeta, ole):
        """从 OLE 流提取 GUID"""
        import re
        guids = []

        for stream in ole.listdir():
            try:
                content = ole.openstream(stream).read()
                pattern = rb'\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}'
                matches = re.findall(pattern, content)
                guids.extend([m.decode('utf-8') for m in matches])
            except:
                pass

        meta.ole_guids = list(set(guids))
```

## Excel 提取器

```python
# src/bidcheck/extractors/xlsx.py

import hashlib
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from .base import BaseExtractor
from ..core.models import FileMeta
from .docx import DocxExtractor  # 复用命名空间和工具方法


class XlsxExtractor(BaseExtractor):
    """Excel 文档提取器 (.xlsx)"""

    @property
    def supported_extensions(self) -> list[str]:
        return ['.xlsx']

    def extract(self, file_path: str) -> FileMeta:
        meta = FileMeta(
            file_path=file_path,
            file_hash=self._calc_hash(file_path),
            file_size=self._get_size(file_path)
        )

        with ZipFile(file_path) as zf:
            # 1. 核心属性
            self._extract_core_props(meta, zf)

            # 2. 扩展属性
            self._extract_app_props(meta, zf)

            # 3. 共享字符串指纹
            self._extract_shared_strings(meta, zf)

            # 4. 样式指纹
            self._extract_style_fingerprint(meta, zf)

            # 5. 工作表信息
            self._extract_sheets_info(meta, zf)

        return meta

    def _extract_core_props(self, meta: FileMeta, zf: ZipFile):
        """提取核心属性"""
        try:
            xml_content = zf.read('docProps/core.xml')
            root = ET.fromstring(xml_content)

            meta.author = DocxExtractor._get_xml_text(root, 'dc:creator', NAMESPACES)
            meta.last_modified_by = DocxExtractor._get_xml_text(root, 'cp:lastModifiedBy', NAMESPACES)
            meta.create_time = DocxExtractor._parse_datetime(
                DocxExtractor._get_xml_text(root, 'dcterms:created', NAMESPACES)
            )
            meta.modify_time = DocxExtractor._parse_datetime(
                DocxExtractor._get_xml_text(root, 'dcterms:modified', NAMESPACES)
            )
        except KeyError:
            pass

    def _extract_app_props(self, meta: FileMeta, zf: ZipFile):
        """提取扩展属性"""
        try:
            xml_content = zf.read('docProps/app.xml')
            root = ET.fromstring(xml_content)

            meta.company = DocxExtractor._get_xml_text(root, 'ep:Company', NAMESPACES)
            meta.manager = DocxExtractor._get_xml_text(root, 'ep:Manager', NAMESPACES)

            # 工作表数量
            sheet_names = DocxExtractor._get_xml_text(root, 'ep:TitlesOfParts', NAMESPACES)
            # 简化处理
        except KeyError:
            pass

    def _extract_shared_strings(self, meta: FileMeta, zf: ZipFile):
        """提取共享字符串指纹 (关键!)"""
        try:
            content = zf.read('xl/sharedStrings.xml')
            root = ET.fromstring(content)

            # 提取所有字符串
            strings = []
            for si in root.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
                text_parts = []
                for t in si.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t'):
                    if t.text:
                        text_parts.append(t.text)
                if text_parts:
                    strings.append(''.join(text_parts))

            # 生成指纹
            combined = '|'.join(sorted(strings))
            meta.shared_string_hash = hashlib.md5(combined.encode()).hexdigest()
            meta.extra['string_count'] = len(strings)

        except KeyError:
            pass

    def _extract_style_fingerprint(self, meta: FileMeta, zf: ZipFile):
        """提取样式指纹"""
        try:
            content = zf.read('xl/styles.xml')
            # 基于样式文件内容生成指纹
            meta.style_fingerprint = hashlib.md5(content).hexdigest()
        except KeyError:
            pass

    def _extract_sheets_info(self, meta: FileMeta, zf: ZipFile):
        """提取工作表信息"""
        try:
            content = zf.read('xl/workbook.xml')
            root = ET.fromstring(content)

            sheets = []
            for sheet in root.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet'):
                sheets.append(sheet.get('name'))

            meta.sheet_count = len(sheets)
            meta.extra['sheet_names'] = sheets
        except KeyError:
            pass
```

## PDF 提取器

```python
# src/bidcheck/extractors/pdf.py

import hashlib
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
                if hasattr(info, 'identifier'):
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
                if hasattr(xmp, 'creator'):
                    if not meta.author:
                        meta.author = xmp.creator
        except:
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
                        for font_name in font_obj:
                            fonts.append(font_name)
        except:
            pass

        meta.embedded_fonts = list(set(fonts))
```

## 提取器工厂

```python
# src/bidcheck/extractors/__init__.py

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


__all__ = ['BaseExtractor', 'get_extractor', 'DocxExtractor', 'DocExtractor',
           'XlsxExtractor', 'PdfExtractor']
```

## 验收标准

- [ ] DocxExtractor 可提取 Word 2007+ 文档的所有元数据
- [ ] DocExtractor 可提取旧版 .doc 文档元数据
- [ ] XlsxExtractor 可提取 Excel 的共享字符串指纹
- [ ] PdfExtractor 可提取 PDF 的 XMP 元数据
- [ ] RSID 提取正确
- [ ] OLE GUID 提取正确
- [ ] 文件哈希计算正确
- [ ] 单元测试覆盖率 > 80%
