# BidCheck - 围标检测系统设计规格

## 项目概述

BidCheck 是一个用于检测政府招投标项目中围标、串标行为的工具。通过分析不同投标方提交的文档元数据，识别可能来自同一来源的文件，从而发现潜在的围标风险。

## 核心功能

1. **多格式文件解析** - 支持 Word (.docx)、Excel (.xlsx)、PDF 文件
2. **深度元数据提取** - 提取 6 大类 25+ 种痕迹信息
3. **智能风险评分** - 基于权重计算风险指数 (0-100)
4. **可视化分析** - 热力图、关系网络图
5. **多端支持** - CLI 命令行、API 服务、Web 界面

## 技术栈

| 组件 | 技术选型 |
|------|---------|
| 后端语言 | Python 3.11+ |
| 后端框架 | FastAPI |
| 文档解析 | python-docx, openpyxl, pypdf, oletools |
| 前端框架 | Vue 3 + Vite |
| UI 组件 | Element Plus |
| 图表库 | ECharts |
| 样式 | TailwindCSS |

## 项目结构

```
bidcheck/
├── pyproject.toml
├── README.md
├── src/
│   └── bidcheck/
│       ├── core/              # 核心模块
│       │   ├── models.py      # 数据模型
│       │   └── engine.py      # 检测引擎
│       ├── extractors/        # 文件提取器
│       │   ├── base.py
│       │   ├── docx.py
│       │   ├── xlsx.py
│       │   └── pdf.py
│       ├── analyzers/         # 分析器
│       │   ├── metadata.py
│       │   ├── fingerprint.py
│       │   └── similarity.py
│       ├── cli/               # 命令行接口
│       │   └── main.py
│       ├── api/               # API 服务
│       │   ├── main.py
│       │   └── routes.py
│       └── report/            # 报告生成
│           ├── generator.py
│           └── templates/
├── web/                       # Web 前端
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.js
│       ├── App.vue
│       ├── views/
│       ├── components/
│       └── api/
└── tests/
    └── ...
```

## 实现阶段

| 阶段 | 内容 | 文档 |
|------|------|------|
| Phase 1 | 核心引擎与数据模型 | [01-core-engine.md](./01-core-engine.md) |
| Phase 2 | 文件提取器实现 | [02-extractors.md](./02-extractors.md) |
| Phase 3 | 分析器与评分算法 | [03-analyzers.md](./03-analyzers.md) |
| Phase 4 | CLI 与 API 接口 | [04-cli-api.md](./04-cli-api.md) |
| Phase 5 | Web 前端界面 | [05-web-frontend.md](./05-web-frontend.md) |

## 关键设计决策

1. **痕迹权重体系** - 基于可伪造难度划分 4 档权重 (0.30-0.95)
2. **分层架构** - 提取器/分析器/报告 三个层次解耦
3. **RSID 作为核心指纹** - Word 修订保存 ID 可建立文档谱系
4. **API 优先** - 后端设计 API，CLI 和 Web 均调用 API

## 验收标准

- [ ] 能正确提取 Word/Excel/PDF 的元数据
- [ ] 能检测出 RSID、OLE GUID 等高权重痕迹
- [ ] 风险评分算法合理，阈值可配置
- [ ] CLI 可正常分析目录并生成报告
- [ ] API 可被正常调用
- [ ] Web 界面可上传文件并查看结果
