# Phase 4: CLI 与 API 接口

## 概述

本阶段实现命令行接口 (CLI) 和 REST API 服务，提供用户交互入口。

## 依赖

```toml
[project.dependencies]
click = ">=8.1.0"
fastapi = ">=0.109.0"
uvicorn = ">=0.27.0"
python-multipart = ">=0.0.6"
```

## CLI 实现

```python
# src/bidcheck/cli/main.py

import click
import json
from pathlib import Path
from datetime import datetime
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
@click.option('--format', '-f', type=click.Choice(['html', 'json', 'pdf']),
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
    with click.progressbar(length=100, label='进度') as bar:
        report = engine.analyze(bidder_files)
        bar.update(100)

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
        # JSON 输出
        import dataclasses
        from datetime import datetime

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
```

## FastAPI 实现

```python
# src/bidcheck/api/main.py

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uuid
import os
import shutil
import asyncio
from pathlib import Path

app = FastAPI(
    title="BidCheck API",
    description="围标检测服务 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 任务存储 (生产环境应使用 Redis)
tasks: dict = {}


# === 数据模型 ===

class TaskCreateResponse(BaseModel):
    """任务创建响应"""
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: str
    progress: int
    project_name: Optional[str] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    traces_count: Optional[int] = None
    bidders_count: Optional[int] = None
    error: Optional[str] = None
    download_url: Optional[str] = None


class TraceDetail(BaseModel):
    """痕迹详情"""
    type: str
    bidder_a: str
    bidder_b: str
    value: str
    weight: float
    evidence: str


class ReportDetailResponse(BaseModel):
    """报告详情响应"""
    task_id: str
    project_name: str
    analysis_time: str
    risk_score: float
    risk_level: str
    bidders: list[str]
    traces: list[TraceDetail]
    trace_matrix: dict
    heatmap_data: list[list[float]]
    network_nodes: list[dict]
    network_edges: list[dict]


# === API 端点 ===

@app.get("/")
async def root():
    """API 根路径"""
    return {
        "name": "BidCheck API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.post("/api/v1/analyze", response_model=TaskCreateResponse)
async def create_analysis(
    background_tasks: BackgroundTasks,
    project_name: str = Query(..., description="项目名称"),
    files: list[UploadFile] = File(..., description="投标文件"),
    bidder_names: str = Query(..., description="投标方名称列表 (JSON数组)")
):
    """
    上传文件并开始分析

    bidder_names 格式: ["投标方A", "投标方B", "投标方C"]
    文件应按投标方顺序上传，每个投标方可以有多个文件
    """
    import json

    task_id = str(uuid.uuid4())
    task_dir = Path(f"/tmp/bidcheck/{task_id}")
    task_dir.mkdir(parents=True, exist_ok=True)

    try:
        names = json.loads(bidder_names)
    except:
        raise HTTPException(status_code=400, detail="bidder_names 格式错误")

    # 分配文件到投标方 (简化逻辑：按顺序分配)
    bidder_files = {name: [] for name in names}
    file_idx = 0
    for upload_file in files:
        bidder_name = names[min(file_idx, len(names) - 1)]
        file_path = task_dir / f"{bidder_name}_{upload_file.filename}"
        with open(file_path, "wb") as f:
            shutil.copyfileobj(upload_file.file, f)
        bidder_files[bidder_name].append(str(file_path))
        file_idx += 1

    # 初始化任务状态
    tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "project_name": project_name,
        "task_dir": str(task_dir),
        "bidder_files": {k: v for k, v in bidder_files.items() if v}
    }

    # 后台执行分析
    background_tasks.add_task(run_analysis, task_id)

    return TaskCreateResponse(
        task_id=task_id,
        status="pending",
        message="分析任务已创建"
    )


@app.get("/api/v1/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks[task_id]

    response = TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        progress=task.get("progress", 0),
        project_name=task.get("project_name"),
        risk_score=task.get("risk_score"),
        risk_level=task.get("risk_level"),
        traces_count=task.get("traces_count"),
        bidders_count=task.get("bidders_count"),
        error=task.get("error"),
        download_url=f"/api/v1/download/{task_id}" if task["status"] == "completed" else None
    )

    return response


@app.get("/api/v1/report/{task_id}", response_model=ReportDetailResponse)
async def get_report_detail(task_id: str):
    """获取报告详情"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")

    report = task.get("report")
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    return ReportDetailResponse(
        task_id=task_id,
        project_name=report.project_name,
        analysis_time=report.analysis_time.isoformat(),
        risk_score=report.risk_score,
        risk_level=report.risk_level,
        bidders=report.bidders,
        traces=[
            TraceDetail(
                type=t.trace_type.value,
                bidder_a=t.bidder_a,
                bidder_b=t.bidder_b,
                value=t.value,
                weight=t.weight,
                evidence=t.evidence
            ) for t in report.traces
        ],
        trace_matrix=report.trace_matrix,
        heatmap_data=report.heatmap_data,
        network_nodes=report.network_nodes,
        network_edges=report.network_edges
    )


@app.get("/api/v1/download/{task_id}")
async def download_report(
    task_id: str,
    format: str = Query("html", description="报告格式: html, json, pdf")
):
    """下载报告文件"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")

    file_path = Path(task["task_dir"]) / f"report.{format}"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="报告文件不存在")

    return FileResponse(
        file_path,
        filename=f"bidcheck_report_{task_id}.{format}",
        media_type=_get_media_type(format)
    )


# === 辅助函数 ===

def run_analysis(task_id: str):
    """执行分析任务"""
    from ..core.engine import DetectionEngine
    from ..report.generator import ReportGenerator

    task = tasks[task_id]
    task["status"] = "processing"
    task["progress"] = 10

    try:
        engine = DetectionEngine(task["project_name"])
        task["progress"] = 30

        report = engine.analyze(task["bidder_files"])
        task["progress"] = 80

        # 保存报告
        generator = ReportGenerator()
        task_dir = Path(task["task_dir"])
        generator.generate(report, "html", str(task_dir / "report.html"))
        generator.generate(report, "json", str(task_dir / "report.json"))

        # 更新任务状态
        task["status"] = "completed"
        task["progress"] = 100
        task["report"] = report
        task["risk_score"] = report.risk_score
        task["risk_level"] = report.risk_level
        task["traces_count"] = len(report.traces)
        task["bidders_count"] = len(report.bidders)

    except Exception as e:
        task["status"] = "failed"
        task["error"] = str(e)


def _get_media_type(format: str) -> str:
    """获取 MIME 类型"""
    types = {
        "html": "text/html",
        "json": "application/json",
        "pdf": "application/pdf"
    }
    return types.get(format, "application/octet-stream")


# === 启动命令 ===
# uvicorn bidcheck.api.main:app --reload --port 8000
```

## 验收标准

- [ ] CLI `analyze` 命令可正确分析目录
- [ ] CLI `inspect` 命令可正确显示文件元数据
- [ ] API `/api/v1/analyze` 可接收文件并创建任务
- [ ] API `/api/v1/status/{task_id}` 可返回任务状态
- [ ] API `/api/v1/report/{task_id}` 可返回报告详情
- [ ] API `/api/v1/download/{task_id}` 可下载报告文件
- [ ] Swagger 文档可访问 (/docs)
- [ ] 单元测试覆盖率 > 80%
