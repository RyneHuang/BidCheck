"""痕迹权重配置"""

from .models import TraceType

# 基于可伪造难度划分权重
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
    TraceType.TIME_PATTERN: 0.35,
}


def get_weight(trace_type: TraceType) -> float:
    """获取痕迹类型权重"""
    return TRACE_WEIGHTS.get(trace_type, 0.5)
