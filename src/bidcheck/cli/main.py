"""命令行接口"""

import click
import json
from pathlib import Path
from datetime import datetime
import dataclasses

from ..core.engine import DetectionEngine
from ..report.generator import ReportGenerator


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """
    BidCheck - 围标检测工具

    分析投标文件，检测围标串标风险。
    """
    pass


@cli.command()
@click.argument('input_dir', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), default='report.html',
              help='输出报告路径 (默认: report.html)')
@click.option('--format', '-f', type=click.Choice(['html', 'json']),
              default='html', help='报告格式 (默认: html)')
@click.option('--threshold', '-t', type=float, default=60.0,
              help='风险评分阈值 (默认: 60)')
@click.option('--project', '-p', type=str, default=None,
              help='项目名称')
@click.option('--verbose', '-v', is_flag=True,
              help='详细输出')
def analyze(input_dir: str, output: str, format: str,
            threshold: float, project: str, verbose: bool):
    """
    分析投标文件目录

    INPUT_DIR 应为包含各投标方子目录的根目录。
    例如:
    ├── 投标方A/
    │   ├── 技术标.docx
    │   └── 商务标.xlsx
    └── 投标方B/
        └── ...
    """
    # 扫描投标方目录
    bidder_files = _scan_bidders(input_dir)

    if len(bidder_files) < 2:
        click.secho("错误: 需要至少 2 个投标方目录", fg='red')
        return

    click.echo(f"\n📁 发现 {len(bidder_files)} 个投标方:")
    total_files = 0
    for bidder, files in bidder_files.items():
        click.echo(f"   • {bidder}: {len(files)} 个文件")
        total_files += len(files)

    click.echo(f"   共计 {total_files} 个文件\n")

    if verbose:
        click.echo("文件列表:")
        for bidder, files in bidder_files.items():
            click.echo(f"\n  [{bidder}]")
            for f in files:
                click.echo(f"    - {Path(f).name}")

    # 执行分析
    project_name = project or Path(input_dir).name
    engine = DetectionEngine(project_name)

    click.echo("🔍 正在分析...")
    report = engine.analyze(bidder_files)

    # 生成报告
    generator = ReportGenerator()
    output_path = generator.generate(report, format, output)

    # 输出结果摘要
    click.echo(f"\n{'='*50}")
    click.echo("📊 分析结果")
    click.echo(f"{'='*50}")
    click.echo(f"  项目名称: {report.project_name}")
    click.echo(f"  分析时间: {report.analysis_time.strftime('%Y-%m-%d %H:%M:%S')}")
    click.echo(f"  风险评分: ", nl=False)

    if report.risk_score >= 80:
        click.secho(f"{report.risk_score:.1f}/100", fg='red', nl=False)
        click.secho(f" ({report.risk_level})", fg='red')
    elif report.risk_score >= 60:
        click.secho(f"{report.risk_score:.1f}/100", fg='yellow', nl=False)
        click.secho(f" ({report.risk_level})", fg='yellow')
    else:
        click.secho(f"{report.risk_score:.1f}/100", fg='green', nl=False)
        click.secho(f" ({report.risk_level})", fg='green')

    click.echo(f"  发现痕迹: {len(report.traces)} 条")

    # 显示高风险痕迹
    high_risk = [t for t in report.traces if t.weight >= 0.8]
    if high_risk:
        click.echo(f"\n⚠️  高风险痕迹 ({len(high_risk)} 条):")
        for trace in high_risk[:10]:
            click.secho(f"   • [{trace.trace_type.value}] ", nl=False, fg='yellow')
            click.echo(f"{trace.bidder_a} ↔ {trace.bidder_b}: {trace.evidence}")

    # 风险警告
    if report.risk_score >= threshold:
        click.secho(f"\n⚠️  警告: 风险评分超过阈值 {threshold}!", fg='red', bold=True)

    click.echo(f"\n📄 报告已保存: {output_path}")


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--json', '-j', 'as_json', is_flag=True,
              help='以 JSON 格式输出')
def inspect(file_path: str, as_json: bool):
    """
    检查单个文件的元数据

    用于调试和了解文件包含的元数据信息。
    """
    from ..extractors import get_extractor

    extractor = get_extractor(file_path)
    if not extractor:
        click.secho(f"错误: 不支持的文件格式", fg='red')
        return

    meta = extractor.extract(file_path)

    if as_json:
        def serialize(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif dataclasses.is_dataclass(obj):
                return dataclasses.asdict(obj)
            return str(obj)

        click.echo(json.dumps(dataclasses.asdict(meta), default=serialize, indent=2, ensure_ascii=False))
        return

    # 表格输出
    click.echo(f"\n📄 文件: {file_path}")
    click.echo(f"   哈希: {meta.file_hash}")
    click.echo(f"   大小: {meta.file_size:,} bytes")
    click.echo("-" * 50)

    # 基础元数据
    click.echo("\n📋 基础元数据:")
    for field in ['author', 'last_modified_by', 'company', 'manager']:
        value = getattr(meta, field, None)
        if value:
            click.echo(f"   {field}: {value}")

    for field in ['create_time', 'modify_time']:
        value = getattr(meta, field, None)
        if value:
            click.echo(f"   {field}: {value.strftime('%Y-%m-%d %H:%M:%S')}")

    # Word 特有
    if meta.rsids:
        click.echo(f"\n🔑 RSID (修订保存ID) - {len(meta.rsids)} 个:")
        for rsid in meta.rsids[:10]:
            click.echo(f"   • {rsid}")
        if len(meta.rsids) > 10:
            click.echo(f"   ... 还有 {len(meta.rsids) - 10} 个")

    if meta.template_path:
        click.echo(f"\n📝 模板路径: {meta.template_path}")

    if meta.printer_path:
        click.echo(f"\n🖨️  打印机路径: {meta.printer_path}")

    # OLE GUID
    if meta.ole_guids:
        click.echo(f"\n🔒 OLE GUID - {len(meta.ole_guids)} 个:")
        for guid in meta.ole_guids[:5]:
            click.echo(f"   • {guid}")

    # Excel 特有
    if meta.shared_string_hash:
        click.echo(f"\n📊 共享字符串指纹: {meta.shared_string_hash}")

    if meta.style_fingerprint:
        click.echo(f"   样式指纹: {meta.style_fingerprint}")

    # PDF 特有
    if meta.pdf_producer:
        click.echo(f"\n📕 PDF 信息:")
        click.echo(f"   Producer: {meta.pdf_producer}")
        if meta.pdf_creator:
            click.echo(f"   Creator: {meta.pdf_creator}")
        if meta.pdf_document_id:
            click.echo(f"   Document ID: {meta.pdf_document_id[:32]}...")

    # 嵌入资源
    if meta.image_hashes:
        click.echo(f"\n🖼️  嵌入图片: {len(meta.image_hashes)} 个")

    if meta.embedded_fonts:
        click.echo(f"\n🔤 嵌入字体: {', '.join(meta.embedded_fonts[:5])}")


def _scan_bidders(input_dir: str) -> dict[str, list[str]]:
    """扫描投标方目录"""
    bidder_files = {}
    input_path = Path(input_dir)
    supported_ext = {'.docx', '.doc', '.xlsx', '.xls', '.pdf'}

    for item in input_path.iterdir():
        if item.is_dir():
            files = []
            for ext in supported_ext:
                files.extend([str(f) for f in item.rglob(f'*{ext}')])
            if files:
                bidder_files[item.name] = sorted(files)

    return bidder_files


if __name__ == '__main__':
    cli()
