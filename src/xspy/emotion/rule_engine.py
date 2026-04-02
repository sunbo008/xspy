"""Rule-based emotion detection from narration cues.

Detects emotion hints from text patterns before/after dialogue,
used as a complement to LLM inference for minor characters.
"""

from __future__ import annotations

import re

from xspy.core.models import EmotionType

_CUE_MAP: list[tuple[re.Pattern[str], EmotionType]] = [
    (re.compile(r"笑[着道了]|微笑|哈哈|嘻嘻|大笑"), EmotionType.JOYFUL),
    (re.compile(r"怒[道吼]|愤怒|暴怒|咆哮|大怒"), EmotionType.FURIOUS),
    (re.compile(r"冷[笑哼]|不屑|蔑视|鄙夷"), EmotionType.CONTEMPTUOUS),
    (re.compile(r"叹[了息气]|长叹|唉"), EmotionType.SORROWFUL),
    (re.compile(r"惊[呼道讶]|吃惊|震惊|目瞪口呆"), EmotionType.SURPRISED),
    (re.compile(r"害怕|恐惧|颤抖|吓[得了]|瑟瑟"), EmotionType.FEARFUL),
    (re.compile(r"焦急|着急|急切|紧张|急[道忙]"), EmotionType.ANXIOUS),
    (re.compile(r"温柔|轻声|柔声|温和"), EmotionType.TENDER),
    (re.compile(r"得意|骄傲|自豪|昂首"), EmotionType.PROUD),
    (re.compile(r"羞[愧红]|脸红|不好意思"), EmotionType.ASHAMED),
    (re.compile(r"好奇|疑惑|纳闷|奇怪"), EmotionType.CURIOUS),
    (re.compile(r"打趣|戏谑|逗|调侃"), EmotionType.PLAYFUL),
    (re.compile(r"淡淡|平静|从容|冷静"), EmotionType.SERENE),
    (re.compile(r"痛苦|惨叫|呻吟|疼痛"), EmotionType.PAINED),
    (re.compile(r"恶心|厌恶|作呕"), EmotionType.DISGUSTED),
    (re.compile(r"哭[了泣]|流泪|泪|啜泣|呜咽"), EmotionType.SORROWFUL),
    (re.compile(r"嫉妒|眼红|不甘"), EmotionType.ENVIOUS),
    (re.compile(r"郁闷|烦[躁了]|不耐烦"), EmotionType.IRRITATED),
]

_PARAVERBAL_CUES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"叹[了息气]|长叹|唉"), "sigh"),
    (re.compile(r"笑[着道了]|哈哈|嘻嘻|大笑|轻笑"), "laughter"),
    (re.compile(r"冷笑|嗤笑|嘲笑"), "chuckle"),
    (re.compile(r"哭[了泣]|啜泣|呜咽"), "sob"),
    (re.compile(r"倒吸[一了]口"), "gasp"),
    (re.compile(r"呻吟|哼[了一]声"), "groan"),
    (re.compile(r"尖叫|惊叫"), "scream"),
    (re.compile(r"轻声|低声|悄声"), "whisper"),
]


def detect_emotion_from_cue(context_text: str) -> EmotionType | None:
    """Detect emotion from narration text using pattern matching.

    Returns the first matching emotion type, or None if no patterns match.
    """
    for pattern, emotion in _CUE_MAP:
        if pattern.search(context_text):
            return emotion
    return None


def detect_paraverbals(context_text: str) -> list[str]:
    """Detect paraverbal cues from narration context.

    Returns list of paraverbal types (e.g. ["sigh", "laughter"]).
    """
    found: list[str] = []
    for pattern, ptype in _PARAVERBAL_CUES:
        if pattern.search(context_text) and ptype not in found:
            found.append(ptype)
    return found
