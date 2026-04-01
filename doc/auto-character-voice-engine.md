# 全自动角色分析与智能配音引擎设计

> 本文档定义「角色分析引擎」的完整自动化流水线——从原始小说文本中自动提取角色画像、匹配音色、推断情感、注入语气词，最终输出可直接送入 TTS 的增强剧本。
>
> 关联文档：
> - [`novel-tts-design.md`](novel-tts-design.md) — 系统架构与 TTS 管线
> - [`novel-audio-screenwriter-agent.md`](novel-audio-screenwriter-agent.md) — 编剧 Agent 基础设计

---

## 1. 系统全景

```
原始小说文本（全本 / 多章）
    ↓
┌──────────────────────────────────────────────────────────┐
│               Phase 1: 全局角色建档                        │
│  ┌────────────────┐   ┌────────────────┐                 │
│  │ 角色发现与合并   │──▶│ 角色画像推断     │                 │
│  │ (Character      │   │ (Character      │                 │
│  │  Discovery)     │   │  Profiling)     │                 │
│  └────────────────┘   └───────┬────────┘                 │
│                               ↓                           │
│                    ┌────────────────┐                     │
│                    │ 角色关系图谱     │                     │
│                    │ (Relationship   │                     │
│                    │  Graph)         │                     │
│                    └───────┬────────┘                     │
└────────────────────────────┼─────────────────────────────┘
                             ↓
┌──────────────────────────────────────────────────────────┐
│               Phase 2: 音色设计与绑定                      │
│  ┌────────────────┐   ┌────────────────┐                 │
│  │ 画像→音色描述    │──▶│ 音色生成/匹配    │                 │
│  │ (Profile to     │   │ (Voice Design   │                 │
│  │  Voice Desc)    │   │  / Clone)       │                 │
│  └────────────────┘   └───────┬────────┘                 │
│                               ↓                           │
│                    ┌────────────────┐                     │
│                    │ 角色音色库       │                     │
│                    │ (Voice Bank)    │                     │
│                    └───────┬────────┘                     │
└────────────────────────────┼─────────────────────────────┘
                             ↓
┌──────────────────────────────────────────────────────────┐
│               Phase 3: 逐章剧本生成（编剧 Agent 增强版）    │
│  ┌────────────────┐   ┌────────────────┐                 │
│  │ 上下文情感推断   │──▶│ 语气词/副语言    │                 │
│  │ (Contextual     │   │  注入            │                 │
│  │  Emotion)       │   │ (Paraverbal     │                 │
│  │                 │   │  Injection)     │                 │
│  └────────────────┘   └───────┬────────┘                 │
│                               ↓                           │
│                    ┌────────────────┐                     │
│                    │ 一致性校验       │                     │
│                    │ (Consistency    │                     │
│                    │  Validator)     │                     │
│                    └───────┬────────┘                     │
└────────────────────────────┼─────────────────────────────┘
                             ↓
                增强版结构化剧本（JSON）
                             ↓
                    TTS 合成 → 有声书
```

---

## 2. Phase 1：全局角色建档

### 2.1 角色发现与合并（Character Discovery）

**目标：** 从全书文本中发现所有出场角色，合并同一人的不同称谓。

**LLM 提示策略：** 分章扫描 + 全局合并

```
第一轮（逐章扫描）：
  输入：单章文本
  输出：本章出现的角色列表，包含：
    - 所有称谓/别名（"林晚"、"晚晚"、"阿晚"、"林姑娘"）
    - 首次出场的上下文片段
    - 对话频次统计

第二轮（全局合并）：
  输入：所有章节的角色列表
  输出：去重合并后的全局角色表
    - 主角 / 配角 / 龙套 分级
    - 每个角色的别名列表
    - 跨章出场统计
```

**合并规则：**

| 规则 | 说明 | 示例 |
|------|------|------|
| 称谓链推断 | 同一段文本中的指代关系 | "林晚笑了笑，晚晚……" → 同一人 |
| 对话引导语 | 「某某说」紧跟对话，绑定说话人 | "阿强说道：'走吧'" → 阿强 |
| 关系称谓推断 | 通过关系词关联 | "她的丈夫赵明" → 赵明=她丈夫 |
| 代词消解 | 上下文代词回指 | 连续对话中的"他"、"她" |

**角色分级标准：**

| 等级 | 标准 | 配音策略 |
|------|------|----------|
| **主角** | 出场 >50% 章节，对话量 top 3 | 独立定制音色，精细情感控制 |
| **重要配角** | 出场 10-50% 章节 | 独立音色，标准情感控制 |
| **次要角色** | 出场 3-10% 章节 | 从音色模板库匹配 |
| **龙套** | 出场 <3 章 | 共享通用音色池 |

### 2.2 角色画像推断（Character Profiling）

**目标：** 从文本线索自动推断每个角色的个人属性。

**推断维度与文本线索映射：**

| 属性 | 推断来源 | 示例 |
|------|----------|------|
| **性别** | 称谓（"她"/"他"）、名字特征、关系词（"妻子"/"丈夫"） | "她转身离去" → 女性 |
| **年龄段** | 称谓（"老头"/"小伙子"）、自述、外貌描写、行为习惯 | "白发苍苍的老者" → 老年 |
| **职业** | 直接描写、工作场景、专业术语使用、社会地位线索 | "穿着白大褂走进诊室" → 医生 |
| **性格** | 对话风格、行为模式、他人评价、内心独白 | 频繁使用感叹句 → 情绪外露型 |
| **社会地位** | 称谓敬语、居住环境、消费行为、他人态度 | "府上"、"大人" → 上层阶级 |
| **语言风格** | 口头禅、用词习惯、句式长短、方言特征 | 频繁使用"嗯哼" → 随性 |
| **情感基调** | 跨章节的总体情绪趋势 | 多数对话偏忧郁 → 基调=忧郁 |

**输出结构：增强版 `cast_registry`**

```json
{
  "speaker_id": "char_lin_wan",
  "speaker_slug": "linwan",
  "display_name": "林晚",
  "aliases": ["晚晚", "阿晚", "林姑娘"],
  "role_type": "character",
  "role_level": "protagonist",

  "profile": {
    "gender": "female",
    "age_range": "young_adult",
    "age_estimate": "22-25",
    "occupation": "书店店员",
    "social_class": "middle",
    "personality_tags": ["温柔", "内敛", "坚韧"],
    "speech_style": {
      "tempo": "moderate",
      "vocabulary_level": "literary",
      "typical_sentence_length": "medium",
      "dialect": null,
      "catchphrases": ["算了吧", "也好"],
      "politeness_level": "polite"
    },
    "emotional_baseline": "calm",
    "evidence": [
      { "chapter": 1, "excerpt": "她低头整理着书架，声音轻轻的", "inferred": "gender=female, personality=内敛" },
      { "chapter": 3, "excerpt": "二十三岁的林晚第一次觉得生活如此沉重", "inferred": "age=23" }
    ]
  },

  "voice_ref": null,
  "voice_description": null,
  "notes": null
}
```

**年龄段枚举：**

| 枚举值 | 年龄范围 | 音色特征 |
|--------|----------|----------|
| `child` | 0-12 | 音高偏高，语速快，天真感 |
| `teenager` | 13-17 | 带青春感，可能有不稳定音高 |
| `young_adult` | 18-30 | 清亮，有活力 |
| `middle_aged` | 31-55 | 沉稳，音域中等 |
| `elderly` | 56+ | 低沉/沙哑，语速偏慢 |

### 2.3 角色关系图谱（Relationship Graph）

**目标：** 理解角色间的关系，为对话语气推断提供上下文。

```json
{
  "relationships": [
    {
      "from": "char_lin_wan",
      "to": "char_zhao_ming",
      "relation": "lover",
      "sentiment": "positive",
      "dynamic": "evolving",
      "notes": "前 20 章为暗恋，第 21 章确认关系"
    },
    {
      "from": "char_lin_wan",
      "to": "char_wang_boss",
      "relation": "employer_employee",
      "sentiment": "neutral_negative",
      "dynamic": "stable",
      "notes": "林晚对王老板有不满但隐忍"
    }
  ]
}
```

**关系类型枚举：** `family`、`lover`、`friend`、`rival`、`enemy`、`mentor_student`、`employer_employee`、`stranger`、`ally`

**关系对情感推断的影响：**

- 恋人间的对话 → 倾向 `romantic`、`happy`、`shy` 情感
- 敌对关系的对话 → 倾向 `angry`、`sarcastic`、`cold` 情感
- 师生/上下级 → 语气恭敬度不同，影响 TTS 的 instruct 参数

---

## 3. Phase 2：音色设计与绑定

### 3.1 画像到音色描述的自动转换

**核心思路：** 将角色画像的结构化属性，通过模板 + LLM 转换为 Qwen3-TTS VoiceDesign 可以理解的自然语言音色描述。

**转换模板：**

```python
VOICE_DESCRIPTION_TEMPLATE = """
请为以下小说角色设计一个音色描述，用于 TTS 语音合成：

角色名：{display_name}
性别：{gender}
年龄段：{age_range}（约 {age_estimate} 岁）
职业：{occupation}
性格特征：{personality_tags}
说话风格：{speech_style_summary}
情感基调：{emotional_baseline}

要求：
1. 用一段自然语言描述这个角色说话时的声音特征
2. 包含：音高、音色质感、语速、气息感、情感色彩
3. 不超过 50 字
4. 避免与以下已有角色的音色描述雷同：
{existing_voice_descriptions}
"""
```

**自动生成示例：**

| 角色 | 画像关键词 | 生成的音色描述 |
|------|-----------|--------------|
| 林晚（女，23岁，书店店员，温柔内敛） | female + young_adult + calm | "23岁年轻女性，声音轻柔清澈，语速偏慢，带有文艺气质的书卷气" |
| 赵明（男，28岁，刑警，正直刚毅） | male + young_adult + confident | "28岁青年男性，嗓音低沉有力，语速中等偏快，说话干脆利落有威严感" |
| 王老板（男，55岁，书店老板，市侩圆滑） | male + middle_aged + sarcastic | "55岁中年男性，声音略带沙哑，说话圆滑带笑意，语调起伏大" |
| 小丫头（女，8岁，邻居小孩） | female + child + happy | "8岁小女孩，声音清脆高亢，语速快，天真烂漫带奶声奶气" |

### 3.2 音色生成与固化流程

```
角色画像
    ↓
LLM 生成音色描述（自然语言）
    ↓
┌─────────────────────────────────────────┐
│     Qwen3-TTS VoiceDesign 模式           │
│     输入：音色描述文本                     │
│     输出：参考音频片段（3-5秒）            │
├─────────────────────────────────────────┤
│     质量校验（可选人工试听）               │
│     · 音色是否符合角色设定？               │
│     · 与其他角色是否有足够区分度？          │
├─────────────────────────────────────────┤
│     通过校验 ──→ VoiceClone 模式固化       │
│     生成 voice_clone_prompt（可复用）      │
└─────────────────────────────────────────┘
    ↓
写入角色音色库（data/voice_bank/）
```

**音色库目录结构：**（详见 [`module-voice-bank.md`](module-voice-bank.md) §4）

```
data/voice_bank/
├── {novel_slug}/
│   ├── voice_registry.json         # 音色注册表
│   ├── linwan/
│   │   ├── reference.wav           # 参考音频
│   │   ├── voice_clone_prompt.bin  # 克隆特征（可复用）
│   │   └── metadata.json           # 画像 + 音色描述
│   ├── zhaoming/
│   │   ├── reference.wav
│   │   ├── voice_clone_prompt.bin
│   │   └── metadata.json
│   └── narrator/
│       ├── reference.wav
│       └── voice_clone_prompt.bin
```

### 3.3 音色区分度保证

**问题：** 同性别、相近年龄的角色可能生成相似音色。

**解决策略：**

1. **差异化描述注入**：在生成音色描述时，明确要求与已有角色区分
2. **音色特征向量比对**：生成后计算 speaker embedding 余弦相似度，相似度 > 0.85 时触发重新生成
3. **人工兜底**：`requires_review: true` 标记区分度不足的音色对，供人工调整

---

## 4. Phase 3：上下文情感推断引擎

### 4.1 多层情感分析模型

传统方案仅看当前句子内容判断情感，但小说中情感高度依赖上下文。本方案采用**三层分析**：

```
┌───────────────────────────────────────┐
│  Layer 1: 宏观情感弧线（Chapter Arc）   │
│  输入：全章概要                         │
│  输出：章节情感走势（起承转合）          │
│  粒度：场景级                           │
├───────────────────────────────────────┤
│  Layer 2: 场景情感上下文（Scene Context）│
│  输入：当前场景 + 前一场景摘要           │
│  输出：场景基调、紧张度、节奏            │
│  粒度：场景级                           │
├───────────────────────────────────────┤
│  Layer 3: 单句情感精标（Utterance）      │
│  输入：当前句 + 前后 3 句上下文          │
│  输出：精确情感标签 + 强度 + 语气词建议  │
│  粒度：utterance 级                     │
└───────────────────────────────────────┘
```

### 4.2 情感推断的上下文窗口

```python
class EmotionContext:
    """情感推断的上下文信息"""

    chapter_arc: str            # 本章情感走势摘要
    scene_mood: str             # 当前场景基调
    scene_tension: float        # 紧张度 0.0-1.0

    speaker_profile: dict       # 说话人画像（性格、情感基调）
    speaker_recent_emotions: list  # 该角色最近 5 句的情感变化

    relationship_to_listener: str  # 与对话对象的关系
    listener_last_emotion: str     # 对话对象上一句的情感

    preceding_text: str         # 前 3 句文本
    current_text: str           # 当前句
    following_text: str         # 后 3 句文本

    narration_cues: list        # 叙述中的情感暗示
                                # 如 "他咬紧牙关" → angry
                                # 如 "眼眶微微泛红" → sad
```

### 4.3 叙述线索 → 情感映射表

小说中大量情感信息隐藏在叙述描写中，而非对话本身。

| 叙述描写模式 | 推断情感 | 强度 |
|-------------|----------|------|
| "笑了/笑着说/忍不住笑" | happy | 0.6-0.8 |
| "大笑/哈哈大笑/笑得前仰后合" | happy | 0.9-1.0 |
| "苦笑/勉强笑了笑" | sad + forced_smile | 0.5 |
| "叹了口气/长叹一声" | sad / resigned | 0.6 |
| "咬紧牙关/攥紧拳头" | angry | 0.7-0.9 |
| "声音颤抖/哆嗦着说" | fear / sad | 0.7 |
| "低下头/沉默良久" | sad / contemplative | 0.5 |
| "瞪大了眼/愣住了" | surprise | 0.8 |
| "冷冷地/淡淡地" | cold / indifferent | 0.6 |
| "急切地/连忙说" | anxious / urgent | 0.7 |
| "轻声/小声说" | gentle / secretive | 0.5 |
| "吼道/怒喝" | angry | 0.9-1.0 |
| "嘟囔/嘀咕" | annoyed / reluctant | 0.4 |
| "哽咽/泣不成声" | grief | 0.9 |

### 4.4 增强版情感输出

在原有 `emotion` 字段基础上，新增精细控制字段：

```json
{
  "seq": 5,
  "speaker_id": "char_lin_wan",
  "utterance_type": "dialogue",
  "text": "算了……你走吧。",
  "emotion": "sad",
  "emotion_detail": {
    "primary": "sad",
    "secondary": "resigned",
    "intensity": 0.7,
    "valence": -0.6,
    "arousal": 0.3,
    "narration_cue": "她别过脸去，声音有些发颤",
    "tts_instruct": "用略带颤抖的、压抑悲伤的语气说，语速放慢，尾音下沉"
  }
}
```

**`emotion_detail` 字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `primary` | string | 主要情感（对齐 EmotionType） |
| `secondary` | string? | 次要情感（复合情感场景） |
| `intensity` | float | 情感强度 0.0-1.0 |
| `valence` | float | 情感正负向 -1.0 ~ +1.0 |
| `arousal` | float | 激活度 0.0-1.0（低=平静 高=激动） |
| `narration_cue` | string? | 触发该情感判断的叙述线索 |
| `tts_instruct` | string | 给 Qwen3-TTS instruct 参数的自然语言指令 |

---

## 5. 语气词与副语言注入系统

### 5.1 副语言类型定义

| 类型 | 标签 | TTS 实现方式 | 典型触发场景 |
|------|------|------------|------------|
| 笑声 | `[laughter]` | 文本内嵌 / 音效拼接 | 叙述写"笑了"、对话含"哈哈" |
| 轻笑 | `[chuckle]` | TTS instruct: "带着轻笑的语气" | "忍不住笑了一下" |
| 叹气 | `[sigh]` | 在句前插入叹气音效 | "叹了口气"、"唉" |
| 哭泣 | `[sobbing]` | TTS instruct: "带哭腔" | "哽咽着说"、"泪流满面" |
| 喘息 | `[panting]` | 音效拼接 | 奔跑后、紧张场景 |
| 吞咽 | `[gulp]` | 音效拼接 | 紧张、恐惧 |
| 清嗓 | `[throat_clear]` | 音效拼接 | 正式发言前 |
| 冷哼 | `[scoff]` | TTS instruct: "带着不屑的冷哼" | "哼"、轻蔑场景 |
| 惊叫 | `[gasp]` | 文本内嵌 | 受惊、震惊 |
| 吸鼻子 | `[sniff]` | 音效拼接 | 哭泣后、感动 |
| 犹豫停顿 | `[hesitation]` | TTS 文本插入"……" + pause | "欲言又止"、纠结 |
| 打断 | `[interruption]` | 前句截断 + pause 缩短 | "话还没说完——" |

### 5.2 自动注入规则

**注入时机判断：** LLM 基于三类线索决定是否注入语气词。

```
线索类型 1: 叙述动作描写
  "他叹了口气，说道：" → 在对话文本前注入 [sigh]
  "她忍不住笑出声来" → 在对话文本前注入 [laughter]

线索类型 2: 对话文本内容
  "哈哈哈，太好了！" → 保留文本中的笑声，TTS instruct 加"笑着说"
  "唉……算了。" → 在"唉"前注入 [sigh]

线索类型 3: 上下文情感突变
  前一句 calm → 当前句 surprise → 在句前注入 [gasp]
  前一句 angry → 当前句 sad → 可能注入 [sigh] 或 [sobbing]
```

### 5.3 注入后的 utterance 结构

```json
{
  "seq": 12,
  "speaker_id": "char_lin_wan",
  "utterance_type": "dialogue",
  "text": "算了……你走吧。",
  "emotion": "sad",
  "emotion_detail": {
    "primary": "sad",
    "secondary": "resigned",
    "intensity": 0.7,
    "tts_instruct": "用疲惫而悲伤的语气说，语速偏慢"
  },
  "paraverbals": [
    {
      "type": "sigh",
      "position": "before",
      "source": "narration",
      "narration_cue": "她叹了口气",
      "implementation": "audio_splice",
      "audio_asset": "resources/sfx/sigh/female_soft.wav"
    },
    {
      "type": "hesitation",
      "position": "inline",
      "source": "text_content",
      "implementation": "tts_pause",
      "pause_ms": 600
    }
  ],
  "pause_after_ms": 500
}
```

### 5.4 实现策略矩阵

不同 TTS 引擎对副语言的支持能力不同，需要适配：

| 副语言类型 | Qwen3-TTS 实现 | Index-TTS 实现 | 通用后备方案 |
|-----------|---------------|---------------|-------------|
| 笑声 | instruct: "笑着说" | 无直接支持 | 音效文件拼接 |
| 叹气 | instruct: "叹气后说" | 无直接支持 | sfx 拼接在句前 |
| 哭腔 | instruct: "带哭腔说" | 无直接支持 | instruct 控制 + sfx |
| 停顿 | 文本中插入 `……` | 文本中插入 `……` | silence 音频拼接 |
| 惊叫 | instruct: "惊讶地" | 无直接支持 | sfx 拼接 |
| 冷哼 | instruct: "不屑地" | 无直接支持 | sfx 拼接 |

**音效资源库：**（位于 `resources/sfx/`）

```
resources/sfx/
├── laughter/
│   ├── male_hearty.wav
│   ├── male_chuckle.wav
│   ├── female_giggle.wav
│   └── female_chuckle.wav
├── sigh/
│   ├── male_deep.wav
│   ├── male_light.wav
│   ├── female_soft.wav
│   └── female_heavy.wav
├── gasp/
│   ├── male_surprise.wav
│   └── female_surprise.wav
├── sobbing/
│   ├── male_restrained.wav
│   └── female_soft.wav
└── ...
```

---

## 6. 对话一致性分析引擎

### 6.1 多维度一致性校验

**目标：** 确保跨章节的角色表现连贯，避免"角色崩塌"。

| 校验维度 | 校验内容 | 示例 |
|----------|----------|------|
| **人称一致性** | 同一角色的自称、他称保持一致 | 张三全书自称"我"，不应突然变成"在下" |
| **语言风格一致性** | 角色的用词习惯、句式特点跨章稳定 | 粗犷角色不应突然使用文雅措辞 |
| **情感连贯性** | 情感变化要有合理的上下文支撑 | 刚经历亲人去世，下一章不应毫无过渡地欢乐 |
| **关系一致性** | 角色间的称谓和态度与关系发展匹配 | 从"你"到"你"到"亲爱的"要有发展过程 |
| **知识一致性** | 角色不应说出其不该知道的信息 | 不在场的角色不应提到未被告知的事件 |

### 6.2 跨章节角色状态追踪

```json
{
  "character_state_tracker": {
    "char_lin_wan": {
      "chapter_states": [
        {
          "chapter": 1,
          "mood_summary": "平静，对生活有些倦怠",
          "key_events": ["日常工作", "偶遇赵明"],
          "relationship_changes": [],
          "emotional_arc": "calm → curious"
        },
        {
          "chapter": 5,
          "mood_summary": "逐渐对赵明产生好感，但内心纠结",
          "key_events": ["与赵明共进晚餐", "得知赵明身份"],
          "relationship_changes": [
            { "target": "char_zhao_ming", "from": "stranger", "to": "acquaintance" }
          ],
          "emotional_arc": "nervous → happy → conflicted"
        }
      ],
      "global_emotional_trajectory": "从麻木到重新燃起对生活的热情"
    }
  }
}
```

### 6.3 一致性校验 LLM Prompt

```
你是一个有声书质量审核员。请校验以下角色在本章中的表现是否与其历史状态一致。

角色画像：{character_profile}
角色在前几章的状态：{recent_chapter_states}
角色关系图谱：{relationships}

本章该角色的所有 utterances：
{current_chapter_utterances}

请检查：
1. 说话风格是否符合角色画像？如有偏差，标记具体 seq 编号
2. 情感变化是否有合理支撑？是否存在突兀的情感跳跃？
3. 称谓使用是否正确？
4. 是否有角色不应知道的信息泄漏？

输出格式：
{
  "is_consistent": true/false,
  "issues": [
    {
      "seq": 15,
      "issue_type": "emotion_jump",
      "description": "从极度悲伤直接变为开心，缺少过渡",
      "suggestion": "在 seq 14-15 之间增加旁白过渡，或将 seq 15 的情感改为苦笑"
    }
  ]
}
```

---

## 7. 完整处理流水线

### 7.1 首次处理（全书建档）

```python
# 伪代码：首次运行时执行全书分析
def process_novel_first_time(novel_text: str, novel_slug: str):
    # Step 1: 章节分割
    chapters = chapter_splitter.split(novel_text)

    # Step 2: 全局角色发现（逐章扫描 + 合并）
    per_chapter_characters = []
    for chapter in chapters:
        chars = llm.extract_characters(chapter.text)
        per_chapter_characters.append(chars)

    global_cast = llm.merge_characters(per_chapter_characters)

    # Step 3: 角色画像推断（传入全书上下文）
    for character in global_cast:
        character.profile = llm.infer_profile(
            character=character,
            appearances=get_all_appearances(character, chapters)
        )

    # Step 4: 角色关系图谱构建
    relationships = llm.build_relationship_graph(global_cast, chapters)

    # Step 5: 自动音色生成
    voice_bank = VoiceBank(novel_slug)
    for character in global_cast:
        voice_desc = llm.generate_voice_description(
            character.profile,
            existing_voices=voice_bank.get_all_descriptions()
        )
        reference_audio = qwen_tts.voice_design(voice_desc)
        voice_clone_prompt = qwen_tts.create_clone_prompt(reference_audio)
        voice_bank.register(character.speaker_slug, voice_desc, voice_clone_prompt)

    # 保存全局角色档案
    save_novel_profile(novel_slug, global_cast, relationships, voice_bank)
```

### 7.2 逐章生成（增强版编剧 Agent）

```python
# 伪代码：逐章生成增强剧本
def process_chapter(chapter, novel_profile):
    # Step 1: 基础编剧（已有的编剧 Agent 流程）
    script = screenwriter_agent.generate(
        chapter_text=chapter.text,
        cast_registry=novel_profile.cast,
        style_profile=novel_profile.style
    )

    # Step 2: 上下文情感增强
    for scene in script.scenes:
        scene_context = build_scene_context(
            scene, chapter, novel_profile
        )
        for utt in scene.utterances:
            emotion_ctx = EmotionContext(
                chapter_arc=chapter.emotion_arc,
                scene_mood=scene_context.mood,
                speaker_profile=novel_profile.get_profile(utt.speaker_id),
                relationship=novel_profile.get_relationship(
                    utt.speaker_id, get_listener(scene, utt)
                ),
                preceding_text=get_preceding(scene, utt, n=3),
                following_text=get_following(scene, utt, n=3),
                narration_cues=extract_narration_cues(scene, utt)
            )
            utt.emotion_detail = llm.infer_emotion(utt, emotion_ctx)

    # Step 3: 语气词注入
    for scene in script.scenes:
        for utt in scene.utterances:
            utt.paraverbals = paraverbal_injector.analyze(
                utt, scene, novel_profile
            )

    # Step 4: TTS 指令生成
    for scene in script.scenes:
        for utt in scene.utterances:
            utt.emotion_detail.tts_instruct = llm.generate_tts_instruct(
                utt.emotion_detail,
                novel_profile.get_profile(utt.speaker_id)
            )

    # Step 5: 一致性校验
    issues = consistency_validator.check(
        script,
        novel_profile,
        chapter_history=get_chapter_history(chapter.num)
    )
    for issue in issues:
        script.utterances[issue.seq].requires_review = True
        script.utterances[issue.seq].review_notes = issue.description

    # Step 6: 更新角色状态
    novel_profile.update_chapter_state(chapter.num, script)

    return script
```

### 7.3 LLM 调用策略

由于全流程涉及大量 LLM 调用，需要合理设计调用策略以控制成本和延迟：

| 阶段 | LLM 调用次数 | 推荐策略 |
|------|-------------|----------|
| 角色发现（逐章） | N 章 × 1 次 | 批量调用，可并行 |
| 角色合并 | 1 次 | 全局一次性 |
| 画像推断 | M 角色 × 1 次 | 可并行 |
| 关系图谱 | 1 次 | 全局一次性 |
| 音色描述 | M 角色 × 1 次 | 串行（需避免重复） |
| 逐章编剧 | N 章 × 1 次 | 按章串行 |
| 情感推断 | N 章 × K 句 | **合并到编剧调用中**，避免逐句调用 |
| 语气词注入 | 同上 | **合并到编剧调用中** |
| 一致性校验 | N 章 × 1 次 | 每章生成后立即校验 |

**优化方案：** 将阶段 C（编剧生成）、D（情感推断）、语气词注入合并为单次 LLM 调用，通过精心设计的系统提示让 LLM 一次性输出包含情感细节和语气词的完整剧本 JSON。

---

## 8. 实现优先级

| 阶段 | 内容 | 依赖 | 优先级 |
|------|------|------|--------|
| P0 | 角色发现 + 画像推断 | LLM（Qwen3.5） | 最高 |
| P0 | 增强情感推断（上下文窗口） | LLM | 最高 |
| P1 | 语气词注入系统 | P0 + TTS 引擎适配 | 高 |
| P1 | 音色自动设计与绑定 | P0 + Qwen3-TTS VoiceDesign | 高 |
| P2 | 角色关系图谱 | P0 | 中 |
| P2 | 跨章一致性校验 | P0 + 角色状态追踪 | 中 |
| P3 | 音效资源库 | 音效素材收集 | 低 |
| P3 | 音色区分度自动校验 | Speaker embedding 比对工具 | 低 |

---

## 9. 与现有系统的整合点

| 现有模块 | 整合方式 |
|----------|----------|
| `novel-tts-design.md` 11.2 EmotionType | 新增 `emotion_detail` 作为 emotion 的扩展，保持向后兼容 |
| `novel-tts-design.md` 11.4 音频命名 | 不变，`emotion` 字段仍用主情感标签 |
| `novel-audio-screenwriter-agent.md` cast_registry | 新增 `profile` 和 `aliases` 字段 |
| `novel-audio-screenwriter-agent.md` utterance | 新增 `emotion_detail` 和 `paraverbals` 字段 |
| TTS 合成层 | 新增 `tts_instruct` 参数传递给 Qwen3-TTS |
| 音频后处理 | 新增 paraverbal 音效拼接步骤 |

---

## 10. 扩展版 Schema 示例（完整）

```json
{
  "schema_version": "2.0",
  "novel_slug": "silent_bookstore",
  "chapter_num": 5,
  "chapter_title": "第五章 重逢",

  "cast_registry": [
    {
      "speaker_id": "nar",
      "speaker_slug": "narrator",
      "display_name": "旁白",
      "role_type": "narrator",
      "role_level": "system",
      "voice_ref": "data/voice_bank/silent_bookstore/narrator/voice_clone_prompt.bin"
    },
    {
      "speaker_id": "char_lin_wan",
      "speaker_slug": "linwan",
      "display_name": "林晚",
      "aliases": ["晚晚", "阿晚", "林姑娘"],
      "role_type": "character",
      "role_level": "protagonist",
      "profile": {
        "gender": "female",
        "age_range": "young_adult",
        "age_estimate": "23",
        "occupation": "书店店员",
        "social_class": "middle",
        "personality_tags": ["温柔", "内敛", "坚韧"],
        "speech_style": {
          "tempo": "moderate",
          "vocabulary_level": "literary",
          "catchphrases": ["算了吧", "也好"]
        },
        "emotional_baseline": "calm"
      },
      "voice_ref": "data/voice_bank/silent_bookstore/linwan/voice_clone_prompt.bin",
      "voice_description": "23岁年轻女性，声音轻柔清澈，语速偏慢，带有文艺气质的书卷气"
    },
    {
      "speaker_id": "char_zhao_ming",
      "speaker_slug": "zhaoming",
      "display_name": "赵明",
      "aliases": ["赵队", "老赵"],
      "role_type": "character",
      "role_level": "protagonist",
      "profile": {
        "gender": "male",
        "age_range": "young_adult",
        "age_estimate": "28",
        "occupation": "刑警",
        "social_class": "middle",
        "personality_tags": ["正直", "刚毅", "偶尔温柔"],
        "speech_style": {
          "tempo": "fast",
          "vocabulary_level": "colloquial",
          "catchphrases": ["行", "没问题"]
        },
        "emotional_baseline": "confident"
      },
      "voice_ref": "data/voice_bank/silent_bookstore/zhaoming/voice_clone_prompt.bin",
      "voice_description": "28岁青年男性，嗓音低沉有力，语速中等偏快，说话干脆利落有威严感"
    }
  ],

  "chapter_emotion_arc": "紧张 → 惊喜 → 温暖 → 不安",

  "scenes": [
    {
      "scene_id": "ch05_sc01",
      "setting": "书店门口，黄昏",
      "mood": "nostalgic",
      "tension": 0.4,
      "utterances": [
        {
          "seq": 1,
          "speaker_id": "nar",
          "utterance_type": "narration",
          "text": "黄昏的光斜斜地照在书店的玻璃门上，林晚正准备翻转'营业中'的牌子。",
          "emotion": "calm",
          "emotion_detail": {
            "primary": "calm",
            "intensity": 0.4,
            "tts_instruct": "用平静舒缓的叙述语气"
          },
          "pause_after_ms": 500
        },
        {
          "seq": 2,
          "speaker_id": "char_lin_wan",
          "utterance_type": "dialogue",
          "text": "赵……赵明？",
          "emotion": "surprise",
          "emotion_detail": {
            "primary": "surprise",
            "secondary": "nervous",
            "intensity": 0.8,
            "valence": 0.3,
            "arousal": 0.7,
            "narration_cue": "她愣在原地，手中的牌子差点掉下来",
            "tts_instruct": "用惊讶且带点紧张的语气说，第一个字有轻微结巴"
          },
          "paraverbals": [
            {
              "type": "gasp",
              "position": "before",
              "source": "narration",
              "narration_cue": "她愣在原地",
              "implementation": "audio_splice",
              "audio_asset": "resources/sfx/gasp/female_surprise.wav"
            },
            {
              "type": "hesitation",
              "position": "inline",
              "source": "text_content",
              "implementation": "tts_native"
            }
          ],
          "pause_after_ms": 300
        },
        {
          "seq": 3,
          "speaker_id": "char_zhao_ming",
          "utterance_type": "dialogue",
          "text": "好久不见，林晚。",
          "emotion": "happy",
          "emotion_detail": {
            "primary": "happy",
            "secondary": "gentle",
            "intensity": 0.6,
            "valence": 0.7,
            "arousal": 0.4,
            "narration_cue": "他站在台阶下，微微笑着",
            "tts_instruct": "用温暖而克制的笑意说，语调轻柔"
          },
          "paraverbals": [
            {
              "type": "chuckle",
              "position": "before",
              "source": "narration",
              "narration_cue": "微微笑着",
              "implementation": "tts_instruct_merge"
            }
          ],
          "pause_after_ms": 400
        }
      ]
    }
  ]
}
```

---

## 11. 技术风险与缓解

| 风险 | 影响 | 缓解策略 |
|------|------|----------|
| LLM 角色识别错误（合并了不同角色 / 拆分了同一角色） | 后续所有环节出错 | 角色合并结果设为可编辑，支持人工校正后重跑 |
| 画像推断不准确（文本线索不足） | 音色不匹配 | 设 confidence 字段，低置信度标记 requires_review |
| 音色设计不理想 | 听感差 | 支持人工替换参考音频，VoiceClone 重新固化 |
| LLM 调用成本 | 长篇小说可能产生大量 token | 合并调用、利用缓存、龙套角色用规则而非 LLM |
| 情感推断与原文意图不符 | 配音情感失真 | 保留 source_excerpt + narration_cue 供人工审核 |
| 语气词过度注入 | 听感不自然 | 设置频率阈值（如每 10 句最多 2-3 个语气词） |
