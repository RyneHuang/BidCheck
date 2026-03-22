"""Excel 文档提取器"""

import hashlib
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from typing import Optional

from .base import BaseExtractor
from .docx import DocxExtractor
from ..core.models import FileMeta

# XML 命名空间
NAMESPACES = {
    'cp': 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'dcterms': 'http://purl.org/dc/terms/',
    'ep': 'http://schemas.openxmlformats.org/officeDocument/2006/extended-properties',
    's': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
}


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

        try:
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

                # 6. 嵌入图片哈希
                self._extract_image_hashes(meta, zf)

        except Exception as e:
            meta.extra['error'] = str(e)

        return meta

    def _extract_core_props(self, meta: FileMeta, zf: ZipFile):
        """提取核心属性"""
        try:
            xml_content = zf.read('docProps/core.xml')
            root = ET.fromstring(xml_content)

            meta.author = self._get_xml_text(root, 'dc:creator')
            meta.last_modified_by = self._get_xml_text(root, 'cp:lastModifiedBy')
            meta.create_time = DocxExtractor._parse_datetime(
                self._get_xml_text(root, 'dcterms:created')
            )
            meta.modify_time = DocxExtractor._parse_datetime(
                self._get_xml_text(root, 'dcterms:modified')
            )
        except KeyError:
            pass

    def _extract_app_props(self, meta: FileMeta, zf: ZipFile):
        """提取扩展属性"""
        try:
            xml_content = zf.read('docProps/app.xml')
            root = ET.fromstring(xml_content)

            meta.company = self._get_xml_text(root, 'ep:Company')
            meta.manager = self._get_xml_text(root, 'ep:Manager')
        except KeyError:
            pass

    def _extract_shared_strings(self, meta: FileMeta, zf: ZipFile):
        """提取共享字符串指纹 (关键!)"""
        strings = []
        ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

        # 方式1: 从 sharedStrings.xml 提取
        try:
            content = zf.read('xl/sharedStrings.xml')
            root = ET.fromstring(content)

            for si in root.iter(f'{ns}si'):
                text_parts = []
                for t in si.iter(f'{ns}t'):
                    if t.text:
                        text_parts.append(t.text)
                if text_parts:
                    strings.append(''.join(text_parts))
        except KeyError:
            pass

        # 方式2: 从工作表中提取内联字符串 (inlineStr)
        try:
            content = zf.read('xl/workbook.xml')
            root = ET.fromstring(content)

            # 获取所有工作表
            for sheet in root.iter(f'{ns}sheet'):
                sheet_name = sheet.get('name')
                sheet_id = sheet.get('sheetId')

                # 尝试读取工作表文件
                sheet_file = f'xl/worksheets/sheet{sheet_id}.xml'
                if sheet_file in [n for n in zf.namelist()]:
                    try:
                        sheet_content = zf.read(sheet_file)
                        sheet_root = ET.fromstring(sheet_content)

                        # 提取内联字符串
                        for is_elem in sheet_root.iter(f'{ns}is'):
                            for t in is_elem.iter(f'{ns}t'):
                                if t.text:
                                    strings.append(t.text)
                    except:
                        pass
        except KeyError:
            pass

        # 生成指纹
        if strings:
            combined = '|'.join(sorted(set(strings)))
            meta.shared_string_hash = hashlib.md5(combined.encode()).hexdigest()
            meta.extra['string_count'] = len(strings)
        else:
            meta.shared_string_hash = None
            meta.extra['string_count'] = 0

    def _extract_style_fingerprint(self, meta: FileMeta, zf: ZipFile):
        """提取样式指纹"""
        try:
            content = zf.read('xl/styles.xml')
            meta.style_fingerprint = hashlib.md5(content).hexdigest()
        except KeyError:
            pass

    def _extract_sheets_info(self, meta: FileMeta, zf: ZipFile):
        """提取工作表信息"""
        try:
            content = zf.read('xl/workbook.xml')
            root = ET.fromstring(content)

            sheets = []
            ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

            for sheet in root.iter(f'{ns}sheet'):
                name = sheet.get('name')
                if name:
                    sheets.append(name)

            meta.sheet_count = len(sheets)
            meta.extra['sheet_names'] = sheets
        except KeyError:
            pass

    def _extract_image_hashes(self, meta: FileMeta, zf: ZipFile):
        """提取嵌入图片哈希"""
        hashes = []
        for name in zf.namelist():
            if 'media/' in name:
                content = zf.read(name)
                hashes.append(hashlib.md5(content).hexdigest())
        meta.image_hashes = hashes

    @staticmethod
    def _get_xml_text(root, tag: str) -> Optional[str]:
        """获取 XML 元素文本"""
        prefix, local = tag.split(':')
        ns = NAMESPACES.get(prefix, '')
        if ns:
            full_tag = f'{{{ns}}}{local}'
        else:
            full_tag = local
        elem = root.find(full_tag)
        return elem.text if elem is not None and elem.text else None
