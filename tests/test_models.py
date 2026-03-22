"""测试核心数据模型"""

import pytest
from datetime import datetime

from bidcheck.core.models import TraceType, FileMeta, Trace, Report
from bidcheck.core.weights import get_weight, TRACE_WEIGHTS


class TestTraceType:
    """测试 TraceType 枚举"""

    def test_trace_types_exist(self):
        """测试所有痕迹类型都存在"""
        assert TraceType.AUTHOR.value == "author"
        assert TraceType.RSID.value == "rsid"
        assert TraceType.OLE_GUID.value == "ole_guid"
        assert TraceType.COMPANY.value == "company"
        assert TraceType.SHARED_STRING.value == "shared_string"

    def test_high_weight_traces(self):
        """测试高权重痕迹"""
        assert get_weight(TraceType.OLE_GUID) >= 0.85
        assert get_weight(TraceType.RSID) >= 0.85
        assert get_weight(TraceType.PDF_DOCUMENT_ID) >= 0.85


class TestWeights:
    """测试权重配置"""

    def test_weight_range(self):
        """测试权重范围"""
        for trace_type, weight in TRACE_WEIGHTS.items():
            assert 0 < weight <= 1, f"{trace_type} 权重 {weight} 不在 0-1 范围内"

    def test_get_weight_default(self):
        """测试默认权重"""
        # 创建一个临时的枚举值测试
        assert get_weight(TraceType.AUTHOR) == TRACE_WEIGHTS[TraceType.AUTHOR]


class TestFileMeta:
    """测试 FileMeta 数据类"""

    def test_create_basic(self):
        """测试创建基本元数据"""
        meta = FileMeta(
            file_path="/test.docx",
            file_hash="abc123",
            file_size=1000
        )
        assert meta.file_path == "/test.docx"
        assert meta.author is None
        assert meta.rsids == []

    def test_create_with_author(self):
        """测试创建带作者的元数据"""
        meta = FileMeta(
            file_path="/test.docx",
            file_hash="abc123",
            file_size=1000,
            author="张三"
        )
        assert meta.author == "张三"


class TestTrace:
    """测试 Trace 数据类"""

    def test_create_trace(self):
        """测试创建痕迹"""
        trace = Trace(
            trace_type=TraceType.RSID,
            bidder_a="投标方A",
            bidder_b="投标方B",
            file_a="/a.docx",
            file_b="/b.docx",
            value="00A1B2C3",
            weight=0.9,
            evidence="相同的 RSID"
        )
        assert trace.trace_type == TraceType.RSID
        assert trace.bidder_a == "投标方A"
        assert trace.weight == 0.9


class TestReport:
    """测试 Report 数据类"""

    def test_create_report(self):
        """测试创建报告"""
        report = Report(
            project_name="测试项目",
            analysis_time=datetime.now(),
            bidders=["A", "B"],
            risk_score=50.0,
            risk_level="medium",
            traces=[],
            trace_matrix={},
            heatmap_data=[[0, 50], [50, 0]],
            network_nodes=[{"id": "A", "name": "A"}, {"id": "B", "name": "B"}],
            network_edges=[]
        )
        assert report.project_name == "测试项目"
        assert report.risk_score == 50.0
        assert report.risk_level == "medium"
