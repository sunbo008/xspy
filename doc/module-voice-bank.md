# 模块：角色音色库（Voice Bank）

> 隶属系统：小说 TTS 配音系统
> 运行端：Mac 客户端（管理） + Windows 服务端（生成）
> 上游输入：角色分析引擎输出的角色画像 + 音色描述
> 下游输出：`voice_clone_prompt` / `speaker_embedding` → TTS API 客户端
> 关联文档：[`novel-tts-design.md`](novel-tts-design.md)（总纲）、[`auto-character-voice-engine.md`](auto-character-voice-engine.md)（角色分析引擎）

---

## 1. 模块职责

| 职责 | 说明 |
|------|------|
| 音色注册 | 为每个角色注册唯一的音色配置 |
| 音色存储 | 管理参考音频、克隆特征、embedding 文件 |
| 音色检索 | 根据 speaker_slug 快速查找音色资源 |
| 自动生成 | 基于角色画像调用 TTS VoiceDesign 自动生成音色 |
| 固化复用 | 将 VoiceDesign 生成的参考音频通过 VoiceClone 固化为可复用特征 |
| 区分度校验 | 检测音色间的相似度，避免不同角色使用过于相似的声音 |
| 模板音色池 | 为龙套角色提供预置音色模板，按性别/年龄段分类 |

---

## 2. 代码结构

> 项目路径：`src/xspy/voice/`（完整项目结构见 [`novel-tts-design.md`](novel-tts-design.md) §4）

```
src/xspy/voice/
├── __init__.py          # 公共导出：VoiceBankManager, VoiceGenerator
├── bank.py              # VoiceBankManager（音色库管理器）
├── registry.py          # VoiceRegistry（注册表读写）
├── generator.py         # VoiceGenerator（自动音色生成，调用 TTS VoiceDesign）
├── similarity.py        # SimilarityChecker（音色相似度校验）
└── templates.py         # TemplatePool（龙套模板音色池）
```

**关联的资源与数据目录：**

```
resources/voice_templates/      # 模板音色（静态资源，随代码提交）
data/voice_bank/{novel_slug}/   # 角色音色库存储（运行时生成，.gitignore）
```

**导入方式：**

```python
from xspy.voice import VoiceBankManager, VoiceGenerator
from xspy.voice.similarity import SimilarityChecker
from xspy.voice.templates import TemplatePool
```

---

## 3. 数据模型

### 3.1 音色条目

```python
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

@dataclass
class VoiceEntry:
    """单个角色的音色条目"""
    speaker_slug: str
    display_name: str

    # 音色资源路径
    reference_audio: Optional[Path] = None      # 参考音频（3-10 秒 WAV）
    voice_clone_prompt: Optional[Path] = None   # 克隆特征文件
    speaker_embedding: Optional[Path] = None    # speaker embedding

    # 音色描述
    voice_description: str = ""                  # 自然语言描述
    gender: str = "unknown"                      # male / female / unknown
    age_range: str = "unknown"                   # child / teenager / young_adult / middle_aged / elderly

    # 生成信息
    source: str = "manual"                       # manual / auto_design / auto_clone / template
    profile_based: bool = False                  # 是否基于角色画像自动生成

    # 质量信息
    quality_score: Optional[float] = None        # 人工打分 0-1
    requires_review: bool = False
    similarity_warnings: list[str] = field(default_factory=list)
```

### 3.2 音色注册表

```json
{
  "novel_slug": "silent_bookstore",
  "schema_version": "1.0",
  "created_at": "2026-03-30T10:00:00",
  "updated_at": "2026-03-30T12:30:00",
  "voices": [
    {
      "speaker_slug": "narrator",
      "display_name": "旁白",
      "reference_audio": "narrator/reference.wav",
      "voice_clone_prompt": "narrator/voice_clone_prompt.bin",
      "voice_description": "成熟男性，声音沉稳温厚，适合叙事",
      "gender": "male",
      "age_range": "middle_aged",
      "source": "manual"
    },
    {
      "speaker_slug": "linwan",
      "display_name": "林晚",
      "reference_audio": "linwan/reference.wav",
      "voice_clone_prompt": "linwan/voice_clone_prompt.bin",
      "voice_description": "23岁年轻女性，声音轻柔清澈，语速偏慢，带有文艺气质的书卷气",
      "gender": "female",
      "age_range": "young_adult",
      "source": "auto_design",
      "profile_based": true
    }
  ]
}
```

---

## 4. 存储目录结构

```
data/voice_bank/                       # 运行时数据（.gitignore）
├── {novel_slug}/
│   ├── voice_registry.json            # 注册表
│   ├── narrator/
│   │   ├── reference.wav              # 参考音频
│   │   ├── voice_clone_prompt.bin     # 克隆特征
│   │   └── metadata.json             # 详细元信息
│   ├── linwan/
│   │   ├── reference.wav
│   │   ├── voice_clone_prompt.bin
│   │   └── metadata.json
│   └── zhaoming/
│       └── ...

resources/voice_templates/             # 模板音色（静态资源，随代码提交）
├── male_child.wav
├── male_young.wav
├── male_middle.wav
├── male_elderly.wav
├── female_child.wav
├── female_young.wav
├── female_middle.wav
└── female_elderly.wav
```

---

## 5. 音色库管理器

```python
import json
from pathlib import Path
from typing import Optional

class VoiceBankManager:

    def __init__(self, bank_root: Path):
        self.bank_root = bank_root

    def get_bank_path(self, novel_slug: str) -> Path:
        return self.bank_root / novel_slug

    def get_registry(self, novel_slug: str) -> dict:
        registry_path = self.get_bank_path(novel_slug) / "voice_registry.json"
        if registry_path.exists():
            return json.loads(registry_path.read_text(encoding='utf-8'))
        return {"novel_slug": novel_slug, "voices": []}

    def register_voice(self, novel_slug: str, entry: VoiceEntry):
        bank_path = self.get_bank_path(novel_slug)
        voice_dir = bank_path / entry.speaker_slug
        voice_dir.mkdir(parents=True, exist_ok=True)

        # 保存元信息
        metadata = {
            "speaker_slug": entry.speaker_slug,
            "display_name": entry.display_name,
            "voice_description": entry.voice_description,
            "gender": entry.gender,
            "age_range": entry.age_range,
            "source": entry.source,
            "profile_based": entry.profile_based,
        }
        (voice_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2)
        )

        # 更新注册表
        registry = self.get_registry(novel_slug)
        voices = registry.get("voices", [])
        voices = [v for v in voices if v["speaker_slug"] != entry.speaker_slug]
        voices.append({
            "speaker_slug": entry.speaker_slug,
            "display_name": entry.display_name,
            "reference_audio": f"{entry.speaker_slug}/reference.wav",
            "voice_clone_prompt": f"{entry.speaker_slug}/voice_clone_prompt.bin",
            "voice_description": entry.voice_description,
            "gender": entry.gender,
            "age_range": entry.age_range,
            "source": entry.source,
        })
        registry["voices"] = voices
        registry["updated_at"] = datetime.now().isoformat()

        registry_path = bank_path / "voice_registry.json"
        registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2))

    def get_voice(self, novel_slug: str, speaker_slug: str) -> Optional[VoiceEntry]:
        registry = self.get_registry(novel_slug)
        for v in registry.get("voices", []):
            if v["speaker_slug"] == speaker_slug:
                bank_path = self.get_bank_path(novel_slug)
                return VoiceEntry(
                    speaker_slug=v["speaker_slug"],
                    display_name=v["display_name"],
                    reference_audio=bank_path / v.get("reference_audio", ""),
                    voice_clone_prompt=bank_path / v.get("voice_clone_prompt", ""),
                    voice_description=v.get("voice_description", ""),
                    gender=v.get("gender", "unknown"),
                    age_range=v.get("age_range", "unknown"),
                    source=v.get("source", "manual"),
                )
        return None

    def list_voices(self, novel_slug: str) -> list[str]:
        registry = self.get_registry(novel_slug)
        return [v["speaker_slug"] for v in registry.get("voices", [])]
```

---

## 6. 自动音色生成器

```python
class VoiceGenerator:
    """基于角色画像自动生成音色"""

    def __init__(self, tts_client, bank_manager: VoiceBankManager):
        self.tts_client = tts_client
        self.bank = bank_manager

    def generate_from_profile(
        self,
        novel_slug: str,
        speaker_slug: str,
        display_name: str,
        profile: dict,
        existing_descriptions: list[str] = None
    ) -> VoiceEntry:
        # Step 1: 画像 → 音色描述
        voice_desc = self._profile_to_description(profile, existing_descriptions)

        # Step 2: VoiceDesign 生成参考音频
        bank_path = self.bank.get_bank_path(novel_slug)
        voice_dir = bank_path / speaker_slug
        voice_dir.mkdir(parents=True, exist_ok=True)
        ref_path = voice_dir / "reference.wav"

        result = self.tts_client.voice_design(voice_desc, ref_path)
        if not result.success:
            raise RuntimeError(f"VoiceDesign 失败: {result.error_message}")

        # Step 3: VoiceClone 固化
        clone_prompt = self.tts_client.create_clone_prompt(ref_path)
        clone_path = voice_dir / "voice_clone_prompt.bin"
        if clone_prompt:
            clone_path.write_bytes(clone_prompt)

        # Step 4: 注册
        entry = VoiceEntry(
            speaker_slug=speaker_slug,
            display_name=display_name,
            reference_audio=ref_path,
            voice_clone_prompt=clone_path if clone_prompt else None,
            voice_description=voice_desc,
            gender=profile.get("gender", "unknown"),
            age_range=profile.get("age_range", "unknown"),
            source="auto_design",
            profile_based=True,
        )
        self.bank.register_voice(novel_slug, entry)
        return entry

    def _profile_to_description(
        self,
        profile: dict,
        existing_descriptions: list[str] = None
    ) -> str:
        gender_map = {"male": "男性", "female": "女性"}
        age_map = {
            "child": "儿童",
            "teenager": "青少年",
            "young_adult": "青年",
            "middle_aged": "中年",
            "elderly": "老年"
        }

        gender = gender_map.get(profile.get("gender"), "")
        age = profile.get("age_estimate", age_map.get(profile.get("age_range"), ""))
        occupation = profile.get("occupation", "")
        personality = "、".join(profile.get("personality_tags", []))
        baseline = profile.get("emotional_baseline", "")

        desc = f"{age}岁{gender}"
        if occupation:
            desc += f"，职业是{occupation}"
        if personality:
            desc += f"，性格{personality}"
        if baseline:
            desc += f"，说话整体感觉{baseline}"

        return desc
```

---

## 7. 音色模板池

为龙套/次要角色提供预设音色，避免每个角色都走 VoiceDesign 流程。

### 7.1 模板分类

| 模板 ID | 性别 | 年龄段 | 特征 |
|---------|------|--------|------|
| `male_child` | 男 | 儿童 | 清脆、天真 |
| `male_teenager` | 男 | 青少年 | 清亮、有朝气 |
| `male_young` | 男 | 青年 | 中等音高、稳重 |
| `male_middle` | 男 | 中年 | 低沉、沉稳 |
| `male_elderly` | 男 | 老年 | 沙哑、缓慢 |
| `female_child` | 女 | 儿童 | 高音、奶声 |
| `female_teenager` | 女 | 青少年 | 清亮、活泼 |
| `female_young` | 女 | 青年 | 柔和、清澈 |
| `female_middle` | 女 | 中年 | 稳重、温和 |
| `female_elderly` | 女 | 老年 | 低哑、慈祥 |

### 7.2 模板匹配

```python
class TemplatePool:

    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir

    def match(self, gender: str, age_range: str) -> Optional[Path]:
        template_id = f"{gender}_{age_range}"
        candidates = [
            self.templates_dir / f"{template_id}.wav",
            self.templates_dir / f"{template_id}.mp3",
        ]
        for path in candidates:
            if path.exists():
                return path

        # 回退到最近的年龄段
        fallback_order = {
            "child": ["teenager", "young_adult"],
            "teenager": ["young_adult", "child"],
            "young_adult": ["middle_aged", "teenager"],
            "middle_aged": ["young_adult", "elderly"],
            "elderly": ["middle_aged", "young_adult"],
        }
        for fallback_age in fallback_order.get(age_range, []):
            fallback_id = f"{gender}_{fallback_age}"
            for ext in ["wav", "mp3"]:
                path = self.templates_dir / f"{fallback_id}.{ext}"
                if path.exists():
                    return path
        return None
```

---

## 8. 音色相似度校验

```python
import numpy as np
from typing import Optional

class SimilarityChecker:
    """音色区分度校验"""

    SIMILARITY_THRESHOLD = 0.85  # 相似度超过此值触发警告

    def check_all(self, novel_slug: str, bank_manager: VoiceBankManager) -> list[dict]:
        """检查音色库中所有音色对的相似度"""
        voices = bank_manager.list_voices(novel_slug)
        warnings = []

        for i in range(len(voices)):
            for j in range(i + 1, len(voices)):
                v1 = bank_manager.get_voice(novel_slug, voices[i])
                v2 = bank_manager.get_voice(novel_slug, voices[j])

                if v1.speaker_embedding and v2.speaker_embedding:
                    sim = self._cosine_similarity(
                        self._load_embedding(v1.speaker_embedding),
                        self._load_embedding(v2.speaker_embedding)
                    )
                    if sim > self.SIMILARITY_THRESHOLD:
                        warnings.append({
                            "voice_a": voices[i],
                            "voice_b": voices[j],
                            "similarity": round(sim, 3),
                            "suggestion": f"{voices[i]} 和 {voices[j]} 的音色过于相似 "
                                         f"(相似度 {sim:.1%})，建议重新生成其中一个"
                        })
        return warnings

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    @staticmethod
    def _load_embedding(path: Path) -> np.ndarray:
        return np.load(str(path))
```

---

## 9. 音色选择策略

根据角色重要性使用不同的音色策略：

| 角色等级 | 音色来源 | 质量 | 成本 |
|----------|----------|------|------|
| **主角** | VoiceDesign 自动生成 → VoiceClone 固化 | 最高 | 高 |
| **重要配角** | VoiceDesign 自动生成 → VoiceClone 固化 | 高 | 高 |
| **次要角色** | 从模板池匹配 | 中等 | 低 |
| **龙套** | 共享通用模板 | 基本 | 无 |
| **旁白** | 手工选定或预设 | 最高 | 一次性 |

---

## 10. 关联文档

| 文档 | 关系 |
|------|------|
| [`novel-tts-design.md`](novel-tts-design.md) | 总纲 |
| [`auto-character-voice-engine.md`](auto-character-voice-engine.md) | 上游：提供角色画像和音色描述 |
| [`module-tts-api-client.md`](module-tts-api-client.md) | 下游：消费 voice_clone_prompt |
| [`module-emotion-system.md`](module-emotion-system.md) | 协作：音色 + 情绪共同控制 TTS 输出 |
