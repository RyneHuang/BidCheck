"""相似度分析器"""

import os
from typing import Optional

from ..core.models import FileMeta, Trace, TraceType
from ..core.weights import get_weight


class SimilarityAnalyzer:
    """相似度分析器"""

    def compare(self, meta_a: FileMeta, meta_b: FileMeta,
                bidder_a: str, bidder_b: str) -> list[Trace]:
        """
        对比两个文件，返回发现的痕迹
        """
        traces = []

        # === 高权重痕迹 ===
        traces.extend(self._compare_rsids(meta_a, meta_b, bidder_a, bidder_b))
        traces.extend(self._compare_ole_guids(meta_a, meta_b, bidder_a, bidder_b))
        traces.extend(self._compare_shared_strings(meta_a, meta_b, bidder_a, bidder_b))
        traces.extend(self._compare_style_fingerprint(meta_a, meta_b, bidder_a, bidder_b))
        traces.extend(self._compare_pdf_id(meta_a, meta_b, bidder_a, bidder_b))

        # === 中高权重痕迹 ===
        traces.extend(self._compare_printer_path(meta_a, meta_b, bidder_a, bidder_b))
        traces.extend(self._compare_template_path(meta_a, meta_b, bidder_a, bidder_b))
        traces.extend(self._compare_image_hashes(meta_a, meta_b, bidder_a, bidder_b))

        # === 中等权重痕迹 ===
        traces.extend(self._compare_company(meta_a, meta_b, bidder_a, bidder_b))
        traces.extend(self._compare_pdf_producer(meta_a, meta_b, bidder_a, bidder_b))

        # === 低权重痕迹 ===
        traces.extend(self._compare_author(meta_a, meta_b, bidder_a, bidder_b))
        traces.extend(self._compare_time_pattern(meta_a, meta_b, bidder_a, bidder_b))

        return traces

    def _compare_rsids(self, meta_a: FileMeta, meta_b: FileMeta,
                       bidder_a: str, bidder_b: str) -> list[Trace]:
        """对比 RSID"""
        traces = []
        if not meta_a.rsids or not meta_b.rsids:
            return traces

        common_rsids = set(meta_a.rsids) & set(meta_b.rsids)

        for rsid in common_rsids:
            traces.append(Trace(
                trace_type=TraceType.RSID,
                bidder_a=bidder_a,
                bidder_b=bidder_b,
                file_a=meta_a.file_path,
                file_b=meta_b.file_path,
                value=rsid,
                weight=get_weight(TraceType.RSID),
                evidence=f"发现相同的编辑会话 ID (RSID): {rsid}，表明文档可能来自同一编辑环境",
                raw_data={'rsid': rsid}
            ))

        return traces

    def _compare_ole_guids(self, meta_a: FileMeta, meta_b: FileMeta,
                           bidder_a: str, bidder_b: str) -> list[Trace]:
        """对比 OLE GUID"""
        traces = []
        if not meta_a.ole_guids or not meta_b.ole_guids:
            return traces

        common_guids = set(meta_a.ole_guids) & set(meta_b.ole_guids)

        for guid in common_guids:
            traces.append(Trace(
                trace_type=TraceType.OLE_GUID,
                bidder_a=bidder_a,
                bidder_b=bidder_b,
                file_a=meta_a.file_path,
                file_b=meta_b.file_path,
                value=guid,
                weight=get_weight(TraceType.OLE_GUID),
                evidence=f"发现相同的 OLE 对象 GUID: {guid}，极可能来自同一来源",
                raw_data={'guid': guid}
            ))

        return traces

    def _compare_shared_strings(self, meta_a: FileMeta, meta_b: FileMeta,
                                 bidder_a: str, bidder_b: str) -> list[Trace]:
        """对比 Excel 共享字符串指纹"""
        traces = []

        if (meta_a.shared_string_hash and meta_b.shared_string_hash and
            meta_a.shared_string_hash == meta_b.shared_string_hash):
            traces.append(Trace(
                trace_type=TraceType.SHARED_STRING,
                bidder_a=bidder_a,
                bidder_b=bidder_b,
                file_a=meta_a.file_path,
                file_b=meta_b.file_path,
                value=meta_a.shared_string_hash[:16],
                weight=get_weight(TraceType.SHARED_STRING),
                evidence="Excel 文档具有相同的共享字符串指纹，内容结构高度相似",
                raw_data={'hash': meta_a.shared_string_hash}
            ))

        return traces

    def _compare_style_fingerprint(self, meta_a: FileMeta, meta_b: FileMeta,
                                    bidder_a: str, bidder_b: str) -> list[Trace]:
        """对比样式指纹"""
        traces = []

        if (meta_a.style_fingerprint and meta_b.style_fingerprint and
            meta_a.style_fingerprint == meta_b.style_fingerprint):
            traces.append(Trace(
                trace_type=TraceType.STYLE_FINGERPRINT,
                bidder_a=bidder_a,
                bidder_b=bidder_b,
                file_a=meta_a.file_path,
                file_b=meta_b.file_path,
                value=meta_a.style_fingerprint[:16],
                weight=get_weight(TraceType.STYLE_FINGERPRINT),
                evidence="文档具有相同的样式指纹，可能使用同一模板或由同一人制作",
                raw_data={'hash': meta_a.style_fingerprint}
            ))

        return traces

    def _compare_pdf_id(self, meta_a: FileMeta, meta_b: FileMeta,
                         bidder_a: str, bidder_b: str) -> list[Trace]:
        """对比 PDF 文档 ID"""
        traces = []

        if (meta_a.pdf_document_id and meta_b.pdf_document_id and
            meta_a.pdf_document_id == meta_b.pdf_document_id):
            value = meta_a.pdf_document_id[:32] if len(meta_a.pdf_document_id) > 32 else meta_a.pdf_document_id
            traces.append(Trace(
                trace_type=TraceType.PDF_DOCUMENT_ID,
                bidder_a=bidder_a,
                bidder_b=bidder_b,
                file_a=meta_a.file_path,
                file_b=meta_b.file_path,
                value=value,
                weight=get_weight(TraceType.PDF_DOCUMENT_ID),
                evidence="PDF 文档具有相同的文档 ID，可能来自同一来源",
                raw_data={'document_id': meta_a.pdf_document_id}
            ))

        return traces

    def _compare_printer_path(self, meta_a: FileMeta, meta_b: FileMeta,
                               bidder_a: str, bidder_b: str) -> list[Trace]:
        """对比打印机路径"""
        traces = []

        if (meta_a.printer_path and meta_b.printer_path and
            meta_a.printer_path == meta_b.printer_path):
            traces.append(Trace(
                trace_type=TraceType.PRINTER_PATH,
                bidder_a=bidder_a,
                bidder_b=bidder_b,
                file_a=meta_a.file_path,
                file_b=meta_b.file_path,
                value=meta_a.printer_path,
                weight=get_weight(TraceType.PRINTER_PATH),
                evidence=f"文档使用相同的打印机路径: {meta_a.printer_path}",
                raw_data={'printer_path': meta_a.printer_path}
            ))

        return traces

    def _compare_template_path(self, meta_a: FileMeta, meta_b: FileMeta,
                                bidder_a: str, bidder_b: str) -> list[Trace]:
        """对比模板路径"""
        traces = []

        if (meta_a.template_path and meta_b.template_path and
            self._is_same_template(meta_a.template_path, meta_b.template_path)):
            traces.append(Trace(
                trace_type=TraceType.TEMPLATE_PATH,
                bidder_a=bidder_a,
                bidder_b=bidder_b,
                file_a=meta_a.file_path,
                file_b=meta_b.file_path,
                value=meta_a.template_path,
                weight=get_weight(TraceType.TEMPLATE_PATH),
                evidence=f"文档使用相同的模板: {meta_a.template_path}",
                raw_data={'template_path': meta_a.template_path}
            ))

        return traces

    def _compare_image_hashes(self, meta_a: FileMeta, meta_b: FileMeta,
                               bidder_a: str, bidder_b: str) -> list[Trace]:
        """对比嵌入图片哈希"""
        traces = []

        if not meta_a.image_hashes or not meta_b.image_hashes:
            return traces

        common_images = set(meta_a.image_hashes) & set(meta_b.image_hashes)

        for img_hash in common_images:
            traces.append(Trace(
                trace_type=TraceType.IMAGE_HASH,
                bidder_a=bidder_a,
                bidder_b=bidder_b,
                file_a=meta_a.file_path,
                file_b=meta_b.file_path,
                value=img_hash[:16],
                weight=get_weight(TraceType.IMAGE_HASH),
                evidence=f"文档包含相同的嵌入图片 (MD5: {img_hash[:16]}...)",
                raw_data={'image_hash': img_hash}
            ))

        return traces

    def _compare_company(self, meta_a: FileMeta, meta_b: FileMeta,
                         bidder_a: str, bidder_b: str) -> list[Trace]:
        """对比公司信息"""
        traces = []

        if (meta_a.company and meta_b.company and
            meta_a.company.strip() and
            meta_a.company == meta_b.company):
            traces.append(Trace(
                trace_type=TraceType.COMPANY,
                bidder_a=bidder_a,
                bidder_b=bidder_b,
                file_a=meta_a.file_path,
                file_b=meta_b.file_path,
                value=meta_a.company,
                weight=get_weight(TraceType.COMPANY),
                evidence=f"文档的公司信息相同: {meta_a.company}",
                raw_data={'company': meta_a.company}
            ))

        return traces

    def _compare_pdf_producer(self, meta_a: FileMeta, meta_b: FileMeta,
                               bidder_a: str, bidder_b: str) -> list[Trace]:
        """对比 PDF 生成器"""
        traces = []

        if (meta_a.pdf_producer and meta_b.pdf_producer and
            meta_a.pdf_producer == meta_b.pdf_producer):
            traces.append(Trace(
                trace_type=TraceType.PDF_PRODUCER,
                bidder_a=bidder_a,
                bidder_b=bidder_b,
                file_a=meta_a.file_path,
                file_b=meta_b.file_path,
                value=meta_a.pdf_producer,
                weight=get_weight(TraceType.PDF_PRODUCER),
                evidence=f"PDF 使用相同的生成器: {meta_a.pdf_producer}",
                raw_data={'producer': meta_a.pdf_producer}
            ))

        return traces

    def _compare_author(self, meta_a: FileMeta, meta_b: FileMeta,
                        bidder_a: str, bidder_b: str) -> list[Trace]:
        """对比作者信息"""
        traces = []

        if (meta_a.author and meta_b.author and
            meta_a.author.strip() and
            meta_a.author == meta_b.author):
            traces.append(Trace(
                trace_type=TraceType.AUTHOR,
                bidder_a=bidder_a,
                bidder_b=bidder_b,
                file_a=meta_a.file_path,
                file_b=meta_b.file_path,
                value=meta_a.author,
                weight=get_weight(TraceType.AUTHOR),
                evidence=f"文档作者相同: {meta_a.author}",
                raw_data={'author': meta_a.author}
            ))

        return traces

    def _compare_time_pattern(self, meta_a: FileMeta, meta_b: FileMeta,
                              bidder_a: str, bidder_b: str) -> list[Trace]:
        """检测异常时间模式"""
        traces = []

        if meta_a.modify_time and meta_b.modify_time:
            delta = abs((meta_a.modify_time - meta_b.modify_time).total_seconds())
            if 0 < delta < 60:
                traces.append(Trace(
                    trace_type=TraceType.TIME_PATTERN,
                    bidder_a=bidder_a,
                    bidder_b=bidder_b,
                    file_a=meta_a.file_path,
                    file_b=meta_b.file_path,
                    value=f"{delta:.1f}s",
                    weight=get_weight(TraceType.TIME_PATTERN),
                    evidence=f"两文档修改时间相差仅 {delta:.1f} 秒，可能同时编辑",
                    raw_data={'delta_seconds': delta}
                ))

        return traces

    @staticmethod
    def _is_same_template(path_a: str, path_b: str) -> bool:
        """判断是否为同一模板"""
        name_a = os.path.basename(path_a).lower()
        name_b = os.path.basename(path_b).lower()
        return name_a == name_b and name_a != 'normal.dotm'
