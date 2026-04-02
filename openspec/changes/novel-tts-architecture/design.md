## Context

xspy 是一个小说→有声书全自动配音系统。Mac 端运行 LLM（Qwen3.5-35B via mlx_lm）+ 任务调度 + Web UI，Windows 端运行 TTS 推理（Index-TTS / Qwen3-TTS via vLLM，RTX 3070 Ti 8GB）。

当前状态：13 篇详细设计文档已完成，定义了 9 个核心模块、数据流、Schema。项目结构已规划为 `src/xspy/` 的 src-layout。尚无可运行代码。

约束：
- Mac M5 Pro 64GB + Windows RTX 3070 Ti 8GB，局域网 HTTP 通信
- Python 3.12+，前端 Vue 3 + TypeScript
- LLM 调用成本需控制（长篇小说可能产生数万次调用）
- 需支持断点续传（一本书可能处理数小时）

## Goals / Non-Goals

**Goals:**
- 低耦合高内聚：每个模块通过 Protocol 接口通信，实现可替换
- AI 原生：LLM 调用可配置、可缓存、可回放、输出可校验
- 可观测：结构化日志 + trace_id 链路追踪，精确到单句 utterance 级别
- 自测闭环：设计→开发→测试→验证设计的完整循环
- 快速迭代：新增 TTS 引擎或解析器只需实现 Protocol + 注册到容器

**Non-Goals:**
- 不做分布式部署（单 Mac + 单 Windows 足够）
- 不做实时流式对话（本项目是批量离线处理）
- 不做移动端 UI
- 不做模型训练/微调

## Decisions

### Decision 1：接口抽象用 Python Protocol 而非 ABC

**选择：** `typing.Protocol`（结构化子类型）

**替代方案：** `abc.ABC`（名义子类型）

**理由：**
- Protocol 是鸭子类型的形式化，不要求继承关系，第三方实现无需改代码
- 更适合"替换实现"的场景——新的 TTS 引擎只需实现相同方法签名即可
- 类型检查器（mypy/pyright）原生支持，与 IDE 集成更好
- ABC 的 `@abstractmethod` 在运行时有微弱的保护作用，但 Protocol + 类型检查器提供编译期保护更强

### Decision 2：依赖注入用 dependency-injector

**选择：** `dependency-injector`

**替代方案：** 手动工厂 / `injector` / `lagom`

**理由：**
- Python 生态中最成熟的 DI 框架，支持 Singleton/Factory/Configuration Provider
- 声明式容器定义，一眼看清所有模块依赖关系
- 支持 override（测试时替换真实实现为 mock）
- 配置可从 YAML/环境变量加载，不改代码切换实现

### Decision 3：日志框架用 structlog

**选择：** `structlog`（结构化日志）

**替代方案：** 标准 `logging` / `loguru`

**理由：**
- 原生结构化输出（JSON），适合机器解析和日志聚合
- 上下文绑定（`bind()`）可以在模块入口绑定 `novel_slug`、`chapter_num`、`speaker_id`，下游所有日志自动携带
- 处理器链架构，可灵活组合（添加 trace_id、过滤敏感信息、采样等）
- 开发环境用彩色 Console 输出，生产环境用 JSON 输出，同一套代码
- loguru 虽然易用但缺乏结构化上下文绑定能力

### Decision 4：LLM 调用层——多模型 OpenAI SDK 兼容架构

**选择：** 统一基于 OpenAI SDK 协议的多模型客户端，模型通过 JSON 配置文件声明式注册

**替代方案：** 硬编码单一模型 / 自建私有协议

**设计：**
```
src/xspy/core/llm/
├── __init__.py
├── protocol.py        # LLMClient Protocol（基于 OpenAI ChatCompletion 接口）
├── client.py          # OpenAICompatibleClient（通用实现，适配所有兼容 API）
├── router.py          # ModelRouter：按任务类型路由到不同模型
├── cache.py           # 响应缓存（磁盘 JSON，key = prompt hash + model_id）
├── prompts.py         # Prompt 模板管理（Jinja2）
└── validator.py       # JSON Schema 校验 LLM 输出
```

**模型配置文件 `config/llm_models.json`：**
```json
{
  "models": [
    {
      "id": "qwen3.5-local",
      "name": "Qwen3.5-35B-A3B",
      "base_url": "http://localhost:8000/v1",
      "api_key": "not-needed",
      "model": "qwen3.5-35b-a3b",
      "max_tokens": 8192,
      "temperature": 0.3,
      "capabilities": ["screenwriter", "character-analysis", "emotion-inference"],
      "priority": 1
    },
    {
      "id": "deepseek-remote",
      "name": "DeepSeek-V3",
      "base_url": "https://api.deepseek.com/v1",
      "api_key": "${DEEPSEEK_API_KEY}",
      "model": "deepseek-chat",
      "max_tokens": 8192,
      "temperature": 0.3,
      "capabilities": ["screenwriter", "character-analysis"],
      "priority": 2
    },
    {
      "id": "qwen-cloud",
      "name": "Qwen-Plus",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "api_key": "${DASHSCOPE_API_KEY}",
      "model": "qwen-plus",
      "max_tokens": 8192,
      "temperature": 0.3,
      "capabilities": ["screenwriter"],
      "priority": 3
    }
  ],
  "task_routing": {
    "screenwriter": "qwen3.5-local",
    "character-analysis": "qwen3.5-local",
    "emotion-inference": "qwen3.5-local"
  }
}
```

**核心设计原则：**
- 所有模型只要兼容 OpenAI SDK 的 `ChatCompletion` 接口即可接入（本地 mlx_lm、vLLM、Ollama、云端 API 均适用）
- `ModelRouter` 根据 `task_routing` 配置将不同 Agent 任务路由到最合适的模型
- `priority` 字段支持自动 fallback：首选模型不可用时按优先级降级
- `api_key` 支持 `${ENV_VAR}` 语法从环境变量注入，避免明文存储
- 新增模型只需在 JSON 中加一条记录，零代码改动

**理由：**
- OpenAI SDK 已成为事实标准，几乎所有 LLM 服务（本地/云端）都提供兼容接口
- JSON 配置比代码注册更灵活，用户可自行添加/切换模型
- 任务路由允许不同 Agent 使用不同模型（如编剧用大模型、情感推断用小模型降低延迟）
- 缓存 key 绑定 `model_id`，切换模型后不会误命中旧缓存
- LLM 输出不确定性高，必须有校验层（JSON Schema 校验 + 重试）
- 测试时用缓存回放替代真实 LLM 调用

### Decision 5：模块 I/O 契约 + 中间数据持久化

**选择：** 每个模块严格定义 Pydantic 类型的 Input/Output，所有中间数据以 JSON 文件持久化到 `data/intermediate/`

**替代方案：** 内存传递 / 数据库存储 / pickle 序列化

**模块数据流与 I/O 定义：**

```
NovelParser                    ScreenwriterAgent                CharacterEngine
┌──────────────────┐          ┌──────────────────────┐          ┌─────────────────────┐
│ IN:  RawNovelFile │          │ IN:  ParseResult      │          │ IN:  ParseResult     │
│      (file path)  │─────────▶│      CastRegistry?    │          │      CastRegistry?   │
│ OUT: ParseResult  │          │ OUT: Screenplay       │─────────▶│ OUT: CastRegistry    │
│      (chapters[]) │          │      CastRegistry     │          │      RelationGraph   │
└──────────────────┘          └──────────────────────┘          └─────────────────────┘
                                        │
                                        ▼
EmotionSystem                  VoiceBank                        TTSClient
┌──────────────────────┐      ┌──────────────────────┐          ┌──────────────────────┐
│ IN:  Screenplay       │      │ IN:  CastRegistry     │          │ IN:  TTSRequest       │
│      CastRegistry     │      │      CharacterProfile  │          │      (text, voice_id, │
│ OUT: EnrichedScreenplay│─────▶│ OUT: VoiceAssignment  │─────────▶│       emotion_params) │
│      (emotion_detail  │      │      (voice_id→params) │          │ OUT: TTSResponse      │
│       filled)         │      └──────────────────────┘          │      (audio bytes,    │
└──────────────────────┘                                         │       metadata)        │
                                                                  └──────────────────────┘
                                        │
                                        ▼
AudioProcessor                 PipelineOrchestrator
┌──────────────────────┐      ┌──────────────────────────────┐
│ IN:  AudioSegment[]   │      │ IN:  RawNovelFile             │
│      Screenplay       │      │ OUT: AudioBook                │
│      ParaverbalConfig │      │      (M4B + chapter markers)  │
│ OUT: ChapterAudio     │      │ 调度所有模块，管理中间数据生命周期  │
│      AudioBook (M4B)  │      └──────────────────────────────┘
└──────────────────────┘
```

**中间数据持久化结构：**
```
data/intermediate/{novel_slug}/
├── parse_result.json           # NovelParser 输出
├── cast_registry.json          # CharacterEngine 输出
├── relation_graph.json         # CharacterEngine 输出
├── screenplay/
│   ├── ch001.json              # ScreenwriterAgent 每章输出
│   ├── ch002.json
│   └── ...
├── enriched_screenplay/
│   ├── ch001.json              # EmotionSystem 情感增强后
│   └── ...
├── voice_assignment.json       # VoiceBank 输出
└── tts_results/
    ├── ch001/
    │   ├── manifest.json       # 该章所有 utterance 的 TTS 状态
    │   ├── u0001.wav
    │   └── ...
    └── ...
```

**设计原则：**
- 每个模块的 `process()` 方法签名严格对应 `Input → Output` Pydantic 类型
- 所有中间数据可序列化为 JSON（音频除外用 WAV），人可读、可检查
- 任何模块都可以独立运行：只需提供其 Input JSON 文件
- 支持"从中间步骤重跑"：修改某章 screenplay JSON 后只需重跑该章下游
- 中间数据是测试的基石：用真实中间数据文件作为模块测试的 fixture

**理由：**
- JSON 持久化让每个处理阶段的结果可审计、可回溯
- 模块测试不依赖上游模块真实运行，只需一份 JSON fixture
- 断点续传天然支持：检查中间文件是否存在即可跳过已完成步骤
- 调试时可以手动修改中间 JSON 观察下游行为变化

### Decision 6：项目→模块→函数 三层测试体系

**选择：** 函数级单测 + 模块级中间数据测试 + 项目级端到端测试

**替代方案：** 传统单元/集成二层测试

**三层架构：**

```
tests/
├── conftest.py                    # 全局 fixture（DI 容器、日志、中间数据加载器）
├── unit/                          # 第一层：函数级单测
│   ├── test_text_cleaner.py       #   纯函数测试，无 I/O，无外部依赖
│   ├── test_chapter_splitter.py
│   ├── test_emotion_mapper.py
│   ├── test_audio_normalizer.py
│   ├── test_prompt_renderer.py
│   └── test_json_validator.py
├── module/                        # 第二层：模块级测试（基于中间数据）
│   ├── conftest.py                #   加载 fixtures/intermediate/ 中的 JSON
│   ├── test_novel_parser.py       #   输入：真实小说文件 → 断言输出 ParseResult
│   ├── test_screenwriter.py       #   输入：parse_result.json → 断言 Screenplay
│   ├── test_character_engine.py   #   输入：parse_result.json → 断言 CastRegistry
│   ├── test_emotion_system.py     #   输入：screenplay.json → 断言 EnrichedScreenplay
│   ├── test_voice_bank.py         #   输入：cast_registry.json → 断言 VoiceAssignment
│   ├── test_tts_client.py         #   输入：tts_request.json → 断言 TTSResponse (mock)
│   └── test_audio_processor.py    #   输入：audio segments + screenplay → 断言 ChapterAudio
├── project/                       # 第三层：项目级端到端测试
│   ├── test_full_pipeline.py      #   完整流程：小说文件 → M4B 有声书
│   ├── test_resume_pipeline.py    #   中断恢复：模拟崩溃后从 checkpoint 续跑
│   └── test_multi_novel.py        #   多本书并行处理
└── fixtures/
    ├── novels/                    #   真实小说片段（3-5 章）
    ├── intermediate/              #   各模块的标准 I/O JSON 样本
    │   ├── parse_result.json
    │   ├── screenplay_ch001.json
    │   ├── cast_registry.json
    │   ├── enriched_screenplay_ch001.json
    │   ├── voice_assignment.json
    │   └── tts_request.json
    ├── llm_cache/                 #   LLM 响应缓存（record-replay）
    └── audio_snapshots/           #   音频回归基准
```

**每层测试的关键特征：**

| 层级 | 粒度 | 输入来源 | 外部依赖 | 速度 | 覆盖目标 |
|------|------|----------|----------|------|----------|
| 函数级 | 单个函数 | 构造参数 | 无 | <1ms/case | 算法逻辑正确性 |
| 模块级 | 单个模块 | fixtures/intermediate/ JSON | LLM 缓存回放、TTS Mock | <5s/case | 模块 I/O 契约、边界条件 |
| 项目级 | 全流程 | 真实小说文件 | LLM 缓存 + TTS Mock | <60s/case | 数据流贯通、断点续传 |

**模块级测试的核心机制——中间数据驱动：**
1. 每个模块测试加载上游的输出 JSON 作为输入
2. 调用模块的 `process()` 方法
3. 断言输出符合下游期望的 Pydantic Schema
4. 可选：与 `fixtures/intermediate/` 中的标准输出做 snapshot 对比
5. LLM 调用走缓存回放，TTS 调用走 Mock

**LLM 测试策略：**
- 首次运行：真实调用 LLM，自动保存响应到 `tests/fixtures/llm_cache/`
- 后续运行：从缓存回放，不调用 LLM（秒级完成）
- CI 环境：仅使用缓存，无 LLM 依赖

### Decision 7：配置管理用 Pydantic Settings

**选择：** `pydantic-settings`

**理由：**
- 类型安全的配置，IDE 自动补全
- 支持 `.env` 文件 + 环境变量 + YAML 多来源
- 与 FastAPI 生态统一
- 配置校验在启动时完成，不留到运行时报错

### Decision 8：异步策略——同步 process() + 异步 FastAPI + httpx.AsyncClient

**选择：** 模块 `process()` 方法保持同步，仅在 FastAPI Web 层和 TTS/LLM 网络调用使用 async

**替代方案：** 全异步 / 全同步 / 多进程

**理由：**
- 核心逻辑（文本解析、情感推断、音频拼接）为 CPU 密集型，async 无收益
- TTS/LLM 网络调用是 I/O 密集型，httpx.AsyncClient 实现并发
- 管线编排层用 `asyncio.Semaphore` 控制 TTS 并发数（默认 4）
- FastAPI 天然异步，Web 层无阻塞
- 避免全异步带来的"传染性 async"复杂度

**实现方式：**
```
Pipeline 编排（同步循环 + 异步 TTS 批次）
│
├── parser.process()     # 同步，CPU 密集
├── screenwriter.process()  # 同步，含 LLM 调用（内部 httpx 同步）
├── character.process()  # 同步
├── emotion.process()    # 同步
├── voice_bank.process() # 同步
├── TTS 批次            # async batch：asyncio.gather + Semaphore(4)
└── audio.process()      # 同步，CPU 密集
```

### Decision 9：容量规划

**100 章长篇小说（约 100 万字）估算：**

| 阶段 | 调用量 | 单次耗时 | 总耗时估算 | 磁盘空间 |
|------|--------|----------|------------|----------|
| 小说解析 | 1 次 | ~5s | 5s | 2MB JSON |
| 编剧（LLM） | 100 章 × 平均 3 次 | ~3s/次 | ~15min | 50MB JSON |
| 角色分析（LLM） | 1 次全书扫描 | ~30s | 30s | 1MB JSON |
| 情感推断（LLM） | ~5000 句 ÷ 批量20 = 250 次 | ~2s/次 | ~8min | 20MB JSON |
| TTS 合成 | ~5000 句 | ~3s/句 × 4 并发 | ~60min | 5GB WAV |
| 音频处理 | 100 章 | ~5s/章 | ~8min | 500MB M4B |
| **合计** | — | — | **~90min** | **~5.5GB** |

**优化杠杆：** 缓存回放避免重复 LLM 调用；TTS 并发数可调至 8（GPU 显存允许时）；龙套角色用规则引擎跳过 LLM。

## Risks / Trade-offs

| 风险 | 影响 | 缓解 |
|------|------|------|
| dependency-injector 学习曲线 | 初期开发稍慢 | 提供容器配置模板 + 注释 |
| LLM 输出不稳定导致测试不可重复 | CI 不稳定 | 缓存回放 + JSON Schema 校验 + 重试 |
| structlog JSON 日志可读性差 | 开发调试不便 | 开发环境用 `ConsoleRenderer`（彩色人类可读） |
| Protocol 无运行时检查 | 错误推迟到类型检查阶段 | pre-commit 强制 pyright 检查 |
| 模块过度解耦增加间接层 | 代码导航复杂度上升 | 容器定义文件作为"接线图"，一处看全局 |
| 长篇小说 LLM 调用量大 | 成本和时间 | 缓存 + 批量调用合并 + 龙套角色用规则引擎替代 LLM |
