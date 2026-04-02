# xspy 术语表 (Glossary)

本文档定义 xspy 项目中使用的领域术语，确保设计文档、代码和 Agent 之间语义一致。

---

| # | 术语 (Term) | 中文 | 定义 |
|---|------------|------|------|
| 1 | **Utterance** | 语句 | 剧本中最小的语音单元，对应一句对白或一段旁白 |
| 2 | **Screenplay** | 剧本 | 小说解析后的结构化脚本，包含按章节排列的语句序列 |
| 3 | **CastRegistry** | 角色注册表 | 全书角色信息汇总，含属性、关系、音色描述 |
| 4 | **CastEntry** | 角色条目 | CastRegistry 中的单个角色记录 |
| 5 | **CharacterProfile** | 角色画像 | 角色的推断属性：性别、年龄段、职业、性格、语言风格 |
| 6 | **RelationGraph** | 关系图谱 | 角色之间的关系网络（有向边） |
| 7 | **SpeakerRole** | 角色等级 | protagonist / supporting / minor / narrator |
| 8 | **EmotionType** | 情感类型 | 20 类情感分类枚举（基于 VAD 心理学模型） |
| 9 | **EmotionDetail** | 情感详情 | 包含 VAD 三维向量、强度和 TTS 参数的完整情感注解 |
| 10 | **VAD** | 效价-激活-支配 | Valence-Arousal-Dominance 三维情感空间 |
| 11 | **Paraverbal** | 副语言 | 非文字的语音表达：叹气、笑声、哭泣等 |
| 12 | **VoiceEntry** | 音色配置 | 将角色映射到 TTS 音色的配置项 |
| 13 | **VoiceAssignment** | 音色分配方案 | 全书角色到音色的完整映射 |
| 14 | **VoiceBank** | 音色库 | 可用音色的存储和检索系统 |
| 15 | **TTSRequest** | TTS 请求 | 发送给 TTS 引擎的单次合成请求 |
| 16 | **TTSResponse** | TTS 响应 | TTS 引擎返回的合成结果（含音频路径、时长等） |
| 17 | **ChapterAudio** | 章节音频 | 单个章节的完整合成音频及时间戳标记 |
| 18 | **AudioBook** | 有声书 | 最终输出的 M4B 有声书文件 |
| 19 | **IntermediateData** | 中间数据 | 管线各阶段持久化到磁盘的 JSON 数据，含 `_meta` 头 |
| 20 | **IntermediateMetaHeader** | 中间数据元头 | 中间数据文件的标准元信息：模块名、版本、时间戳、trace_id |
| 21 | **Pipeline** | 处理管线 | 从小说文件到有声书的完整处理流程（DAG 调度） |
| 22 | **PipelineInput** | 管线输入 | 管线编排器的输入：小说文件路径、配置覆写、章节过滤 |
| 23 | **PipelineResult** | 管线结果 | 管线编排器的输出：有声书、章节结果、统计 |
| 24 | **NovelParser** | 小说解析器 | 将 TXT/EPUB/PDF 文件解析为结构化章节的模块 |
| 25 | **ScreenwriterAgent** | 编剧 Agent | 将章节文本转化为结构化剧本（对白分离、说话人识别） |
| 26 | **CharacterEngine** | 角色引擎 | 分析并推断角色属性、关系图谱的模块 |
| 27 | **EmotionSystem** | 情感系统 | 基于上下文推断每句话的情感类型和强度 |
| 28 | **AudioProcessor** | 音频处理器 | 合并语音片段、加入副语言音效、均衡化、M4B 封装 |
| 29 | **ModelRouter** | 模型路由器 | 按任务类型将请求路由到最优 LLM 模型 |
| 30 | **NovelSlug** | 小说标识符 | 小说的 URL 安全短名，用于目录和文件命名 |
| 31 | **Checkpoint** | 检查点 | 管线断点续传数据，记录已完成的阶段和章节 |
| 32 | **Protocol** | 协议 | Python `typing.Protocol` 定义的模块接口契约 |
| 33 | **DI Container** | 依赖注入容器 | 使用 dependency-injector 管理模块实例的中心注册表 |
| 34 | **trace_id** | 追踪 ID | 12 位十六进制串，贯穿单次管线运行的所有日志 |
| 35 | **LLM Cache Replay** | LLM 缓存回放 | 测试时回放录制的 LLM 响应，确保确定性 |
