"""Word 文档提取器"""

import hashlib
import re
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
    'ep': 'http://schemas.openxmlformats.org/officeDocument/2006/extended-properties',
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
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

        try:
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

                # 6. 样式指纹 (styles.xml)
                self._extract_style_fingerprint(meta, zf)
        except Exception as e:
            meta.extra['error'] = str(e)

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
            pass

    def _extract_app_props(self, meta: FileMeta, zf: ZipFile):
        """提取扩展属性"""
        try:
            xml_content = zf.read('docProps/app.xml')
            root = ET.fromstring(xml_content)

            meta.company = self._get_xml_text(root, 'ep:Company', NAMESPACES)
            meta.manager = self._get_xml_text(root, 'ep:Manager', NAMESPACES)
            meta.template_path = self._get_xml_text(root, 'ep:Template', NAMESPACES)

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
            ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
            ns_w = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

            # 从段落属性中提取 rsidR, rsidRPr 等属性
            for p_elem in root.iter(f'{ns}p'):
                # 段落属性
                pPr = p_elem.find(f'{ns}pPr')
                if pPr is not None:
                    # 检查段落属性中的 rsid 属性
                    for attr_name in ['{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rsidR',
                                      '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rsidRPr',
                                      '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rsidDel',
                                      '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rsidP']:
                        val = pPr.get(attr_name)
                        if val:
                            rsids.add(val)

            # 从运行 (run) 中提取 rsidR, rsidDel 等属性
            for r_elem in root.iter(f'{ns}r'):
                rPr = r_elem.find(f'{ns}rPr')
                if rPr is not None:
                    for attr_name in ['{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rsidR',
                                      '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rsidRPr']:
                        val = rPr.get(attr_name)
                        if val:
                            rsids.add(val)

            # 从文档设置中提取 (settings.xml)
            try:
                settings_content = zf.read('word/settings.xml')
                settings_root = ET.fromstring(settings_content)
                for rsid_elem in settings_root.iter(f'{ns}rsid'):
                    val = rsid_elem.get(f'{ns}val')
                    if val:
                        rsids.add(val)
            except KeyError:
                pass

            meta.rsids = list(rsids)
        except KeyError:
            pass

    def _extract_ole_guids(self, meta: FileMeta, zf: ZipFile):
        """提取 OLE 对象中的 GUID"""
        guids = []
        pattern = rb'\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}'

        for name in zf.namelist():
            if 'embeddings/' in name and name.endswith('.bin'):
                try:
                    content = zf.read(name)
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

    def _extract_style_fingerprint(self, meta: FileMeta, zf: ZipFile):
        """提取样式指纹"""
        try:
            content = zf.read('word/styles.xml')
            meta.style_fingerprint = hashlib.md5(content).hexdigest()
        except KeyError:
            pass

    @staticmethod
    def _get_xml_text(root, tag: str, ns: dict) -> Optional[str]:
        """获取 XML 元素文本"""
        # 处理带命名空间的标签
        prefix, local = tag.split(':')
        full_tag = f'{{{ns[prefix]}}}{local}'

        # 首先尝试直接子元素
        elem = root.find(full_tag)
        if elem is not None and elem.text:
            return elem.text

        # 如果找不到，尝试在所有子元素中查找
        for elem in root.iter(full_tag):
            if elem.text:
                return elem.text

        return None

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """解析 ISO 格式日期时间"""
        if not dt_str:
            return None
        try:
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
            meta.extra['error'] = 'olefile not installed'
        except Exception as e:
            meta.extra['error'] = str(e)

        return meta

    def _extract_ole_guids_ole(self, meta: FileMeta, ole):
        """从 OLE 流提取 GUID"""
        guids = []
        pattern = rb'\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}'

        for stream in ole.listdir():
            try:
                content = ole.openstream(stream).read()
                matches = re.findall(pattern, content)
                guids.extend([m.decode('utf-8') for m in matches])
            except:
                pass

        meta.ole_guids = list(set(guids))
