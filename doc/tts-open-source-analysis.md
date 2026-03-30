# 开源有声书 / TTS 项目分析

> 对标项目：本仓库的 `novel-tts-design.md`（Mac ↔ Windows 局域网 Index-TTS 架构）与 `novel-audio-screenwriter-agent.md`（编剧 Agent 剧本结构化）。

---

## 一、项目速览

| 项目 | Stars | 核心定位 | TTS 引擎 | 语言支持 | 许可证 |
|------|------:|---------|----------|---------|--------|
| [ebook2audiobookSTYLETTS2](https://github.com/DrewThomasson/ebook2audiobookSTYLETTS2) | 35 | 电子书→有声书端到端转换 | StyleTTS2 | 英文为主 | — |
| [easyVoice](https://github.com/cosin2077/easyVoice) | 2k+ | 文本/小说智能转语音 Web 平台 | Edge-TTS (免费) + OpenAI 兼容 API | 中英等多语 | 开源 |
| [Bark](https://github.com/suno-ai/bark) | 39k | 文本→音频生成模型（语音+音乐+音效） | Bark 自研（GPT 风格） | 13 种语言含中文 | MIT |
| [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) | 10k+ | 阿里通义最新 TTS 系列 | Qwen3-TTS（离散多码本 LM） | 10 种语言含中文 | 开源 |

---

## 二、逐项目深度分析

### 2.1 ebook2audiobookSTYLETTS2

**做了什么：**
- 用 Calibre `ebook-convert` 将 EPUB/PDF/MOBI 等格式转为文本并按章分割
- 用 StyleTTS2 逐章合成语音，支持可选的声线克隆
- 输出 m4b 格式（含章节元数据），可直接在有声书播放器中使用
- 提供 Gradio Web UI + Docker 一键部署

**架构流程：**
```
ebook → Calibre(格式转换+章节分割) → StyleTTS2(TTS合成+可选声线克隆) → FFmpeg(合并为m4b)
```

**亮点：**
- 端到端一键流程，从电子书到成品有声书
- m4b 输出带完整章节标记，有声书播放器可直接导航
- Docker 部署简洁（GPU/CPU 均支持）
- 支持 20+ 种电子书格式输入

**局限：**
- **无角色识别**——全书单一音色，不区分角色对话与旁白
- **无情绪控制**——所有文本用相同语气朗读
- StyleTTS2 英文效果好，中文支持弱
- 项目较小（35 stars），维护活跃度低

---

### 2.2 easyVoice

**做了什么：**
- Web 应用（Vue3 + Node.js），一键将长文本/小说转为语音
- **AI 智能推荐配音**：用 LLM 分析文本段落，自动推荐合适的声音、语速、音调
- **多角色配音**：支持 JSON 格式指定角色→声音映射（含旁白）
- 流式传输：超长文本立即开始播放
- 自动生成字幕文件
- 基于 Edge-TTS（免费无限制）+ OpenAI 兼容 API

**核心 API 示例（多角色）：**
```json
{
  "data": [
    { "desc": "徐凤年", "text": "你敢动他，我会穷尽一生毁掉卢家", "voice": "zh-CN-YunjianNeural", "volume": "40%" },
    { "desc": "旁白", "text": "面对棠溪剑仙的杀意，徐凤年按住剑柄...", "voice": "zh-CN-YunxiNeural", "rate": "0%", "pitch": "0Hz" }
  ]
}
```

**亮点：**
- **多角色配音 JSON Schema** 与我们的编剧 Agent 输出 `utterances[]` 设计理念一致
- AI 推荐配音思路可借鉴：用 LLM 分析段落→自动选声音参数
- 流式传输架构对超长小说友好
- 完全免费（Edge-TTS）

**局限：**
- Edge-TTS 是微软云端服务，音色固定，不支持真正的声线克隆
- AI 推荐质量依赖所用 LLM 模型能力
- 无自动角色识别——需要人工或外部工具预处理角色归属
- 并发受 Edge-TTS API 限制

---

### 2.3 Bark (Suno)

**做了什么：**
- **全生成式**文本→音频模型（不只是 TTS，还能生成音乐、音效）
- GPT 风格架构（类 AudioLM + Vall-E），用 EnCodec 量化音频表示
- 支持 100+ 预设音色，13 种语言（含中文）
- 支持非语言声音：`[laughs]`、`[sighs]`、`[music]`、`♪` 等标记
- MIT 许可，可商用

**独特的声音控制标记：**
```
[laughter]  → 笑声
[sighs]     → 叹息
[gasps]     → 喘气
— 或 ...    → 犹豫停顿
♪           → 歌曲模式
CAPITALIZATION → 强调
[MAN]/[WOMAN]  → 性别偏向
```

**亮点：**
- **非语言声音生成**是独特卖点——笑声、叹息、犹豫等让有声书更生动
- 文本内联标记控制（`[laughs]`）简单直观
- 社区庞大（39k stars），生态丰富
- 支持低显存 GPU（<4GB）

**局限：**
- 单次生成只有约 **13 秒**，长文本需分段拼接
- **不支持自定义声线克隆**——只能用预设音色
- 质量不稳定（全生成式模型可能"跑偏"）
- 中文质量不如英文
- 推理速度较慢（非实时）
- 12GB VRAM（完整版），小模型需 8GB

---

### 2.4 Qwen3-TTS (通义千问)

**做了什么：**
- 阿里通义最新开源 TTS 系列，2026 年 1 月发布
- **三大核心能力**：
  - `CustomVoice`：9 种预设音色 + 自然语言指令控制情绪/语气
  - `VoiceDesign`：用自然语言描述创造全新音色（"撒娇萝莉女声"等）
  - `Base (Voice Clone)`：3 秒音频即可克隆音色
- 自研 12Hz Tokenizer，高效音频压缩 + 高保真重建
- 离散多码本 LM 架构，绕过传统 LM+DiT 级联误差
- **流式生成**：端到端延迟低至 97ms
- 10 种语言（中英日韩德法俄葡西意）
- 支持 vLLM 部署 + 微调

**关键 API 模式：**

```python
# 自然语言指令控制情绪
model.generate_custom_voice(
    text="其实我真的有发现...",
    speaker="Vivian",
    instruct="用特别愤怒的语气说"
)

# 声音设计（用描述创建新音色）
model.generate_voice_design(
    text="哥哥，你回来啦...",
    instruct="撒娇稚嫩的萝莉女声，音调偏高..."
)

# 3秒声线克隆 + 可复用 prompt
prompt = model.create_voice_clone_prompt(ref_audio="ref.wav", ref_text="...")
model.generate_voice_clone(text="新文本", voice_clone_prompt=prompt)
```

**亮点：**
- **自然语言情绪控制**（`instruct` 参数）与编剧 Agent 的 `emotion` 标注天然互补
- **Voice Design → Clone 工作流**可为小说角色快速创建一致音色
- 中文效果 SOTA 级（WER 0.77 / Seed-TTS 评测）
- 0.6B 小模型可在消费级显卡运行
- 支持 vLLM 部署（与我们现有 Index-TTS + vLLM 架构一致）
- `create_voice_clone_prompt` 可复用，避免重复计算——适合批量合成
- 支持微调，可针对特定小说风格优化

**局限：**
- 较新（2026.01），社区生态仍在成长
- 完整功能需 1.7B 模型 + FlashAttention2
- vLLM 集成目前仅支持离线推理，在线 serving 尚在开发

---

## 三、对标分析：可借鉴到我们项目的要素

### 3.1 架构与流程层

| 借鉴来源 | 要素 | 对我们的价值 | 落地建议 |
|----------|------|-------------|---------|
| ebook2audiobook | **Calibre 格式转换** | 扩展输入格式支持（当前 TXT/EPUB/PDF） | 集成 `ebook-convert` 支持 MOBI/CHM/FB2 等 20+ 格式 |
| ebook2audiobook | **m4b 输出 + 章节元数据** | 最终交付物从散碎 MP3 升级为单文件有声书 | `audio_merger` 增加 m4b 封装，写入章节标记 |
| easyVoice | **流式传输架构** | 长章节不必等全部合成完才能试听 | 服务端增加 SSE/WebSocket 流式响应 |
| easyVoice | **JSON 多角色配音 Schema** | 验证了我们编剧 Agent `utterances[]` 设计方向正确 | — |

### 3.2 TTS 引擎层

| 借鉴来源 | 要素 | 对我们的价值 | 落地建议 |
|----------|------|-------------|---------|
| **Qwen3-TTS** | **自然语言情绪指令** | 编剧 Agent 的 `emotion` 标签可直接映射为 `instruct` 文本 | `emotion: "angry"` → `instruct: "用愤怒的语气说"` 的映射表 |
| **Qwen3-TTS** | **Voice Design → Clone 流程** | 为新角色快速创建音色：编剧 Agent 输出角色描述 → VoiceDesign 生成参考音频 → Clone 复用 | 在角色音色库系统增加 VoiceDesign 自动创建通道 |
| **Qwen3-TTS** | **`create_voice_clone_prompt` 复用** | 同一角色多句对话只需提取一次 speaker embedding | 替代 Index-TTS 每句重新提取的方式，大幅提速 |
| **Qwen3-TTS** | **vLLM 部署** | 与现有 Index-TTS + vLLM 架构一致，切换成本低 | 作为 Index-TTS 的**备选/升级引擎**纳入 `api_server_v2.py` |
| **Qwen3-TTS** | **0.6B 小模型** | 在 RTX 3070 Ti (8GB) 上可运行 | 测试 0.6B-Base 在 8GB 显存下的表现 |
| Bark | **非语言声音标记** | `[laughs]`、`[sighs]` 等让有声书更有沉浸感 | 编剧 Agent 的 `ssml_hints` / `sfx_placeholder` 可输出 Bark 风格标记 |

### 3.3 编剧 Agent 层

| 借鉴来源 | 要素 | 对我们的价值 | 落地建议 |
|----------|------|-------------|---------|
| easyVoice | **AI 智能推荐配音** | LLM 根据文本内容自动推荐声音参数（语速/音调/音量） | 编剧 Agent 阶段 D 增加 `rate`/`pitch`/`volume` 建议字段 |
| easyVoice | **角色→声音映射 JSON** | 验证了 `cast_registry` + `voice_ref` 设计 | — |
| Bark | **文本内联标记** | `[laughs]` 等标记比独立 `sfx_placeholder` 更紧凑 | 支持两种模式：内联标记（Bark 引擎）和独立字段（通用引擎） |
| Qwen3-TTS | **角色声线描述 → 自动生成** | 编剧 Agent 的 `cast_registry.notes` 字段可驱动 VoiceDesign | 新增工作流：`notes` → `generate_voice_design` → `voice_ref` 自动填充 |

---

## 四、推荐行动优先级

### P0（短期，高价值）

1. **评估 Qwen3-TTS 作为 Index-TTS 替代/补充引擎**
   - 测试 `0.6B-Base` 在 RTX 3070 Ti 上的速度和质量
   - 对比 Index-TTS 1.5 的中文有声书效果
   - 若效果好，在 `api_server_v2.py` 中增加 Qwen3-TTS 后端

2. **编剧 Agent 输出增加语音参数建议**
   - 参考 easyVoice 的 `rate`/`pitch`/`volume` 字段
   - `utterance` 增加 `voice_params: { rate, pitch, volume }` 可选字段

### P1（中期，架构增强）

3. **角色音色自动创建管道**
   - 编剧 Agent 输出角色描述 → Qwen3-TTS VoiceDesign 生成参考音频 → 存入角色音色库
   - 替代当前"人工为每个角色录制参考音频"的方式

4. **m4b 有声书封装**
   - 参考 ebook2audiobook 的 FFmpeg 封装流程
   - 将散碎章节 MP3 合并为带章节标记的 m4b

### P2（长期，体验优化）

5. **流式试听**
   - 参考 easyVoice 的流式传输架构
   - 章节合成过程中即可开始播放

6. **非语言声音增强**
   - 参考 Bark 的 `[laughs]`/`[sighs]` 标记体系
   - 编剧 Agent 识别叹息、笑声等场景，插入对应标记

---

## 五、引擎能力对比矩阵

| 能力 | Index-TTS 1.5 (当前) | Qwen3-TTS 1.7B | Bark | Edge-TTS (easyVoice) |
|------|:---:|:---:|:---:|:---:|
| 中文质量 | ★★★★ | ★★★★★ | ★★★ | ★★★★ |
| 声线克隆 | ✅ | ✅ (3秒克隆) | ❌ | ❌ |
| 情绪控制 | ✅ (embedding) | ✅ (自然语言指令) | ❌ | ❌ |
| 音色设计 | ❌ | ✅ (VoiceDesign) | ❌ | ❌ |
| 非语言声音 | ❌ | ❌ | ✅ | ❌ |
| 流式生成 | ❌ | ✅ (97ms 首包) | ❌ | ✅ |
| vLLM 部署 | ✅ | ✅ | ❌ | N/A (云端) |
| 最低显存 | 8GB | ~4GB (0.6B) | 2-12GB | 0 (云端) |
| 推理速度 | 中 | 快 | 慢 | 快（云端） |
| 商用许可 | 需确认 | ✅ | ✅ MIT | 受限（微软条款） |

---

## 六、参考链接

| 项目 | 仓库 | 关键文档 |
|------|------|---------|
| ebook2audiobookSTYLETTS2 | https://github.com/DrewThomasson/ebook2audiobookSTYLETTS2 | README |
| easyVoice | https://github.com/cosin2077/easyVoice | README + `/api/v1/tts/generateJson` API |
| Bark | https://github.com/suno-ai/bark | README + `notebooks/long_form_generation.ipynb` |
| Qwen3-TTS | https://github.com/QwenLM/Qwen3-TTS | README + `finetuning/` + vLLM examples |
| 本项目 TTS 设计 | `doc/novel-tts-design.md` | 11.1-11.4 角色音色与命名 |
| 本项目编剧 Agent | `doc/novel-audio-screenwriter-agent.md` | 4.4 utterance Schema |
