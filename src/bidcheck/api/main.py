"""FastAPI 服务"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uuid
import os
import shutil
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

    # 过滤空投标方
    bidder_files = {k: v for k, v in bidder_files.items() if v}

    # 初始化任务状态
    tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "project_name": project_name,
        "task_dir": str(task_dir),
        "bidder_files": bidder_files
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

    return TaskStatusResponse(
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
    format: str = Query("html", description="报告格式: html, json")
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
    }
    return types.get(format, "application/octet-stream")


# === 启动命令 ===
# uvicorn bidcheck.api.main:app --reload --port 8000
