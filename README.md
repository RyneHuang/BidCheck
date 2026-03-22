# BidCheck - 围标检测系统

通过分析投标文档元数据识别围标风险。

## 安装

```bash
pip install -e ".[dev]"
```

## 使用

### CLI 命令行

```bash
# 分析投标文件目录
bidcheck analyze ./bidding_files -o report.html

# 检查单个文件元数据
bidcheck inspect ./技术标.docx
```

### API 服务

```bash
uvicorn bidcheck.api.main:app --reload --port 8000
```

## 支持的文件格式

- Word (.docx, .doc)
- Excel (.xlsx)
- PDF (.pdf)
