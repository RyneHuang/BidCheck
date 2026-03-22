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

            # 从文档设置中提取
            for rsid_elem in root.iter(f'{ns}rsid'):
                for attr in ['{ns}rsidRoot', '{ns}rsid']:
                    val = rsid_elem.get(attr)
                    if val:
                        rsids.add(val)
                val = rsid_elem.get(f'{ns}val')
                if val:
                    rsids.add(val)

            # 从段落中提取
            for p_elem in root.iter(f'{ns}p'):
                pPr = p_elem.find(f'{ns}pPr')
                if pPr is not None:
                    for rsid in pPr.iter(f'{ns}rsid'):
                        val = rsid.get(f'{ns}val')
                        if val:
                            rsids.add(val)

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
