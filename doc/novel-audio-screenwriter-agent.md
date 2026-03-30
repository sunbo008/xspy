# 文本小说 → 有声小说：编剧 Agent 设计

本文档定义「有声书编剧 Agent」的职责、输入输出、工作流与质量准则，与 [`novel-tts-design.md`](novel-tts-design.md) 中的章节分割、角色音色、情绪标注、TTS 合成链路对齐，作为上游「剧本结构化」环节的可实现规格。

---

## 1. 定位与边界

### 1.1 在系统中的位置

```
原始小说文本
    ↓
[章节分割]（已有：客户端 TXT/EPUB/PDF 解析器，见 novel-tts-design.md 3.1 节）
    ↓
┌────────────────────────────────┐
│      【编剧 Agent】← 本文档     │
│  内聚以下全部子任务：            │
│  · 对话 / 旁白 / 内心独白提取   │
│  · 角色识别与 speaker_slug 绑定  │
│  · 情绪标注（EmotionType）       │
│  · 听感改写与节奏控制            │
└────────────────────────────────┘
    ↓
结构化有声剧本（JSON：cast_registry + scenes[].utterances[]）
    ↓
[speaker_embedding 查表 + TTS 合成]（novel-tts-design.md 11.3 节）
    ↓
音频合并 → 成品有声书
```

### 1.2 Agent 做什么 / 不做什么

| 做 | 不做 |
|----|------|
| 将书面语转为**适合耳朵听**的口语文本 | 替代 TTS 引擎或声线克隆技术实现 |
| 划分**旁白 / 对白 / 内心独白**，并标注说话人 | 最终混音、BGM、专业拟音制作（可输出占位符） |
| 维护**角色表**（与 `speaker_slug`、参考音频映射一致） | 改写原著情节或擅自增删主线剧情 |
| 为每句可合成单元标注**情绪**（对齐 `EmotionType`） | 法律/版权审查（可提示高风险片段供人工复核） |
| 设计**停顿、分段长度**，避免单段过长导致 TTS 断句差 | 替代人工终审 |

**原则：** 改编服从原著信息与节奏；所有「听感优化」可在元数据中标记 `adaptation_note` 供人工回滚。

---

## 2. 角色定义（Persona）

**名称：** 有声小说编剧（Audio Drama Screenwriter）

**人设要点：**

- 熟悉广播剧、有声书口播习惯：短句、少从句堆砌、指代清晰。
- 区分「叙述层」与「角色层」，内心独白与旁白在剧本里类型不同，避免 TTS 用同一说话人误播。
- 尊重原文对话内容，可做**轻微**口语化（如「之於」→「对于」类仅当明显拗口时），重大改动需 `requires_review: true`。

**系统级约束（建议写入 Agent 系统提示）：**

1. 输出必须是可解析的结构化格式，不得仅返回大段散文。
2. 每个可合成单元对应一条 `utterance`，长度**推荐** 中文 **80～200 字/段**；**硬上限**为配置值（默认 300 字，可按引擎能力调整），超过硬上限必须拆分并保留顺序。
3. 情绪标签仅使用项目枚举（参见 `novel-tts-design.md` 11.2 节 `EmotionType`）。

---

## 3. 输入规格

### 3.1 最小输入

| 字段 | 说明 |
|------|------|
| `novel_id` / `novel_slug` | 与音频命名 `novel_slug` 一致 |
| `chapter_id` / `chapter_num` | 章节序号 |
| `chapter_title` | 章节标题（可选，用于元数据） |
| `raw_text` | 该章完整正文（UTF-8） |
| `style_profile` | 可选：题材（武侠/言情/科幻）、受众（全年龄/成人）、语速偏好 |

### 3.2 可选增强输入

- **角色白名单 / 别名表**：`{ "林晚": ["晚晚", "阿晚"], "旁白": ["叙述","画外音"] }`
- **已有音色配置路径**：与 JSON 中 `speaker_slug` 对齐
- **禁忌词与替换表**：平台合规（由产品提供）

---

## 4. 输出规格：有声剧本 Schema

建议主交付物为 **JSON**（或 YAML），便于下游直接生成 `AudioFileInfo` 与 TTS 请求。

### 4.1 顶层结构

```json
{
  "schema_version": "1.0",
  "novel_slug": "example_novel",
  "chapter_num": 1,
  "chapter_title": "第一章 风起",
  "cast_registry": [],
  "scenes": []
}
```

### 4.2 角色表 `cast_registry`

| 字段 | 类型 | 说明 |
|------|------|------|
| `speaker_id` | string | 稳定 ID，如 `char_lin_wan` |
| `speaker_slug` | string | 与 `novel-tts-design.md` 11.4 命名一致 |
| `display_name` | string | 原著展示名 |
| `role_type` | enum | `narrator` / `character` / `inner_voice` / `system`（系统音、章节头等） |
| `voice_ref` | string? | 参考音频路径或引擎内音色 key |
| `notes` | string? | 声线人设：年龄感、方言、语速建议 |

**旁白**必须有一条 `role_type: narrator`，`speaker_slug` 如 `narrator`。

### 4.3 场景 `scenes`

将一章拆为若干 `scene`（同时间地点或连续叙事），便于后期加环境音效占位。

| 字段 | 说明 |
|------|------|
| `scene_id` | 如 `ch01_sc03` |
| `setting` | 简短环境描述（给后期与 Agent 自检用） |
| `utterances` | 有序数组 |

### 4.4 话语单元 `utterance`（核心）

| 字段 | 类型 | 说明 |
|------|------|------|
| `seq` | int | 章内顺序，与 `seq_num` 对应 |
| `speaker_id` | string | 指向 `cast_registry` |
| `utterance_type` | enum | `narration` / `dialogue` / `inner_monologue` / `chapter_hook`（引子） |
| `text` | string | **送入 TTS 的最终文本**（已做听感处理） |
| `source_excerpt` | string? | 可选：对应原文片段，便于 diff |
| `emotion` | string | `happy` / `sad` / … 与 `EmotionType` 一致 |
| `pause_after_ms` | int? | 句后停顿建议（下游可映射静音） |
| `ssml_hints` | object? | 可选：`emphasis_words`, `break_ms`（若引擎支持） |
| `sfx_placeholder` | string? | 如 `door_knock`，无则省略 |
| `adaptation_note` | string? | 改编说明 |
| `requires_review` | bool | 是否需人工确认 |

---

## 5. 编剧工作流（Agent 内部阶段）

建议实现为**可多轮调用的子任务**（单模型多步或子 Agent），便于插拔与评测。

### 阶段 A：通读与角色建档

1. 扫描本章出场人物、称谓、对话引导语（「某某道」「心想」等）。
2. 合并同一人别名，写入 `cast_registry`。
3. 未出现姓名但有对话时，用 `speaker_id: unknown_spk_1` 并 `requires_review: true`。

### 阶段 B：场景切分

1. 按地点/时间跳跃/大段旁白后的对话转折点切 `scene`。
2. 每场景 `utterances` 保持时间顺序。

### 阶段 C：文本有声化改写

对 `narration`：

- 删减过度书面连接词，拆长句；保留关键信息与氛围描写。
- 避免「他」连指：必要时重复姓名或特征（听众所见无画面）。

对 `dialogue`：

- 保留引号内核心语义；可适度加语气词（「罢了」「呢」）若符合人物，不篡改冲突与信息。
- 去掉多余「说道」「问道」若 TTS 会念出（可移到元数据或省略）。

对 `inner_monologue`：

- 与旁白音色区分（不同 `speaker_id` 或同音色加 `utterance_type` 标记供下游处理）。

### 阶段 D：情绪与节奏

1. 结合上下文为每句 `utterance` 填 `emotion`；不确定则用 `neutral` 并 `requires_review: true`。
2. 设定 `pause_after_ms`：段落结束 300～800ms，激烈对话可缩短。

### 阶段 E：一致性与自检

执行第 6 节检查清单；失败则自动重试或标记 `requires_review`。

---

## 6. 质量检查清单（可自动化）

- [ ] 每个 `speaker_id` 均在 `cast_registry` 中有定义。
- [ ] 章内 `seq` 严格递增，无重复、无跳号。
- [ ] 无空 `text`；单段字数不超过硬上限（默认 300 字，与第 2 节系统约束一致）。
- [ ] `emotion` 均在允许枚举内。
- [ ] `narrator` 类型句未错误标成角色对白（除「叙述性假对话」已显式标注）。
- [ ] 敏感内容（暴力、性描写等）若保留，已 `requires_review: true` 并 `adaptation_note` 说明处理策略（淡化/隐去/原文直出）。

---

## 7. 与 TTS 流水线对接

1. 下游遍历 `scenes[].utterances[]`，按 `seq` 排序，映射为：

   - `AudioFileInfo`: `novel_slug`, `chapter_num`, `speaker_slug`（由 `speaker_id` 查表）, `emotion`, `seq_num`
   - TTS 文本： `text`

2. `inner_monologue` 若与旁白共用音色，由工程配置决定；编剧侧只保证类型与文本分离清晰。

3. `pause_after_ms` 与 `sfx_placeholder` 由 `audio_merger` 或后处理脚本消费（见 `novel-tts-design.md` 后续优化中的「音频后处理」「多角色对话合并」）。

---

## 8. 实现形态建议

| 形态 | 适用 |
|------|------|
| **单 LLM + 结构化输出**（JSON mode / tool call） | 快速原型、成本低 |
| **编排：解析 Agent + 编剧 Agent + 校对 Agent** | 质量要求高、长章节 |
| **MCP 工具** | 读原文文件、写剧本、查角色表、写审计日志 |

**提示词片段（系统）可包含：**

- 输出 Schema 的 JSON Schema 或示例（避免模型发明字段）。
- 「不得改变剧情因果与关键事实」的硬约束。
- 本书 `cast_registry` 已有条目（多章连载时每次传入累积表）。

---

## 9. 最小示例（节选）

```json
{
  "schema_version": "1.0",
  "novel_slug": "demo",
  "chapter_num": 1,
  "chapter_title": "夜雨",
  "cast_registry": [
    {
      "speaker_id": "nar",
      "speaker_slug": "narrator",
      "display_name": "旁白",
      "role_type": "narrator",
      "voice_ref": "voices/narrator_ref.wav"
    },
    {
      "speaker_id": "char_ah_qiang",
      "speaker_slug": "aqiang",
      "display_name": "阿强",
      "role_type": "character",
      "voice_ref": "voices/aqiang_ref.wav",
      "notes": "青年男性，语速中等"
    }
  ],
  "scenes": [
    {
      "scene_id": "ch01_sc01",
      "setting": "客栈内，雨夜",
      "utterances": [
        {
          "seq": 1,
          "speaker_id": "nar",
          "utterance_type": "narration",
          "text": "雨点敲在窗棂上，客栈里只剩一盏油灯摇摇晃晃。",
          "emotion": "calm",
          "pause_after_ms": 400
        },
        {
          "seq": 2,
          "speaker_id": "char_ah_qiang",
          "utterance_type": "dialogue",
          "text": "掌柜的，还有热汤吗？",
          "emotion": "neutral",
          "pause_after_ms": 200
        }
      ]
    }
  ]
}
```

---

## 10. 版本与维护

| 版本 | 说明 |
|------|------|
| `schema_version` `1.0` | 与本文档初版一致 |

若 `EmotionType` 或音频命名规范变更，应同步更新本文档第 3、4、7 节，并在 `novel-tts-design.md` 中增加对「编剧 Agent 输出」的交叉引用。

---

## 11. 延伸阅读

- 系统架构与 TTS：`doc/novel-tts-design.md`
- 部署：`doc/index-tts-vllm-deployment.md`
