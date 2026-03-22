"""报告生成器"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.models import Report


class ReportGenerator:
    """报告生成器"""

    def generate(self, report: Report, format: str, output_path: str) -> str:
        """
        生成报告

        Args:
            report: 分析报告
            format: 格式 (html/json)
            output_path: 输出路径

        Returns:
            实际输出路径
        """
        if format == 'json':
            return self._generate_json(report, output_path)
        elif format == 'html':
            return self._generate_html(report, output_path)
        else:
            raise ValueError(f"不支持的格式: {format}")

    def _generate_json(self, report: Report, output_path: str) -> str:
        """生成 JSON 报告"""
        data = {
            'project_name': report.project_name,
            'analysis_time': report.analysis_time.isoformat(),
            'bidders': report.bidders,
            'risk_score': report.risk_score,
            'risk_level': report.risk_level,
            'traces': [
                {
                    'type': t.trace_type.value,
                    'bidder_a': t.bidder_a,
                    'bidder_b': t.bidder_b,
                    'value': t.value,
                    'weight': t.weight,
                    'evidence': t.evidence
                }
                for t in report.traces
            ],
            'trace_matrix': report.trace_matrix,
            'heatmap_data': report.heatmap_data,
            'network': {
                'nodes': report.network_nodes,
                'edges': report.network_edges
            }
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return output_path

    def _generate_html(self, report: Report, output_path: str) -> str:
        """生成 HTML 报告"""
        html = self._get_html_template().format(
            project_name=report.project_name,
            analysis_time=report.analysis_time.strftime('%Y-%m-%d %H:%M:%S'),
            risk_score=report.risk_score,
            risk_level=report.risk_level.upper(),
            risk_color=self._get_risk_color(report.risk_level),
            bidders=', '.join(report.bidders),
            bidders_count=len(report.bidders),
            traces_count=len(report.traces),
            traces_table=self._generate_traces_table(report.traces),
            heatmap_json=json.dumps(report.heatmap_data),
            network_json=json.dumps({
                'nodes': report.network_nodes,
                'edges': report.network_edges
            })
        )

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        return output_path

    def _get_risk_color(self, level: str) -> str:
        """获取风险等级颜色"""
        colors = {
            'low': '#67C23A',
            'medium': '#409EFF',
            'high': '#E6A23C',
            'critical': '#F56C6C'
        }
        return colors.get(level, '#909399')

    def _generate_traces_table(self, traces) -> str:
        """生成痕迹表格 HTML"""
        rows = []
        for t in traces:
            rows.append(f"""
                <tr>
                    <td><span class="badge">{t.trace_type.value}</span></td>
                    <td>{t.bidder_a} ↔ {t.bidder_b}</td>
                    <td>{t.value}</td>
                    <td>{t.weight:.2f}</td>
                    <td>{t.evidence}</td>
                </tr>
            """)

        return '\n'.join(rows)

    def _get_html_template(self) -> str:
        """获取 HTML 模板"""
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>围标检测报告 - {project_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 20px; }}
        .header h1 {{ font-size: 24px; margin-bottom: 10px; }}
        .risk-card {{ background: {risk_color}; color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; display: flex; align-items: center; gap: 30px; }}
        .risk-score {{ font-size: 48px; font-weight: bold; }}
        .risk-level {{ font-size: 24px; }}
        .card {{ background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); }}
        .card h2 {{ font-size: 18px; margin-bottom: 15px; color: #303133; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ebeef5; }}
        th {{ background: #f5f7fa; font-weight: 600; }}
        .badge {{ background: #409eff; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; }}
        .info-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; }}
        .info-item {{ background: #f5f7fa; padding: 15px; border-radius: 8px; }}
        .info-label {{ font-size: 12px; color: #909399; margin-bottom: 5px; }}
        .info-value {{ font-size: 18px; font-weight: 600; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>围标检测报告</h1>
            <p>{project_name}</p>
        </div>

        <div class="risk-card">
            <div>
                <div class="risk-score">{risk_score:.1f}</div>
                <div class="risk-level">{risk_level}</div>
            </div>
            <div style="flex: 1;">
                <div class="info-grid">
                    <div class="info-item" style="background: rgba(255,255,255,0.2); color: white;">
                        <div class="info-label" style="color: rgba(255,255,255,0.8);">投标方数量</div>
                        <div class="info-value">{bidders_count}</div>
                    </div>
                    <div class="info-item" style="background: rgba(255,255,255,0.2); color: white;">
                        <div class="info-label" style="color: rgba(255,255,255,0.8);">发现痕迹</div>
                        <div class="info-value">{traces_count}</div>
                    </div>
                    <div class="info-item" style="background: rgba(255,255,255,0.2); color: white;">
                        <div class="info-label" style="color: rgba(255,255,255,0.8);">分析时间</div>
                        <div class="info-value" style="font-size: 14px;">{analysis_time}</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>可疑痕迹详情 ({traces_count} 条)</h2>
            <table>
                <thead>
                    <tr>
                        <th>类型</th>
                        <th>投标方</th>
                        <th>匹配值</th>
                        <th>权重</th>
                        <th>证据</th>
                    </tr>
                </thead>
                <tbody>
                    {traces_table}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>'''
