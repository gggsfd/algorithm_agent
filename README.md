# Algorithm Agent - 字幕纠错系统

基于 FastAPI 的高并发强约束多 Agent 字幕纠错系统，解决垂直领域（计算机科学与算法课程）视频 ASR 处理后专业术语识别率低的痛点。

---

## 核心流程

```
SRT解析 → 滑动窗口切片 → RAG检索 → 双重Agent纠错 → 格式还原
```

**核心红线**：零格式破坏，必须 100% 保持原始 .srt 文件的时间轴、序号和换行符

---

## 技术栈

| 类别 | 技术 |
|------|------|
| Web 框架 | FastAPI + Uvicorn |
| LLM API | DeepSeek (支持双 API Key) |
| RAG 引擎 | ChromaDB + 拼音检索 |
| 数据库 | MySQL + SQLAlchemy |
| 其他 | Pydantic, python-multipart, pypinyin |

---

## 项目结构

```
algorithm_agent/
├── app/
│   ├── main.py                    # FastAPI 入口
│   ├── agents/                    # 多智能体
│   │   ├── agent_a.py             # 侦察 Agent，发现错误
│   │   ├── agent_b.py             # 主刀 Agent，执行替换
│   │   └── pipeline.py            # Agent 编排
│   ├── api/                       # 接口路由
│   │   ├── srt.py                 # 字幕处理接口
│   │   └── device.py              # 设备管理
│   ├── core/                      # 核心模块
│   │   ├── srt_parser.py          # SRT 解析器 (CRLF/LF 兼容)
│   │   ├── constraint_checker.py  # 格式校验器
│   │   ├── task_dispatcher.py     # 滑动窗口分发器
│   │   ├── retry_handler.py       # 重试处理器 (指数退避)
│   │   ├── circuit_breaker.py     # 熔断器 (三态)
│   │   └── llm_config.py          # LLM 配置
│   ├── rag/                       # RAG 引擎
│   │   ├── pinyin_converter.py    # 拼音转换器
│   │   ├── vector_store.py        # 向量存储
│   │   └── retrieval.py           # 检索引擎
│   ├── services/
│   │   └── srt_service.py         # SRT 处理服务
│   └── schemas/
│       └── response.py            # 统一响应结构
├── scripts/
│   └── import_terms.py            # 术语库导入
├── tests/                         # 测试文件
└── requirements.txt
```

---

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/parse` | POST | 解析 SRT 文件 |
| `/api/v1/correct` | POST | 单次字幕纠错 |
| `/api/v1/batch` | POST | 滑动窗口批量纠错 |
| `/api/v1/batch/robust` | POST | 带重试+熔断的健壮纠错 |

---

## 核心特性

- ✅ **RAG 检索**：算法术语库 76 个 + ASR 错误映射 51 个
- ✅ **拼音纠错**：拼音相似度计算，捕获音近错误
- ✅ **滑动窗口**：长视频分块处理，避免 Token 超限
- ✅ **重试机制**：指数退避 + 随机抖动
- ✅ **熔断保护**：CLOSED → HALF_OPEN → OPEN 三态转换
- ✅ **CRLF 兼容**：Windows/Linux 文件换行符自动适配

---

## 快速开始

### 1. 创建虚拟环境

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. 安装依赖

```powershell
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY 等配置
```

### 4. 启动服务

```powershell
uvicorn app.main:app --reload
```

服务启动于 `http://localhost:8000`，API 文档 `http://localhost:8000/docs`

---

## 测试

```powershell
.\venv\Scripts\python.exe -m pytest tests/ -v --tb=short
```

---

## 许可证

MIT
