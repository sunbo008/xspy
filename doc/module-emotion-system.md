# 模块：情绪控制系统（Emotion System）

> 隶属系统：小说 TTS 配音系统
> 运行端：Mac 客户端（推断） + Windows 服务端（TTS 情绪参数执行）
> 上游输入：编剧 Agent / 角色分析引擎输出的 `emotion` / `emotion_detail`
> 下游输出：TTS 引擎可执行的情绪控制参数
> 关联文档：[`novel-tts-design.md`](novel-tts-design.md)（总纲）、[`auto-character-voice-engine.md`](auto-character-voice-engine.md)（上下文情感推断引擎）

---

## 1. 模块职责

| 职责 | 说明 |
|------|------|
| 情绪类型定义 | 统一的情绪枚举，全系统共用 |
| 情绪标签校验 | 确保所有 utterance 的 emotion 都在合法枚举内 |
| 情绪→TTS 参数转换 | 将 emotion_detail 映射为不同 TTS 引擎的具体参数 |
| 情绪参考音频管理 | 管理预录制的情绪参考音频（用于引擎方法 2） |
| 叙述线索→情绪推断 | 基于规则引擎的快速情绪推断（LLM 推断的补充） |
| 情绪平滑 | 检测并平滑相邻句子间不自然的情绪跳跃 |

---

## 2. 代码结构

> 项目路径：`src/xspy/emotion/`（完整项目结构见 [`novel-tts-design.md`](novel-tts-design.md) §4）

```
src/xspy/emotion/
├── __init__.py              # 公共导出：EmotionType, EmotionDetail
├── types.py                 # EmotionType 枚举定义（从 core/types.py re-export）
├── detail.py                # EmotionDetail 数据模型（含 VAD 维度）
├── rules.py                 # NarrationRuleEngine（叙述线索→情绪映射规则）
├── smoother.py              # EmotionSmoother（情绪平滑器）
├── audio_library.py         # EmotionAudioLibrary（情绪参考音频库）
└── adapter/                 # TTS 引擎情绪适配器
    ├── __init__.py
    ├── base.py              #   EmotionAdapter 抽象基类
    ├── qwen.py              #   QwenTTSEmotionAdapter（instruct 自然语言）
    └── index_tts.py         #   IndexTTSEmotionAdapter（情绪参考音频）
```

**关联的资源目录：**

```
resources/emotion_audio/        # 情绪参考音频（用于 Index-TTS，静态资源）
    ├── happy/
    │   ├── low.wav
    │   ├── medium.wav
    │   └── high.wav
    ├── sad/
    └── ...
```

**导入方式：**

```python
from xspy.emotion import EmotionType, EmotionDetail
from xspy.emotion.rules import NarrationRuleEngine
from xspy.emotion.adapter.qwen import QwenTTSEmotionAdapter
```

---

## 3. 情绪类型定义

### 3.1 主情绪枚举

```python
from enum import Enum

class EmotionType(Enum):
    """主情绪类型 — 全系统统一使用"""

    # 基础情绪
    HAPPY = "happy"           # 快乐
    SAD = "sad"               # 悲伤
    ANGRY = "angry"           # 愤怒
    FEAR = "fear"             # 恐惧
    SURPRISE = "surprise"     # 惊讶
    DISGUST = "disgust"       # 厌恶
    NEUTRAL = "neutral"       # 中性

    # 扩展情绪
    EXCITED = "excited"       # 兴奋
    CALM = "calm"             # 平静
    CONFIDENT = "confident"   # 自信
    SARCASTIC = "sarcastic"   # 讽刺
    ROMANTIC = "romantic"     # 浪漫
    ANXIOUS = "anxious"       # 焦虑
    NOSTALGIC = "nostalgic"   # 怀旧
    GRIEF = "grief"           # 悲痛
    CONTEMPT = "contempt"     # 蔑视
    GENTLE = "gentle"         # 温柔
    COLD = "cold"             # 冷漠
    RESIGNED = "resigned"     # 无奈/认命
    PROUD = "proud"           # 骄傲

    @classmethod
    def values(cls) -> list[str]:
        return [e.value for e in cls]

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls.values()
```

### 3.2 情绪维度模型

除了离散情绪标签，还支持连续维度模型（VAD 模型）：

| 维度 | 范围 | 说明 |
|------|------|------|
| **Valence**（效价） | -1.0 ~ +1.0 | 负面 ↔ 正面 |
| **Arousal**（激活度） | 0.0 ~ 1.0 | 平静 ↔ 激动 |
| **Dominance**（支配度） | 0.0 ~ 1.0 | 顺从 ↔ 支配 |

**情绪标签到 VAD 默认映射：**

| 情绪 | Valence | Arousal | Dominance |
|------|---------|---------|-----------|
| happy | +0.7 | 0.6 | 0.6 |
| sad | -0.7 | 0.3 | 0.2 |
| angry | -0.5 | 0.9 | 0.8 |
| fear | -0.6 | 0.8 | 0.1 |
| surprise | +0.2 | 0.8 | 0.4 |
| neutral | 0.0 | 0.3 | 0.5 |
| excited | +0.8 | 0.9 | 0.7 |
| calm | +0.3 | 0.1 | 0.5 |
| confident | +0.5 | 0.5 | 0.9 |
| sarcastic | -0.3 | 0.5 | 0.7 |
| romantic | +0.8 | 0.4 | 0.4 |
| anxious | -0.5 | 0.7 | 0.2 |
| grief | -0.9 | 0.4 | 0.1 |
| cold | -0.2 | 0.2 | 0.8 |
| resigned | -0.4 | 0.1 | 0.1 |

---

## 4. emotion_detail 数据模型

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class EmotionDetail:
    """精细情绪控制"""
    primary: str                          # 主情绪（EmotionType）
    secondary: Optional[str] = None       # 次要情绪
    intensity: float = 0.5                # 情绪强度 0.0-1.0
    valence: float = 0.0                  # 效价 -1.0 ~ +1.0
    arousal: float = 0.3                  # 激活度 0.0-1.0
    dominance: float = 0.5               # 支配度 0.0-1.0
    narration_cue: Optional[str] = None  # 触发该情绪的叙述线索
    tts_instruct: Optional[str] = None   # TTS 自然语言指令

    def validate(self) -> list[str]:
        errors = []
        if not EmotionType.is_valid(self.primary):
            errors.append(f"无效的主情绪: {self.primary}")
        if self.secondary and not EmotionType.is_valid(self.secondary):
            errors.append(f"无效的次要情绪: {self.secondary}")
        if not 0.0 <= self.intensity <= 1.0:
            errors.append(f"intensity 超出范围: {self.intensity}")
        if not -1.0 <= self.valence <= 1.0:
            errors.append(f"valence 超出范围: {self.valence}")
        if not 0.0 <= self.arousal <= 1.0:
            errors.append(f"arousal 超出范围: {self.arousal}")
        return errors
```

---

## 5. TTS 引擎情绪适配器

不同 TTS 引擎接受不同格式的情绪参数，本模块负责统一转换。

### 5.1 适配器接口

```python
from abc import ABC, abstractmethod

class EmotionAdapter(ABC):

    @abstractmethod
    def adapt(self, detail: EmotionDetail) -> dict:
        """将 EmotionDetail 转换为引擎特定参数"""
        ...
```

### 5.2 Qwen3-TTS 适配器

```python
class QwenTTSEmotionAdapter(EmotionAdapter):
    """Qwen3-TTS 使用 instruct 自然语言参数"""

    def adapt(self, detail: EmotionDetail) -> dict:
        params = {}

        if detail.tts_instruct:
            params["instruct"] = detail.tts_instruct
        else:
            params["instruct"] = self._generate_instruct(detail)

        return params

    def _generate_instruct(self, detail: EmotionDetail) -> str:
        intensity_word = self._intensity_to_word(detail.intensity)

        emotion_phrases = {
            "happy": f"{intensity_word}开心愉快",
            "sad": f"{intensity_word}悲伤低沉",
            "angry": f"{intensity_word}愤怒激动",
            "fear": f"{intensity_word}恐惧紧张",
            "surprise": f"{intensity_word}惊讶",
            "excited": f"{intensity_word}兴奋高昂",
            "calm": "平静舒缓",
            "confident": "自信有力",
            "sarcastic": f"{intensity_word}讽刺嘲弄",
            "romantic": f"{intensity_word}温柔浪漫",
            "anxious": f"{intensity_word}焦虑不安",
            "grief": f"{intensity_word}悲痛欲绝",
            "cold": "冷漠疏离",
            "resigned": "无奈叹息",
            "gentle": "温柔轻声",
        }

        primary_phrase = emotion_phrases.get(detail.primary, "")
        instruct = f"用{primary_phrase}的语气说"

        if detail.secondary:
            secondary_phrase = emotion_phrases.get(detail.secondary, "")
            if secondary_phrase:
                instruct += f"，带有一些{secondary_phrase}的感觉"

        # 语速控制
        if detail.arousal > 0.7:
            instruct += "，语速偏快"
        elif detail.arousal < 0.3:
            instruct += "，语速放慢"

        return instruct

    @staticmethod
    def _intensity_to_word(intensity: float) -> str:
        if intensity < 0.3:
            return "微微"
        elif intensity < 0.5:
            return "稍微"
        elif intensity < 0.7:
            return ""
        elif intensity < 0.9:
            return "非常"
        else:
            return "极其"
```

### 5.3 Index-TTS 适配器

```python
class IndexTTSEmotionAdapter(EmotionAdapter):
    """Index-TTS 通过情绪参考音频或 embedding 控制"""

    def __init__(self, emotion_audio_library):
        self.audio_library = emotion_audio_library

    def adapt(self, detail: EmotionDetail) -> dict:
        params = {}

        # IndexTTS-2 支持情绪参考音频
        ref_audio = self.audio_library.get_emotion_audio(
            detail.primary,
            detail.intensity
        )
        if ref_audio:
            params["emotion_reference_audio"] = str(ref_audio)

        return params
```

---

## 6. 叙述线索规则引擎

基于正则匹配的快速情绪推断，作为 LLM 推断的补充和校验。

```python
import re
from typing import Optional

class NarrationRuleEngine:
    """叙述线索→情绪映射规则"""

    RULES = [
        # (正则模式, 推断情绪, 默认强度)
        (r'笑了|笑着说|忍不住笑', 'happy', 0.6),
        (r'大笑|哈哈大笑|笑得前仰后合', 'happy', 0.9),
        (r'苦笑|勉强笑了笑|苦涩地笑', 'sad', 0.5),
        (r'叹了口气|长叹一声|叹息', 'sad', 0.6),
        (r'咬紧牙关|攥紧拳头|怒目', 'angry', 0.8),
        (r'吼道|怒喝|暴怒', 'angry', 0.95),
        (r'声音颤抖|哆嗦着说|发抖', 'fear', 0.7),
        (r'低下头|沉默良久|默默', 'sad', 0.5),
        (r'瞪大了眼|愣住了|目瞪口呆', 'surprise', 0.8),
        (r'冷冷地|淡淡地|漠然', 'cold', 0.6),
        (r'急切地|连忙说|赶紧', 'anxious', 0.7),
        (r'轻声|小声说|低声', 'gentle', 0.5),
        (r'嘟囔|嘀咕|小声抱怨', 'contempt', 0.4),
        (r'哽咽|泣不成声|泪流满面', 'grief', 0.9),
        (r'得意地|骄傲地|扬起下巴', 'proud', 0.7),
        (r'温柔地|轻柔地|深情地', 'romantic', 0.6),
        (r'不屑地|嗤笑|撇了撇嘴', 'contempt', 0.6),
        (r'紧张地|心跳加速|手心出汗', 'anxious', 0.7),
        (r'平静地|缓缓说|不紧不慢', 'calm', 0.4),
    ]

    @classmethod
    def infer(cls, narration_text: str) -> Optional[tuple[str, float]]:
        """从叙述文本推断情绪

        Returns: (emotion, intensity) 或 None
        """
        for pattern, emotion, intensity in cls.RULES:
            if re.search(pattern, narration_text):
                return emotion, intensity
        return None

    @classmethod
    def validate_emotion(
        cls,
        narration_text: str,
        assigned_emotion: str
    ) -> Optional[str]:
        """校验 LLM 分配的情绪是否与叙述线索矛盾

        Returns: 警告消息 或 None
        """
        rule_result = cls.infer(narration_text)
        if rule_result is None:
            return None

        rule_emotion, _ = rule_result
        if rule_emotion != assigned_emotion:
            # 检查是否为合理的近义情绪
            compatible = {
                'happy': {'excited', 'proud', 'romantic'},
                'sad': {'grief', 'resigned', 'nostalgic'},
                'angry': {'contempt', 'cold'},
                'fear': {'anxious', 'surprise'},
            }
            if assigned_emotion not in compatible.get(rule_emotion, set()):
                return (
                    f"叙述线索暗示 '{rule_emotion}'，但标注为 '{assigned_emotion}'，"
                    f"请确认是否正确"
                )
        return None
```

---

## 7. 情绪平滑器

```python
class EmotionSmoother:
    """检测并平滑不自然的情绪跳跃"""

    # 情绪距离矩阵（越大代表跳跃越突兀）
    EMOTION_DISTANCE = {
        ('happy', 'grief'): 0.95,
        ('happy', 'angry'): 0.7,
        ('calm', 'angry'): 0.8,
        ('calm', 'excited'): 0.6,
        ('grief', 'happy'): 0.95,
        ('angry', 'romantic'): 0.9,
        ('fear', 'confident'): 0.75,
    }

    JUMP_THRESHOLD = 0.7  # 超过此距离视为突兀跳跃

    def check(self, utterances: list[dict]) -> list[dict]:
        """检查相邻 utterance 间的情绪跳跃"""
        issues = []
        for i in range(1, len(utterances)):
            prev_emotion = utterances[i-1].get("emotion", "neutral")
            curr_emotion = utterances[i].get("emotion", "neutral")

            if prev_emotion == curr_emotion:
                continue

            distance = self._get_distance(prev_emotion, curr_emotion)
            if distance > self.JUMP_THRESHOLD:
                # 同一说话人的情绪跳跃更突兀
                same_speaker = (
                    utterances[i-1].get("speaker_id") ==
                    utterances[i].get("speaker_id")
                )
                if same_speaker:
                    issues.append({
                        "seq": utterances[i]["seq"],
                        "prev_seq": utterances[i-1]["seq"],
                        "prev_emotion": prev_emotion,
                        "curr_emotion": curr_emotion,
                        "distance": distance,
                        "suggestion": (
                            f"同一角色从 '{prev_emotion}' 突变为 '{curr_emotion}'，"
                            f"建议增加过渡旁白或调整情绪"
                        )
                    })
        return issues

    def _get_distance(self, emotion_a: str, emotion_b: str) -> float:
        key = (emotion_a, emotion_b)
        if key in self.EMOTION_DISTANCE:
            return self.EMOTION_DISTANCE[key]
        key_reversed = (emotion_b, emotion_a)
        if key_reversed in self.EMOTION_DISTANCE:
            return self.EMOTION_DISTANCE[key_reversed]
        return 0.3  # 默认中等距离
```

---

## 8. 情绪参考音频库

用于 Index-TTS 等需要情绪参考音频的引擎。

```
emotion_audio/
├── happy/
│   ├── low.wav        # 轻微开心
│   ├── medium.wav     # 中等开心
│   └── high.wav       # 非常开心
├── sad/
│   ├── low.wav
│   ├── medium.wav
│   └── high.wav
├── angry/
│   └── ...
└── ...（每种情绪三档强度）
```

```python
from pathlib import Path
from typing import Optional

class EmotionAudioLibrary:

    def __init__(self, library_path: Path):
        self.library_path = library_path

    def get_emotion_audio(
        self,
        emotion: str,
        intensity: float
    ) -> Optional[Path]:
        level = "low" if intensity < 0.4 else ("medium" if intensity < 0.7 else "high")
        path = self.library_path / emotion / f"{level}.wav"
        if path.exists():
            return path
        # 回退到 medium
        fallback = self.library_path / emotion / "medium.wav"
        return fallback if fallback.exists() else None
```

---

## 9. 与其他模块的四种情绪控制方式

| 方法 | 数据来源 | TTS 引擎支持 | 精度 |
|------|----------|-------------|------|
| **方法 1：tts_instruct** | `emotion_detail.tts_instruct` | Qwen3-TTS | 最高（自然语言） |
| **方法 2：情绪参考音频** | `emotion_audio_library` | IndexTTS-2 | 高 |
| **方法 3：emotion 标签** | `utterance.emotion` | 通用 | 中等 |
| **方法 4：VAD 向量** | `emotion_detail.valence/arousal/dominance` | 未来引擎 | 高（连续空间） |

---

## 10. 关联文档

| 文档 | 关系 |
|------|------|
| [`novel-tts-design.md`](novel-tts-design.md) | 总纲 |
| [`auto-character-voice-engine.md`](auto-character-voice-engine.md) | 上游：上下文情感推断引擎 |
| [`novel-audio-screenwriter-agent.md`](novel-audio-screenwriter-agent.md) | 上游：编剧 Agent 标注 emotion |
| [`module-tts-api-client.md`](module-tts-api-client.md) | 下游：TTS 客户端使用适配后的参数 |
| [`module-voice-bank.md`](module-voice-bank.md) | 协作：音色 + 情绪共同控制 |
