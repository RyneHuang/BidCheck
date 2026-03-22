"""核心数据模型"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


class TraceType(Enum):
    """痕迹类型 - 6大类25+种"""

    # === 1. 文档身份痕迹 ===
    AUTHOR = "author"
    LAST_MODIFIED_BY = "last_modified_by"
    COMPANY = "company"
    MANAGER = "manager"

    # === 2. 编辑会话痕迹 ===
    RSID = "rsid"
    REVISION_ID = "revision_id"
    EDIT_SESSION = "edit_session"
    VERSION_HISTORY = "version_history"

    # === 3. 设备/环境痕迹 ===
    PRINTER_PATH = "printer_path"
    TEMPLATE_PATH = "template_path"
    COMPUTER_NAME = "computer_name"
    USER_SID = "user_sid"

    # === 4. 隐藏技术痕迹 ===
    OLE_GUID = "ole_guid"
    EMBEDDED_FONT = "embedded_font"
    HIDDEN_TEXT = "hidden_text"
    WATERMARK = "watermark"
    CUSTOM_XML = "custom_xml"

    # === 5. 时间模式痕迹 ===
    CREATE_TIME = "create_time"
    MODIFY_TIME = "modify_time"
    PRINT_TIME = "print_time"
    TIME_PATTERN = "time_pattern"

    # === 6. 内容结构痕迹 ===
    SHARED_STRING = "shared_string"
    STYLE_FINGERPRINT = "style_fingerprint"
    PARAGRAPH_COUNT = "paragraph_count"
    IMAGE_HASH = "image_hash"

    # === 7. PDF专用痕迹 ===
    PDF_PRODUCER = "pdf_producer"
    PDF_CREATOR = "pdf_creator"
    PDF_DOCUMENT_ID = "pdf_document_id"
    XMP_METADATA = "xmp_metadata"


@dataclass
class FileMeta:
    """文件元数据"""
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


@dataclass
class Trace:
    """检测到的可疑痕迹"""
    trace_type: TraceType
    bidder_a: str
    bidder_b: str
    file_a: str
    file_b: str
    value: str
    weight: float
    evidence: str
    raw_data: dict = field(default_factory=dict)


@dataclass
class Report:
    """分析报告"""
    project_name: str
    analysis_time: datetime
    bidders: list[str]

    risk_score: float
    risk_level: str

    traces: list[Trace]
    trace_matrix: dict

    # 可视化数据
    heatmap_data: list[list[float]]
    network_nodes: list[dict]
    network_edges: list[dict]
