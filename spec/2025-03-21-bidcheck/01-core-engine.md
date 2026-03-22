# Phase 1: 核心引擎与数据模型

## 概述

本阶段实现核心数据模型和检测引擎框架，定义系统的数据结构和核心流程。

## 数据模型

### TraceType 枚举

定义 6 大类 25+ 种可检测的痕迹类型：

```python
# src/bidcheck/core/models.py

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


class TraceType(Enum):
    """痕迹类型 - 6大类25+种"""

    # === 1. 文档身份痕迹 ===
    AUTHOR = "author"                    # 作者
    LAST_MODIFIED_BY = "last_modified_by" # 最后修改人
    COMPANY = "company"                  # 公司名称
    MANAGER = "manager"                  # 管理者

    # === 2. 编辑会话痕迹 ===
    RSID = "rsid"                        # Word 修订保存ID (关键!)
    REVISION_ID = "revision_id"          # 通用修订ID
    EDIT_SESSION = "edit_session"        # 编辑会话指纹
    VERSION_HISTORY = "version_history"  # 版本历史

    # === 3. 设备/环境痕迹 ===
    PRINTER_PATH = "printer_path"        # 最后打印路径
    TEMPLATE_PATH = "template_path"      # 模板路径
    COMPUTER_NAME = "computer_name"      # 计算机名 (OLE中)
    USER_SID = "user_sid"                # 用户安全标识符

    # === 4. 隐藏技术痕迹 ===
    OLE_GUID = "ole_guid"                # OLE 对象 GUID
    EMBEDDED_FONT = "embedded_font"      # 嵌入字体指纹
    HIDDEN_TEXT = "hidden_text"          # 隐藏文本
    WATERMARK = "watermark"              # 水印
    CUSTOM_XML = "custom_xml"            # 自定义XML部件

    # === 5. 时间模式痕迹 ===
    CREATE_TIME = "create_time"          # 创建时间
    MODIFY_TIME = "modify_time"          # 修改时间
    PRINT_TIME = "print_time"            # 打印时间
    TIME_PATTERN = "time_pattern"        # 异常时间模式

    # === 6. 内容结构痕迹 ===
    SHARED_STRING = "shared_string"      # Excel共享字符串指纹
    STYLE_FINGERPRINT = "style_fingerprint"  # 样式指纹
    PARAGRAPH_COUNT = "paragraph_count"  # 段落数结构
    IMAGE_HASH = "image_hash"            # 嵌入图片哈希

    # === 7. PDF专用痕迹 ===
    PDF_PRODUCER = "pdf_producer"        # PDF生成器
    PDF_CREATOR = "pdf_creator"          # 创建工具
    PDF_DOCUMENT_ID = "pdf_document_id"  # 文档ID
    XMP_METADATA = "xmp_metadata"        # XMP元数据指纹
```

### FileMeta 数据类

```python
@dataclass
class FileMeta:
    """文件元数据 - 扩展版"""
    file_path: str
    file_hash: str
    file_size: int

    # === 基础元数据 ===
    author: Optional[str] = None
    last_modified_by: Optional[str] = None
    company: Optional[str] = None
    manager: Optional[str] = None
    create_time: Optional[datetime] = None
    modify_time: Optional[datetime] = None
    print_time: Optional[datetime] = None

    # === Word 专用 ===
    rsids: list[str] = field(default_factory=list)
    revision_id: Optional[str] = None
    template_path: Optional[str] = None
    printer_path: Optional[str] = None

    # === Excel 专用 ===
    shared_string_hash: Optional[str] = None
    style_fingerprint: Optional[str] = None
    sheet_count: int = 0

    # === PDF 专用 ===
    pdf_producer: Optional[str] = None
    pdf_creator: Optional[str] = None
    pdf_document_id: Optional[str] = None
    xmp_metadata_hash: Optional[str] = None

    # === OLE/隐藏信息 ===
    ole_guids: list[str] = field(default_factory=list)
    computer_name: Optional[str] = None
    user_sid: Optional[str] = None
    embedded_fonts: list[str] = field(default_factory=list)
    hidden_texts: list[str] = field(default_factory=list)
    custom_props: dict[str, str] = field(default_factory=dict)

    # === 内容指纹 ===
    image_hashes: list[str] = field(default_factory=list)
    paragraph_structure: Optional[str] = None

    # === 扩展 ===
    extra: dict = field(default_factory=dict)
```

### Trace 数据类

```python
@dataclass
class Trace:
    """检测到的可疑痕迹"""
    trace_type: TraceType           # 痕迹类型
    bidder_a: str                   # 投标方 A
    bidder_b: str                   # 投标方 B
    file_a: str                     # 文件 A 路径
    file_b: str                     # 文件 B 路径
    value: str                      # 匹配的值
    weight: float                   # 权重 (0-1)
    evidence: str                   # 证据描述
    raw_data: dict = field(default_factory=dict)  # 原始数据
```

### Report 数据类

```python
@dataclass
class Report:
    """分析报告"""
    project_name: str
    analysis_time: datetime
    bidders: list[str]

    risk_score: float               # 0-100 风险评分
    risk_level: str                 # low/medium/high/critical

    traces: list[Trace]             # 所有发现的痕迹
    trace_matrix: dict              # 投标方两两对比的痕迹矩阵

    # 可视化数据
    heatmap_data: list[list[float]]
    network_nodes: list[dict]
    network_edges: list[dict]
```

### 权重配置

```python
# src/bidcheck/core/weights.py

from .models import TraceType

TRACE_WEIGHTS = {
    # 高权重 - 极难伪造 (0.85-0.98)
    TraceType.OLE_GUID: 0.95,
    TraceType.RSID: 0.90,
    TraceType.USER_SID: 0.92,
    TraceType.EMBEDDED_FONT: 0.88,
    TraceType.PDF_DOCUMENT_ID: 0.85,
    TraceType.SHARED_STRING: 0.85,
    TraceType.STYLE_FINGERPRINT: 0.82,

    # 中高权重 - 较难伪造 (0.70-0.84)
    TraceType.PRINTER_PATH: 0.80,
    TraceType.TEMPLATE_PATH: 0.78,
    TraceType.COMPUTER_NAME: 0.75,
    TraceType.CUSTOM_XML: 0.72,
    TraceType.IMAGE_HASH: 0.70,

    # 中等权重 - 可修改但常被忽略 (0.50-0.69)
    TraceType.COMPANY: 0.65,
    TraceType.MANAGER: 0.60,
    TraceType.VERSION_HISTORY: 0.58,
    TraceType.WATERMARK: 0.55,
    TraceType.PDF_PRODUCER: 0.55,

    # 低权重 - 容易修改 (0.30-0.49)
    TraceType.AUTHOR: 0.45,
    TraceType.LAST_MODIFIED_BY: 0.42,
    TraceType.CREATE_TIME: 0.35,
    TraceType.MODIFY_TIME: 0.32,
}

def get_weight(trace_type: TraceType) -> float:
    return TRACE_WEIGHTS.get(trace_type, 0.5)
```

## 检测引擎

```python
# src/bidcheck/core/engine.py

from datetime import datetime
from pathlib import Path
from typing import Optional
from ..extractors import get_extractor
from ..analyzers import SimilarityAnalyzer
from .models import FileMeta, Trace, Report
from .weights import get_weight


class DetectionEngine:
    """围标检测引擎"""

    def __init__(self, project_name: str = "未命名项目"):
        self.project_name = project_name
        self.analyzer = SimilarityAnalyzer()

    def analyze(self, bidder_files: dict[str, list[str]]) -> Report:
        """
        主分析入口

        Args:
            bidder_files: {"投标方A": ["file1.docx", ...], ...}

        Returns:
            Report: 分析报告
        """
        # 1. 提取所有文件元数据
        all_metas = self._extract_all(bidder_files)

        # 2. 两两对比分析
        all_traces = self._compare_all(all_metas, bidder_files)

        # 3. 计算风险评分
        risk_score = self._calculate_risk(all_traces)
        risk_level = self._get_risk_level(risk_score)

        # 4. 生成可视化数据
        heatmap = self._build_heatmap(all_traces, list(bidder_files.keys()))
        network = self._build_network(all_traces, list(bidder_files.keys()))

        return Report(
            project_name=self.project_name,
            analysis_time=datetime.now(),
            bidders=list(bidder_files.keys()),
            risk_score=risk_score,
            risk_level=risk_level,
            traces=all_traces,
            trace_matrix=self._build_trace_matrix(all_traces, bidder_files),
            heatmap_data=heatmap,
            network_nodes=network['nodes'],
            network_edges=network['edges'],
        )

    def _extract_all(self, bidder_files: dict) -> dict[str, list[FileMeta]]:
        """提取所有文件元数据"""
        result = {}
        for bidder, files in bidder_files.items():
            metas = []
            for file_path in files:
                extractor = get_extractor(file_path)
                if extractor:
                    meta = extractor.extract(file_path)
                    metas.append(meta)
            result[bidder] = metas
        return result

    def _compare_all(self, all_metas: dict, bidder_files: dict) -> list[Trace]:
        """两两对比所有投标方"""
        traces = []
        bidders = list(bidder_files.keys())

        for i, bidder_a in enumerate(bidders):
            for bidder_b in bidders[i+1:]:
                for meta_a in all_metas[bidder_a]:
                    for meta_b in all_metas[bidder_b]:
                        new_traces = self.analyzer.compare(
                            meta_a, meta_b, bidder_a, bidder_b
                        )
                        traces.extend(new_traces)

        return traces

    def _calculate_risk(self, traces: list[Trace]) -> float:
        """计算风险评分 (0-100)"""
        if not traces:
            return 0.0

        # 加权求和
        total_weight = sum(t.weight for t in traces)
        # 归一化
        max_weight = max(get_weight(t.trace_type) for t in traces)
        normalized = total_weight / (len(traces) * max_weight) if traces else 0

        return min(100, normalized * 100)

    def _get_risk_level(self, score: float) -> str:
        """根据评分确定风险等级"""
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 40:
            return "medium"
        else:
            return "low"

    def _build_heatmap(self, traces: list, bidders: list) -> list[list[float]]:
        """构建热力图数据"""
        n = len(bidders)
        matrix = [[0.0] * n for _ in range(n)]
        bidder_idx = {b: i for i, b in enumerate(bidders)}

        for trace in traces:
            i, j = bidder_idx[trace.bidder_a], bidder_idx[trace.bidder_b]
            matrix[i][j] += trace.weight
            matrix[j][i] += trace.weight

        # 归一化
        max_val = max(max(row) for row in matrix) if traces else 1
        if max_val > 0:
            matrix = [[v / max_val * 100 for v in row] for row in matrix]

        return matrix

    def _build_network(self, traces: list, bidders: list) -> dict:
        """构建关系网络图数据"""
        nodes = [{"id": b, "name": b} for b in bidders]
        edges = []

        # 按投标方对聚合
        pair_traces = {}
        for trace in traces:
            key = tuple(sorted([trace.bidder_a, trace.bidder_b]))
            if key not in pair_traces:
                pair_traces[key] = []
            pair_traces[key].append(trace)

        for (a, b), pair_trace_list in pair_traces.items():
            total_weight = sum(t.weight for t in pair_trace_list)
            edges.append({
                "source": a,
                "target": b,
                "weight": total_weight,
                "traces": [t.trace_type.value for t in pair_trace_list]
            })

        return {"nodes": nodes, "edges": edges}

    def _build_trace_matrix(self, traces: list, bidder_files: dict) -> dict:
        """构建痕迹矩阵"""
        matrix = {}
        for trace in traces:
            key = f"{trace.bidder_a}::{trace.bidder_b}"
            if key not in matrix:
                matrix[key] = []
            matrix[key].append({
                "type": trace.trace_type.value,
                "value": trace.value,
                "weight": trace.weight,
                "evidence": trace.evidence
            })
        return matrix
```

## 验收标准

- [ ] TraceType 枚举包含所有 25+ 种痕迹类型
- [ ] FileMeta 可存储所有格式的元数据
- [ ] 权重配置合理，高权重 > 0.85，低权重 < 0.5
- [ ] DetectionEngine 可完成分析流程
- [ ] 风险评分范围正确 (0-100)
- [ ] 单元测试覆盖率 > 80%
