# 模块：音频处理器（Audio Processor）

> 隶属系统：小说 TTS 配音系统
> 运行端：Mac 客户端
> 上游输入：TTS API 客户端生成的音频片段 + 编剧 Agent 输出的剧本（停顿、副语言标记）
> 下游输出：完整章节/全书音频文件
> 关联文档：[`novel-tts-design.md`](novel-tts-design.md)（总纲）、[`module-tts-api-client.md`](module-tts-api-client.md)（上游）

---

## 1. 模块职责

| 职责 | 说明 |
|------|------|
| 音频文件命名 | 按统一规范生成文件名，保证排序和唯一性 |
| 音频合并 | 按章节将多个 utterance 音频拼接为完整章节音频 |
| 副语言音效拼接 | 将 `[sigh]`、`[laughter]` 等音效插入对应位置 |
| 静音插入 | 根据 `pause_after_ms` 在句间插入静音 |
| 后处理 | 淡入淡出、音量标准化、降噪 |
| 全书合成 | 将所有章节合并为完整有声书（含元数据） |

---

## 2. 代码结构

> 项目路径：`src/xspy/audio/`（完整项目结构见 [`novel-tts-design.md`](novel-tts-design.md) §4）

```
src/xspy/audio/
├── __init__.py          # 公共导出：AudioMerger, BookAssembler, FilenameGenerator
├── naming.py            # FilenameGenerator（文件命名生成器）
├── merger.py            # AudioMerger（章节合并器）
├── splicer.py           # ParaverbalSplicer（副语言音效拼接器）
├── post_process.py      # PostProcessor（音量标准化、淡入淡出）
└── assembler.py         # BookAssembler（全书 M4B 组装器）
```

**关联的资源与产物目录：**

```
resources/sfx/              # 副语言音效库（静态资源，随代码提交）
data/output/{novel_slug}/   # 音频产物（运行时生成，.gitignore）
```

**导入方式：**

```python
from xspy.audio import AudioMerger, BookAssembler
from xspy.audio.naming import FilenameGenerator, AudioFileInfo
from xspy.audio.post_process import PostProcessor
```

---

## 3. 音频文件命名规范

### 3.1 命名格式

```
{novel_slug}-{chapter_num:04d}-{speaker_slug}-{emotion}-{seq_num:06d}.wav
```

| 字段 | 说明 | 示例 |
|------|------|------|
| `novel_slug` | 小说名（ASCII 简化） | `dragon_ball` |
| `chapter_num` | 章节号（4 位零填充） | `0001` |
| `speaker_slug` | 角色名（简化） | `goku` |
| `emotion` | 主要情绪标签 | `happy` |
| `seq_num` | 章节内全局序号（6 位） | `000001` |

### 3.2 设计原则

1. **排序友好** — 按文件名字母序排列即为播放顺序
2. **唯一性** — novel_slug + chapter + seq 保证全局唯一
3. **可读性** — 人眼可辨识角色和情绪
4. **兼容性** — 仅 ASCII 字符，兼容所有文件系统

### 3.3 特殊元素标记

| 类型 | `speaker_slug` | 说明 |
|------|----------------|------|
| 角色对话 | 角色名（如 `goku`） | 正常对话 |
| 旁白 | `narrator` | 叙述性文字 |
| 场景描述 | `desc` | 环境描述 |
| 内心独白 | `inner_{角色slug}` | 角色内心活动 |
| 音效 | `sfx` | 仅拼接用，不单独 TTS |

### 3.4 输出目录结构

```
data/output/                          # 运行时产物（.gitignore）
├── {novel_slug}/
│   ├── raw/                          # TTS 原始输出（逐句音频）
│   │   ├── ch0001/
│   │   │   ├── xxx-0001-goku-happy-000001.wav
│   │   │   ├── xxx-0001-narrator-calm-000002.wav
│   │   │   └── ...
│   │   └── ch0002/
│   ├── chapters/                     # 合并后的章节音频
│   │   ├── ch0001.mp3
│   │   ├── ch0002.mp3
│   │   └── ...
│   ├── audiobook/                    # 最终有声书
│   │   └── {novel_slug}.m4b
│   └── metadata.json                 # 全书元数据
```

### 3.5 文件名生成器

```python
from pathlib import Path
from typing import NamedTuple
from datetime import datetime
import re

class AudioFileInfo(NamedTuple):
    novel_slug: str
    chapter_num: int
    speaker_slug: str
    emotion: str
    seq_num: int

class FilenameGenerator:

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def generate(self, info: AudioFileInfo, ext: str = "wav") -> Path:
        chapter_dir = (
            self.output_dir / info.novel_slug / "raw"
            / f"ch{info.chapter_num:04d}"
        )  # output_dir 默认为 data/output/
        chapter_dir.mkdir(parents=True, exist_ok=True)

        filename = (
            f"{info.novel_slug}-{info.chapter_num:04d}-"
            f"{info.speaker_slug}-{info.emotion}-"
            f"{info.seq_num:06d}.{ext}"
        )
        return chapter_dir / filename

    @staticmethod
    def sanitize_slug(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r'[^a-z0-9_]', '_', text)
        text = re.sub(r'_+', '_', text)
        return text.strip('_')
```

---

## 4. 音频合并器

### 4.1 章节合并流程

```
章节 utterance 列表（按 seq 排序）
    ↓
遍历每个 utterance：
    ├── 有 paraverbal(position=before)？ → 拼接前置音效
    ├── 拼接 TTS 生成的语音文件
    ├── 有 paraverbal(position=after)？ → 拼接后置音效
    └── 拼接 pause_after_ms 静音
    ↓
后处理（音量标准化、淡入淡出）
    ↓
导出章节音频文件
```

### 4.2 实现

```python
from pydub import AudioSegment
from pathlib import Path
from typing import Optional

class AudioMerger:

    def __init__(self, sfx_library_path: Path):
        self.sfx_library = sfx_library_path

    def merge_chapter(
        self,
        utterances: list[dict],
        raw_audio_dir: Path,
        output_path: Path,
        output_format: str = "mp3"
    ) -> Path:
        combined = AudioSegment.empty()

        for utt in sorted(utterances, key=lambda u: u["seq"]):
            # 前置副语言
            for pv in utt.get("paraverbals", []):
                if pv["position"] == "before" and pv["implementation"] == "audio_splice":
                    sfx = self._load_sfx(pv["audio_asset"])
                    if sfx:
                        combined += sfx
                        combined += AudioSegment.silent(duration=100)

            # 主语音
            audio_file = self._find_audio_file(raw_audio_dir, utt["seq"])
            if audio_file:
                segment = AudioSegment.from_file(str(audio_file))
                combined += segment

            # 后置副语言
            for pv in utt.get("paraverbals", []):
                if pv["position"] == "after" and pv["implementation"] == "audio_splice":
                    sfx = self._load_sfx(pv["audio_asset"])
                    if sfx:
                        combined += AudioSegment.silent(duration=50)
                        combined += sfx

            # 句后停顿
            pause = utt.get("pause_after_ms", 300)
            combined += AudioSegment.silent(duration=pause)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        combined.export(str(output_path), format=output_format)
        return output_path

    def _load_sfx(self, asset_path: str) -> Optional[AudioSegment]:
        full_path = self.sfx_library / asset_path
        if full_path.exists():
            return AudioSegment.from_file(str(full_path))
        return None

    def _find_audio_file(self, directory: Path, seq: int) -> Optional[Path]:
        pattern = f"*-{seq:06d}.*"
        matches = list(directory.glob(pattern))
        return matches[0] if matches else None
```

---

## 5. 音频后处理

### 5.1 处理项

| 处理 | 说明 | 参数 |
|------|------|------|
| **音量标准化** | 统一所有片段的响度（LUFS） | 目标 -16 LUFS |
| **淡入** | 章节开头渐入 | 默认 500ms |
| **淡出** | 章节结尾渐出 | 默认 1000ms |
| **采样率统一** | 所有片段转为相同采样率 | 22050Hz / 44100Hz |
| **格式转换** | 输出为 MP3/FLAC/WAV | 可配置 |
| **片段间平滑** | 不同角色音频拼接处的过渡处理 | 交叉淡化 50ms |

### 5.2 实现

```python
from pydub import AudioSegment
from pydub.effects import normalize
from pathlib import Path

class PostProcessor:

    def __init__(
        self,
        target_sample_rate: int = 22050,
        fade_in_ms: int = 500,
        fade_out_ms: int = 1000,
        crossfade_ms: int = 50
    ):
        self.target_sample_rate = target_sample_rate
        self.fade_in_ms = fade_in_ms
        self.fade_out_ms = fade_out_ms
        self.crossfade_ms = crossfade_ms

    def process(self, audio: AudioSegment) -> AudioSegment:
        audio = audio.set_frame_rate(self.target_sample_rate)
        audio = normalize(audio)
        audio = audio.fade_in(self.fade_in_ms)
        audio = audio.fade_out(self.fade_out_ms)
        return audio

    def normalize_loudness(self, audio: AudioSegment, target_dbfs: float = -20.0) -> AudioSegment:
        change_in_dbfs = target_dbfs - audio.dBFS
        return audio.apply_gain(change_in_dbfs)
```

---

## 6. 全书组装器

### 6.1 M4B 有声书输出

```python
import subprocess
import json
from pathlib import Path

class BookAssembler:
    """将章节音频组装为 m4b 有声书"""

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg = ffmpeg_path

    def assemble(
        self,
        chapter_files: list[Path],
        chapter_titles: list[str],
        metadata: dict,
        output_path: Path,
        cover_image: Path = None
    ) -> Path:
        # Step 1: 创建章节列表文件
        concat_file = output_path.parent / "concat_list.txt"
        with open(concat_file, 'w') as f:
            for chapter_path in chapter_files:
                f.write(f"file '{chapter_path}'\n")

        # Step 2: 合并为单个音频
        merged = output_path.with_suffix('.m4a')
        cmd = [
            self.ffmpeg, '-y',
            '-f', 'concat', '-safe', '0', '-i', str(concat_file),
            '-c:a', 'aac', '-b:a', '128k',
            '-metadata', f'title={metadata.get("title", "")}',
            '-metadata', f'artist={metadata.get("author", "")}',
            '-metadata', f'album={metadata.get("title", "")}',
            str(merged)
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        # Step 3: 添加章节标记（生成 ffmetadata）
        ffmeta = self._generate_ffmetadata(chapter_files, chapter_titles, metadata)
        ffmeta_file = output_path.parent / "ffmetadata.txt"
        ffmeta_file.write_text(ffmeta)

        cmd_chapters = [
            self.ffmpeg, '-y',
            '-i', str(merged),
            '-i', str(ffmeta_file),
            '-map_metadata', '1',
            '-c', 'copy',
            str(output_path)
        ]
        subprocess.run(cmd_chapters, check=True, capture_output=True)

        # 清理临时文件
        concat_file.unlink(missing_ok=True)
        merged.unlink(missing_ok=True)
        ffmeta_file.unlink(missing_ok=True)

        return output_path

    def _generate_ffmetadata(
        self,
        chapter_files: list[Path],
        chapter_titles: list[str],
        metadata: dict
    ) -> str:
        lines = [";FFMETADATA1"]
        lines.append(f"title={metadata.get('title', '')}")
        lines.append(f"artist={metadata.get('author', '')}")
        lines.append("")

        offset_ms = 0
        for i, chapter_path in enumerate(chapter_files):
            audio = AudioSegment.from_file(str(chapter_path))
            duration_ms = len(audio)
            title = chapter_titles[i] if i < len(chapter_titles) else f"Chapter {i+1}"

            lines.append("[CHAPTER]")
            lines.append("TIMEBASE=1/1000")
            lines.append(f"START={offset_ms}")
            lines.append(f"END={offset_ms + duration_ms}")
            lines.append(f"title={title}")
            lines.append("")
            offset_ms += duration_ms

        return '\n'.join(lines)
```

---

## 7. 依赖清单

```
pydub>=0.25
ffmpeg  # 系统级依赖，需要单独安装
```

---

## 8. 关联文档

| 文档 | 关系 |
|------|------|
| [`novel-tts-design.md`](novel-tts-design.md) | 总纲 |
| [`module-tts-api-client.md`](module-tts-api-client.md) | 上游：提供原始音频片段 |
| [`auto-character-voice-engine.md`](auto-character-voice-engine.md) | 提供 paraverbals 定义 |
| [`novel-audio-screenwriter-agent.md`](novel-audio-screenwriter-agent.md) | 提供 utterance 列表和停顿标记 |
| [`module-task-manager.md`](module-task-manager.md) | 合并任务由任务管理器调度 |
