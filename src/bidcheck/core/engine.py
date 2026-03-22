"""围标检测引擎"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import FileMeta, Trace, Report
from .weights import get_weight


class DetectionEngine:
    """围标检测引擎"""

    def __init__(self, project_name: str = "未命名项目"):
        self.project_name = project_name
        self._analyzer = None  # 延迟导入

    @property
    def analyzer(self):
        """延迟加载分析器"""
        if self._analyzer is None:
            from ..analyzers import SimilarityAnalyzer
            self._analyzer = SimilarityAnalyzer()
        return self._analyzer

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
        bidders = list(bidder_files.keys())
        heatmap = self._build_heatmap(all_traces, bidders)
        network = self._build_network(all_traces, bidders)

        return Report(
            project_name=self.project_name,
            analysis_time=datetime.now(),
            bidders=bidders,
            risk_score=risk_score,
            risk_level=risk_level,
            traces=all_traces,
            trace_matrix=self._build_trace_matrix(all_traces),
            heatmap_data=heatmap,
            network_nodes=network['nodes'],
            network_edges=network['edges'],
        )

    def _extract_all(self, bidder_files: dict) -> dict[str, list[FileMeta]]:
        """提取所有文件元数据"""
        from ..extractors import get_extractor

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

    def _build_trace_matrix(self, traces: list) -> dict:
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
