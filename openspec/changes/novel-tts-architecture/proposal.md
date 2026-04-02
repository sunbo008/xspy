## Why

当前项目已完成详细的文档设计（13 篇设计文档），但尚无任何可运行代码。需要将设计落地为一个**低耦合高内聚、模块可独立开发/替换/测试**的 Python 工程。核心诉求：

1. **AI 原生开发**：系统大量依赖 LLM（编剧 Agent、角色分析、情感推断），需要面向 AI 的架构设计——Prompt 可配置、LLM 响应可缓存可回放、输出可结构化校验
2. **快速迭代**：任意模块（解析器、TTS 引擎、情绪适配器）可独立替换，不影响其他模块
3. **可观测性**：全链路结构化日志 + 追踪，定位问题时能精确到某个角色的某句话的某次 TTS 调用
4. **自测闭环**：设计 → 开发 → 测试 → 验证设计的完整闭环，每个模块有契约测试保证接口不被破坏

## What Changes

- **新建完整 Python 工程骨架**：`src/xspy/` 下 9 个子包，`pyproject.toml`，CLI 入口
- **引入依赖注入容器**：基于 `dependency-injector` 实现模块间解耦，任何模块可通过配置替换实现
- **引入统一日志框架**：基于 `structlog` 的结构化日志系统，支持 JSON 输出、请求级 trace_id、模块级上下文绑定
- **引入契约优先的接口设计**：每个模块定义 Protocol（抽象接口），实现与接口分离
- **引入端到端流水线编排**：`pipeline.py` 按 DAG 编排全部 Phase，支持部分重跑
- **引入测试基础设施**：pytest + fixtures + LLM mock + 快照测试，每个模块有独立测试目录
- **引入 CI 质量门禁**：pre-commit hooks（ruff lint + format + type check）+ GitHub Actions

## Capabilities

### New Capabilities

- `core-interfaces`: 全局共享的 Protocol 接口定义、数据模型（Chapter/EmotionType/TTSRequest 等）、配置管理（Pydantic Settings）
- `dependency-injection`: 依赖注入容器，管理所有模块的生命周期和依赖关系，支持配置切换实现
- `structured-logging`: 结构化日志系统（structlog），trace_id 链路追踪，模块级上下文绑定，JSON/Console 双输出
- `novel-parser`: 小说解析器模块——TXT/EPUB/PDF 解析、编码检测、章节分割、文本清洗
- `screenwriter-agent`: 编剧 Agent——对话提取、角色绑定、有声化改写、场景分割、剧本 JSON 输出
- `character-engine`: 角色分析引擎——角色发现合并、画像推断、关系图谱、语气词注入、一致性校验
- `emotion-system`: 情绪控制系统——EmotionType 枚举、VAD 模型、叙述规则引擎、情绪平滑、TTS 引擎适配器
- `voice-bank`: 角色音色库——音色注册/存储、自动生成（VoiceDesign→Clone）、模板池、区分度校验
- `tts-client`: TTS API 客户端——Index-TTS/Qwen3-TTS 多引擎封装、重试/降级、健康检查
- `audio-processor`: 音频处理器——命名规范、章节合并、副语言拼接、后处理、M4B 有声书组装
- `task-manager`: 任务管理器——DAG 调度、并发控制、进度追踪、断点续传
- `web-ui`: Web UI——FastAPI 后端 + Vue 3 前端，全流程图形化操作
- `pipeline-orchestrator`: 端到端流水线编排——Phase 顺序执行、部分重跑、全局状态管理
- `testing-infrastructure`: 测试基础设施——pytest 配置、LLM Mock/Replay、快照测试、契约测试

### Modified Capabilities

## Impact

- **代码**：从零新建 `src/xspy/` 全部 Python 代码、`frontend/` Vue 代码、`tests/` 测试代码
- **依赖**：新增 Python 依赖（structlog、dependency-injector、pydantic、fastapi、pydub、ebooklib、httpx 等）+ 前端依赖（Vue 3、Element Plus、Pinia）
- **构建**：新增 `pyproject.toml`、`ruff.toml`、`.pre-commit-config.yaml`、GitHub Actions workflow
- **数据**：运行时产物目录 `data/`（voice_bank/output/checkpoints/cache）需 .gitignore
- **文档**：现有 `doc/*.md` 设计文档保持不变，作为需求规格的权威来源
