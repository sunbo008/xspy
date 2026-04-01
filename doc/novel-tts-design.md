# 小说 TTS 配音系统设计方案（总纲）

> 本文档是系统的**顶层设计总纲**，定义整体架构、模块划分、数据流。
> 每个模块的详细实现、接口定义、代码示例均在各自的专属文档中，请通过下方索引跳转。

---

## 1. 系统架构

```
┌───────────────────────────────────────────────────────────────────────────┐
│                          小说 TTS 全自动配音系统                            │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  Mac 客户端 (M5 Pro 64GB)                     Windows 服务端 (RTX 3070 Ti)│
│  ┌─────────────────────────────────┐          ┌────────────────────────┐ │
│  │  Web UI (Vue 3 + FastAPI)       │          │  TTS API 服务           │ │
│  │  ┌───────────────────────────┐  │          │  ┌──────────────────┐  │ │
│  │  │ 小说解析器                 │  │          │  │ Index-TTS vLLM   │  │ │
│  │  │ 编剧 Agent (Qwen3.5 LLM) │  │  HTTP    │  │ Qwen3-TTS vLLM   │  │ │
│  │  │ 角色分析引擎               │  │ ──────▶  │  │ FastAPI 封装      │  │ │
│  │  │ 任务管理器                 │  │          │  └──────────────────┘  │ │
│  │  │ 音频处理器                 │  │          │  GPU 推理加速          │ │
│  │  └───────────────────────────┘  │          └────────────────────────┘ │
│  └─────────────────────────────────┘                                     │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

### 1.1 硬件部署

| 节点 | 硬件 | 职责 |
|------|------|------|
| Mac 客户端 | M5 Pro / 64GB 统一内存 | LLM 推理（Qwen3.5-35B via mlx_lm）、任务调度、Web UI、音频处理 |
| Windows 服务端 | RTX 3070 Ti / 8GB VRAM | TTS 推理（Index-TTS / Qwen3-TTS via vLLM） |

### 1.2 通信方式

- Mac → Windows：HTTP REST API（局域网，延迟 <1ms）
- 前端 → 后端：REST API + WebSocket（进度推送）

---

## 2. 功能全景

本系统包含以下**全部功能**（非后续优化，均为本期开发范围）：

| 功能 | 说明 | 详细文档 |
|------|------|----------|
| 小说文件解析 | TXT / EPUB / PDF 解析、编码检测、章节分割、文本清洗 | [`module-novel-parser.md`](module-novel-parser.md) |
| 全局角色建档 | 角色发现合并、画像推断（性别/年龄/职业/性格）、关系图谱 | [`auto-character-voice-engine.md`](auto-character-voice-engine.md) |
| 自动音色设计 | 画像→音色描述→VoiceDesign→VoiceClone 固化、模板音色池 | [`module-voice-bank.md`](module-voice-bank.md) |
| 编剧 Agent | 对话提取、角色绑定、有声化改写、场景分割 | [`novel-audio-screenwriter-agent.md`](novel-audio-screenwriter-agent.md) |
| 上下文情感推断 | 三层情感分析、叙述线索映射、情感弧线追踪 | [`auto-character-voice-engine.md`](auto-character-voice-engine.md) §4 |
| 情绪控制系统 | EmotionType 定义、VAD 模型、TTS 引擎适配、情绪平滑 | [`module-emotion-system.md`](module-emotion-system.md) |
| 语气词/副语言注入 | 笑声、叹气、喘息等 12 种副语言自动注入 | [`auto-character-voice-engine.md`](auto-character-voice-engine.md) §5 |
| 跨章一致性校验 | 人称/风格/情感/关系/知识 五维度一致性检查 | [`auto-character-voice-engine.md`](auto-character-voice-engine.md) §6 |
| TTS API 客户端 | Index-TTS 1.5/2 + Qwen3-TTS 多引擎、重试、降级 | [`module-tts-api-client.md`](module-tts-api-client.md) |
| 音频处理 | 命名规范、合并、副语言拼接、后处理、M4B 有声书输出 | [`module-audio-processor.md`](module-audio-processor.md) |
| 任务管理 | DAG 调度、并发控制、进度追踪、断点续传 | [`module-task-manager.md`](module-task-manager.md) |
| Web UI | 图形化操作界面、角色管理、剧本编辑、任务监控、音频预览 | [`module-web-ui.md`](module-web-ui.md) |

---

## 3. 端到端数据流

```
用户上传小说文件
    ↓
┌─ Phase 1: 解析 ─────────────────────────────────────────────┐
│  小说解析器 → ParseResult (metadata + chapters[])            │
│  详见: module-novel-parser.md                                │
└──────────────────────────────────┬───────────────────────────┘
                                   ↓
┌─ Phase 2: 全局角色建档 ──────────────────────────────────────┐
│  角色发现 → 别名合并 → 画像推断 → 关系图谱                    │
│  输出: cast_registry[] (含 profile, aliases, relationships)  │
│  详见: auto-character-voice-engine.md §2                     │
└──────────────────────────────────┬───────────────────────────┘
                                   ↓
┌─ Phase 3: 自动音色设计 ──────────────────────────────────────┐
│  画像 → 音色描述 → VoiceDesign → VoiceClone 固化             │
│  输出: voice_bank/{novel_slug}/ 下的音色资源                  │
│  详见: module-voice-bank.md §6, auto-character-voice-engine.md §3│
└──────────────────────────────────┬───────────────────────────┘
                                   ↓
┌─ Phase 4: 逐章剧本生成 ──────────────────────────────────────┐
│  编剧 Agent：                                                │
│    对话提取 → 角色绑定 → 有声化改写 → 场景分割                │
│  角色分析引擎增强：                                           │
│    上下文情感推断 → 语气词注入 → TTS instruct 生成            │
│  一致性校验 → 标记异常 → 生成增强版 JSON 剧本                 │
│  详见: novel-audio-screenwriter-agent.md, auto-character-voice-engine.md §4-6│
└──────────────────────────────────┬───────────────────────────┘
                                   ↓
┌─ Phase 5: TTS 合成 ──────────────────────────────────────────┐
│  遍历 utterances[]，携带 voice_clone_prompt + tts_instruct   │
│  调用 Windows TTS 服务（Index-TTS / Qwen3-TTS）              │
│  输出: output/{novel_slug}/raw/ 下的音频片段                  │
│  详见: module-tts-api-client.md                              │
└──────────────────────────────────┬───────────────────────────┘
                                   ↓
┌─ Phase 6: 音频合并与后处理 ──────────────────────────────────┐
│  按 seq 排序拼接 → 插入副语言音效 → 插入静音停顿              │
│  后处理: 音量标准化、淡入淡出、采样率统一                     │
│  全书组装: 章节合并 → M4B 有声书（含元数据、章节标记）         │
│  详见: module-audio-processor.md                             │
└──────────────────────────────────┬───────────────────────────┘
                                   ↓
                          完整有声书 (.m4b / .mp3)
```

---

## 4. 项目代码结构

```
xspy/
├── pyproject.toml                  # 项目元数据、依赖声明
├── README.md
├── doc/                            # 设计文档（本目录）
│
├── src/xspy/                       # ────── Python 主包 ──────
│   ├── __init__.py
│   ├── pipeline.py                 # 端到端流水线编排入口
│   ├── cli.py                      # 命令行入口（Click / Typer）
│   │
│   ├── core/                       # 全局共享：配置、模型、类型
│   │   ├── __init__.py
│   │   ├── config.py               #   ServerConfig / TTSConfig / AppConfig
│   │   ├── models.py               #   Chapter / NovelMetadata / ParseResult
│   │   └── types.py                #   EmotionType / TaskType / TaskStatus
│   │
│   ├── parser/                     # 小说解析器
│   │   ├── __init__.py             #   → module-novel-parser.md
│   │   ├── base.py                 #   BaseParser 抽象基类
│   │   ├── txt.py                  #   TXTParser
│   │   ├── epub.py                 #   EPUBParser
│   │   ├── pdf.py                  #   PDFParser
│   │   ├── splitter.py             #   ChapterSplitter（章节分割引擎）
│   │   ├── encoding.py             #   EncodingDetector
│   │   ├── cleaner.py              #   TextCleaner
│   │   └── factory.py              #   ParserFactory
│   │
│   ├── agent/                      # LLM Agent 层
│   │   ├── __init__.py
│   │   ├── screenwriter/           #   编剧 Agent
│   │   │   ├── __init__.py         #   → novel-audio-screenwriter-agent.md
│   │   │   ├── agent.py            #     ScreenwriterAgent 主逻辑
│   │   │   ├── prompts.py          #     系统提示词模板
│   │   │   └── schema.py           #     剧本 JSON Schema 定义与校验
│   │   └── character/              #   角色分析引擎
│   │       ├── __init__.py         #   → auto-character-voice-engine.md
│   │       ├── discovery.py        #     角色发现与别名合并
│   │       ├── profiler.py         #     角色画像推断（性别/年龄/职业/性格）
│   │       ├── relationship.py     #     角色关系图谱构建
│   │       ├── consistency.py      #     跨章一致性校验
│   │       └── paraverbal.py       #     语气词/副语言注入
│   │
│   ├── emotion/                    # 情绪控制系统
│   │   ├── __init__.py             #   → module-emotion-system.md
│   │   ├── types.py                #   EmotionType 枚举（从 core/types.py re-export）
│   │   ├── detail.py               #   EmotionDetail 数据模型
│   │   ├── rules.py                #   NarrationRuleEngine（叙述线索规则）
│   │   ├── smoother.py             #   EmotionSmoother（情绪平滑器）
│   │   ├── audio_library.py        #   EmotionAudioLibrary（情绪参考音频）
│   │   └── adapter/                #   TTS 引擎情绪适配器
│   │       ├── __init__.py
│   │       ├── base.py             #     EmotionAdapter 抽象基类
│   │       ├── qwen.py             #     QwenTTSEmotionAdapter
│   │       └── index_tts.py        #     IndexTTSEmotionAdapter
│   │
│   ├── voice/                      # 角色音色库
│   │   ├── __init__.py             #   → module-voice-bank.md
│   │   ├── bank.py                 #   VoiceBankManager（音色库管理器）
│   │   ├── registry.py             #   VoiceRegistry（注册表读写）
│   │   ├── generator.py            #   VoiceGenerator（自动音色生成）
│   │   ├── similarity.py           #   SimilarityChecker（区分度校验）
│   │   └── templates.py            #   TemplatePool（模板音色池）
│   │
│   ├── tts/                        # TTS API 客户端
│   │   ├── __init__.py             #   → module-tts-api-client.md
│   │   ├── base.py                 #   BaseTTSClient 抽象基类
│   │   ├── index_v1.py             #   IndexTTSClient（1.0 / 1.5）
│   │   ├── index_v2.py             #   IndexTTSV2Client
│   │   ├── qwen.py                 #   QwenTTSClient
│   │   ├── factory.py              #   TTSClientFactory
│   │   ├── retry.py                #   RetryManager
│   │   └── health.py               #   HealthChecker
│   │
│   ├── audio/                      # 音频处理器
│   │   ├── __init__.py             #   → module-audio-processor.md
│   │   ├── naming.py               #   FilenameGenerator（文件命名）
│   │   ├── merger.py               #   AudioMerger（章节合并）
│   │   ├── splicer.py              #   ParaverbalSplicer（副语言拼接）
│   │   ├── post_process.py         #   PostProcessor（音量/淡入淡出）
│   │   └── assembler.py            #   BookAssembler（M4B 组装）
│   │
│   ├── task/                       # 任务管理器
│   │   ├── __init__.py             #   → module-task-manager.md
│   │   ├── models.py               #   Task / ProcessingPlan
│   │   ├── queue.py                #   TaskQueue（DAG 调度）
│   │   ├── worker.py               #   WorkerPool（线程池）
│   │   ├── progress.py             #   ProgressTracker + CLIProgress
│   │   ├── checkpoint.py           #   CheckpointManager（断点续传）
│   │   └── planner.py              #   PlanGenerator（计划生成器）
│   │
│   └── web/                        # Web UI 后端
│       ├── __init__.py             #   → module-web-ui.md
│       ├── app.py                  #   FastAPI 主入口
│       ├── deps.py                 #   依赖注入
│       ├── routes/                 #   REST API 路由
│       │   ├── __init__.py
│       │   ├── novels.py
│       │   ├── characters.py
│       │   ├── voices.py
│       │   ├── scripts.py
│       │   ├── tasks.py
│       │   └── audio.py
│       └── ws/                     #   WebSocket
│           ├── __init__.py
│           └── progress.py
│
├── frontend/                       # ────── Vue 3 前端 ──────
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── views/                  #   页面组件
│       │   ├── NovelList.vue
│       │   ├── NovelDetail.vue
│       │   ├── CharacterPanel.vue
│       │   ├── VoiceBank.vue
│       │   ├── ScriptEditor.vue
│       │   ├── TaskMonitor.vue
│       │   └── AudioPlayer.vue
│       ├── components/             #   通用组件
│       │   ├── CharacterCard.vue
│       │   ├── EmotionBadge.vue
│       │   ├── WaveformPlayer.vue
│       │   ├── ProgressBar.vue
│       │   └── RelationGraph.vue
│       ├── stores/                 #   Pinia 状态管理
│       │   ├── novel.ts
│       │   ├── character.ts
│       │   └── task.ts
│       └── api/
│           └── client.ts
│
├── resources/                      # ────── 静态资源 ──────
│   ├── sfx/                        #   副语言音效库
│   │   ├── laughter/
│   │   │   ├── male_hearty.wav
│   │   │   ├── male_chuckle.wav
│   │   │   ├── female_giggle.wav
│   │   │   └── female_chuckle.wav
│   │   ├── sigh/
│   │   ├── gasp/
│   │   ├── sobbing/
│   │   └── ...
│   ├── emotion_audio/              #   情绪参考音频（用于 Index-TTS）
│   │   ├── happy/
│   │   │   ├── low.wav
│   │   │   ├── medium.wav
│   │   │   └── high.wav
│   │   ├── sad/
│   │   └── ...
│   └── voice_templates/            #   龙套模板音色
│       ├── male_child.wav
│       ├── male_young.wav
│       ├── male_middle.wav
│       ├── female_child.wav
│       ├── female_young.wav
│       └── ...
│
├── data/                           # ────── 运行时数据（.gitignore） ──────
│   ├── voice_bank/                 #   角色音色库存储
│   │   └── {novel_slug}/
│   │       ├── voice_registry.json
│   │       ├── narrator/
│   │       ├── {character_slug}/
│   │       └── ...
│   ├── output/                     #   音频输出
│   │   └── {novel_slug}/
│   │       ├── raw/ch0001/
│   │       ├── chapters/
│   │       └── audiobook/
│   ├── scripts/                    #   编剧 Agent 输出的剧本 JSON
│   │   └── {novel_slug}/
│   │       ├── novel_profile.json
│   │       ├── ch0001.json
│   │       └── ...
│   ├── checkpoints/                #   断点续传状态
│   └── cache/                      #   LLM 响应缓存
│
├── tests/                          # ────── 测试 ──────
│   ├── conftest.py
│   ├── fixtures/                   #   测试用小说片段、音频样本
│   ├── test_parser/
│   ├── test_agent/
│   ├── test_emotion/
│   ├── test_voice/
│   ├── test_tts/
│   ├── test_audio/
│   └── test_task/
│
├── scripts/                        # ────── 工具脚本 ──────
│   ├── setup_windows_tts.sh        #   Windows TTS 服务端一键部署
│   └── download_models.sh          #   模型权重下载
│
└── novel/                          # ────── 小说文件存放 ──────
    └── ...
```

### 4.1 结构设计原则

| 原则 | 说明 |
|------|------|
| **src-layout** | 使用 `src/xspy/` 布局，避免导入歧义，符合 Python 打包最佳实践 |
| **模块自治** | 每个子包（`parser/`、`tts/`、`voice/`…）内聚，有独立的 `__init__.py` 导出公共接口 |
| **共享上提** | 跨模块共用的类型（`EmotionType`）、模型（`Chapter`）、配置统一放在 `core/` |
| **资源分离** | 静态资源（音效、模板）放 `resources/`，运行时产物放 `data/`（gitignore） |
| **前后端分离** | Python 后端在 `src/xspy/web/`，Vue 前端在 `frontend/`，独立构建 |
| **agent 分组** | 编剧 Agent 和角色分析引擎都是 LLM 驱动的，统一放在 `agent/` 下作为子包 |

### 4.2 模块导入路径

```python
# 小说解析
from xspy.parser import ParserFactory
from xspy.parser.txt import TXTParser

# 编剧 Agent
from xspy.agent.screenwriter import ScreenwriterAgent

# 角色分析
from xspy.agent.character import CharacterDiscovery, CharacterProfiler

# 情绪系统
from xspy.emotion import EmotionDetail, EmotionType
from xspy.emotion.adapter.qwen import QwenTTSEmotionAdapter

# 音色库
from xspy.voice import VoiceBankManager, VoiceGenerator

# TTS 客户端
from xspy.tts import TTSClientFactory
from xspy.tts.qwen import QwenTTSClient

# 音频处理
from xspy.audio import AudioMerger, BookAssembler

# 任务管理
from xspy.task import TaskQueue, WorkerPool, CheckpointManager

# 流水线
from xspy.pipeline import NovelTTSPipeline
```

---

## 5. 模块索引

### 4.1 核心处理模块

| # | 模块 | 文档 | 运行端 | 简述 |
|---|------|------|--------|------|
| 1 | 小说解析器 | [`module-novel-parser.md`](module-novel-parser.md) | Mac | TXT/EPUB/PDF 解析、编码检测、章节分割、文本清洗 |
| 2 | 编剧 Agent | [`novel-audio-screenwriter-agent.md`](novel-audio-screenwriter-agent.md) | Mac (LLM) | 对话提取、角色绑定、有声化改写、场景分割、剧本 JSON 输出 |
| 3 | 角色分析引擎 | [`auto-character-voice-engine.md`](auto-character-voice-engine.md) | Mac (LLM) | 角色发现合并、画像推断、关系图谱、情感推断、语气词注入、一致性校验 |
| 4 | 情绪控制系统 | [`module-emotion-system.md`](module-emotion-system.md) | Mac + Win | EmotionType 定义、VAD 模型、引擎适配、规则推断、平滑 |
| 5 | 角色音色库 | [`module-voice-bank.md`](module-voice-bank.md) | Mac + Win | 音色注册、自动生成、固化存储、模板池、区分度校验 |
| 6 | TTS API 客户端 | [`module-tts-api-client.md`](module-tts-api-client.md) | Mac → Win | Index-TTS/Qwen3-TTS 多引擎封装、重试、降级 |
| 7 | 音频处理器 | [`module-audio-processor.md`](module-audio-processor.md) | Mac | 命名规范、合并、副语言拼接、后处理、M4B 组装 |

### 4.2 基础设施模块

| # | 模块 | 文档 | 运行端 | 简述 |
|---|------|------|--------|------|
| 8 | 任务管理器 | [`module-task-manager.md`](module-task-manager.md) | Mac | DAG 调度、并发、进度、断点续传 |
| 9 | Web UI | [`module-web-ui.md`](module-web-ui.md) | Mac | Vue 3 前端 + FastAPI 后端，全流程图形化操作 |

### 4.3 部署与运维

| # | 文档 | 简述 |
|---|------|------|
| 10 | [`index-tts-vllm-deployment.md`](index-tts-vllm-deployment.md) | Windows 端 Index-TTS vLLM 部署指南 |

### 4.4 分析与调研

| # | 文档 | 简述 |
|---|------|------|
| 11 | [`TTS项目借鉴分析报告.md`](TTS项目借鉴分析报告.md) | ebook2audiobook / easyVoice / Bark / Qwen3-TTS 对比分析 |
| 12 | [`tts-open-source-analysis.md`](tts-open-source-analysis.md) | 开源 TTS 项目分析 |

---

## 5. 技术选型总览

### 5.1 核心技术栈

| 层 | 技术 | 用途 |
|-----|------|------|
| LLM 推理 | Qwen3.5-35B-A3B Q8 + mlx_lm | 编剧 Agent、角色分析、情感推断 |
| TTS 推理 | Index-TTS 1.5 / Qwen3-TTS + vLLM | 语音合成 |
| 后端框架 | Python + FastAPI | Web API、任务调度 |
| 前端框架 | Vue 3 + TypeScript + Element Plus | Web UI |
| 音频处理 | pydub + ffmpeg | 剪辑、合并、格式转换 |

### 5.2 文本解析依赖

| 库 | 用途 | 详见 |
|-----|------|------|
| `chardet` | 编码检测 | [`module-novel-parser.md`](module-novel-parser.md) §5.1 |
| `ebooklib` | EPUB 解析 | [`module-novel-parser.md`](module-novel-parser.md) §6 |
| `PyPDF2` / `pdfplumber` | PDF 解析 | [`module-novel-parser.md`](module-novel-parser.md) §7 |
| `beautifulsoup4` + `lxml` | HTML 内容提取 | [`module-novel-parser.md`](module-novel-parser.md) §6 |

### 5.3 TTS 引擎

| 引擎 | 优势 | 音色克隆 | 情感控制 | 详见 |
|------|------|----------|---------|------|
| Index-TTS 1.5 | 中文优化、质量高 | ✅ | 有限 | [`module-tts-api-client.md`](module-tts-api-client.md) §5 |
| IndexTTS-2 | 多语言、情绪参考音频 | ✅ | ✅ | [`module-tts-api-client.md`](module-tts-api-client.md) §5.2 |
| Qwen3-TTS | VoiceDesign、instruct 自然语言控制 | ✅ (3秒) | ✅ (instruct) | [`module-tts-api-client.md`](module-tts-api-client.md) §6 |

---

## 6. 音频文件命名规范

```
{novel_slug}-{chapter_num:04d}-{speaker_slug}-{emotion}-{seq_num:06d}.wav
```

| 字段 | 位数 | 示例 | 说明 |
|------|------|------|------|
| `novel_slug` | 可变 | `silent_bookstore` | 小说 ASCII 简称 |
| `chapter_num` | 4 | `0001` | 章节号 |
| `speaker_slug` | 可变 | `linwan` / `narrator` | 角色 slug |
| `emotion` | 可变 | `happy` | 主情绪标签 |
| `seq_num` | 6 | `000001` | 章节内全局序号 |

特殊标记：`narrator`（旁白）、`desc`（场景描述）、`inner_{slug}`（内心独白）、`sfx`（音效）

> 完整命名规范、目录结构、生成器实现详见 [`module-audio-processor.md`](module-audio-processor.md) §3

---

## 7. 情绪类型定义

全系统统一使用的情绪枚举（20 种）：

| 基础情绪 | 扩展情绪 |
|----------|----------|
| `happy` 快乐 | `excited` 兴奋 |
| `sad` 悲伤 | `calm` 平静 |
| `angry` 愤怒 | `confident` 自信 |
| `fear` 恐惧 | `sarcastic` 讽刺 |
| `surprise` 惊讶 | `romantic` 浪漫 |
| `disgust` 厌恶 | `anxious` 焦虑 |
| `neutral` 中性 | `nostalgic` 怀旧 |
| | `grief` 悲痛 |
| | `contempt` 蔑视 |
| | `gentle` 温柔 |
| | `cold` 冷漠 |
| | `resigned` 无奈 |
| | `proud` 骄傲 |

> 完整的 EmotionType 定义、VAD 模型、引擎适配详见 [`module-emotion-system.md`](module-emotion-system.md)

---

## 8. 性能预估

| 阶段 | 预估耗时 | 并发 | 瓶颈 |
|------|----------|------|------|
| 小说解析 | 1-5 秒 | 1 | CPU |
| 角色分析 | 30-120 秒 | 1 | LLM |
| 音色设计 | 角色数 × 10-30 秒 | 1 | TTS GPU |
| 剧本生成 | 每章 10-30 秒 | 2-4 | LLM |
| TTS 合成 | 每句 2-10 秒 | 2-4 | GPU |
| 音频合并 | 每章 1-3 秒 | 4-8 | CPU |
| 后处理 | 每章 1-2 秒 | 4-8 | CPU |

**全书预估**（以 50 章、每章 100 句为例）：

| 指标 | 预估 |
|------|------|
| 总 TTS 合成 | 5000 句 |
| TTS 合成总时间 | ~2.5-7 小时（4 并发） |
| 全流程总时间 | ~3-8 小时 |
| 输出有声书时长 | ~15-25 小时 |

---

## 9. 验证清单

### 9.1 基础设施

- [ ] Windows TTS 服务已启动并监听 `0.0.0.0:6006`
- [ ] Mac 可访问 Windows 服务（`curl http://192.168.x.x:6006/docs`）
- [ ] Mac LLM 可正常推理（Qwen3.5-35B via mlx_lm）

### 9.2 模块功能

- [ ] 小说解析器：TXT/EPUB/PDF 各一个文件成功解析并分章
- [ ] 角色分析引擎：自动识别角色、推断画像、构建关系图
- [ ] 音色库：自动为主角生成音色，不同角色音色有区分度
- [ ] 编剧 Agent：输出合法的结构化 JSON 剧本
- [ ] 情绪系统：情绪标签全部在合法枚举内，无突兀跳跃
- [ ] 语气词注入：笑声、叹气等在合适位置注入
- [ ] TTS 合成：单句音频质量可接受，情绪可感知
- [ ] 音频合并：章节音频连续、停顿自然、音量均匀
- [ ] 任务管理：进度显示准确，中断后可断点续传
- [ ] Web UI：上传→处理→预览→导出 全流程可走通

### 9.3 端到端

- [ ] 上传一本完整小说（>10 章），全自动跑完
- [ ] 输出 M4B 有声书可在 Apple Books 正常播放（含章节标记）
- [ ] 不同角色音色可区分，情绪变化可感知

---

## 10. 文档变更同步规则

以下字段/定义如有变更，需同步更新所有关联文档：

| 变更项 | 影响文档 |
|--------|----------|
| `EmotionType` 枚举 | `module-emotion-system.md`、`novel-audio-screenwriter-agent.md`、`auto-character-voice-engine.md` |
| 音频命名规范 | `module-audio-processor.md`、`novel-audio-screenwriter-agent.md` |
| `cast_registry` Schema | `novel-audio-screenwriter-agent.md`、`auto-character-voice-engine.md`、`module-voice-bank.md` |
| `utterance` Schema | `novel-audio-screenwriter-agent.md`、`auto-character-voice-engine.md`、`module-audio-processor.md` |
| TTS API 端点 | `module-tts-api-client.md`、`index-tts-vllm-deployment.md` |

---

## 11. 参考资料

1. https://github.com/DrewThomasson/ebook2audiobookSTYLETTS2
2. https://github.com/cosin2077/easyVoice
3. https://github.com/suno-ai/bark
4. https://github.com/QwenLM/Qwen3-TTS
5. https://github.com/Ksuriuri/index-tts-vllm
