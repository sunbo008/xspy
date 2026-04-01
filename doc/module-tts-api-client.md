# 模块：TTS API 客户端（TTS API Client）

> 隶属系统：小说 TTS 配音系统
> 运行端：Mac 客户端（调用方）→ Windows 服务端（被调用方）
> 上游输入：编剧 Agent 输出的结构化剧本 `utterance.text` + `emotion_detail` + `voice_ref`
> 下游输出：音频文件（WAV/MP3）→ 交给音频处理器
> 关联文档：[`novel-tts-design.md`](novel-tts-design.md)（总纲）、[`index-tts-vllm-deployment.md`](index-tts-vllm-deployment.md)（服务端部署）

---

## 1. 模块职责

| 职责 | 说明 |
|------|------|
| API 调用封装 | 统一封装 Index-TTS 1.0/1.5/2 以及 Qwen3-TTS 的 HTTP API |
| 多引擎适配 | 同一接口支持不同 TTS 引擎，透明切换 |
| 音色参数传递 | 携带 speaker_embedding / voice_clone_prompt 调用 TTS |
| 情感指令传递 | 携带 emotion / tts_instruct 参数控制语气 |
| 重试与容错 | 请求失败时自动重试，支持指数退避策略 |
| 健康检查 | 定期检测服务端可用性 |
| 响应流式接收 | 支持流式音频接收（适配 Qwen3-TTS 流式输出） |

---

## 2. 代码结构

> 项目路径：`src/xspy/tts/`（完整项目结构见 [`novel-tts-design.md`](novel-tts-design.md) §4）

```
src/xspy/tts/
├── __init__.py        # 公共导出：TTSClientFactory, TTSRequest, TTSResponse
├── base.py            # BaseTTSClient 抽象基类
├── index_v1.py        # IndexTTSClient（1.0 / 1.5）
├── index_v2.py        # IndexTTSV2Client
├── qwen.py            # QwenTTSClient（含 VoiceDesign / VoiceClone）
├── factory.py         # TTSClientFactory 工厂
├── retry.py           # RetryManager（指数退避重试）
└── health.py          # HealthChecker（服务健康检查）
```

**导入方式：**

```python
from xspy.tts import TTSClientFactory, TTSRequest
from xspy.tts.qwen import QwenTTSClient
from xspy.tts.retry import RetryManager
```

---

## 3. 数据模型

### 3.1 合成请求

```python
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

@dataclass
class TTSRequest:
    """TTS 合成请求"""
    text: str
    output_path: Path
    speaker_slug: str

    # 音色控制
    voice_ref: Optional[str] = None            # 参考音频路径
    voice_clone_prompt: Optional[str] = None   # 克隆特征文件路径
    speaker_embedding: Optional[str] = None    # embedding 路径

    # 情感控制
    emotion: str = "neutral"
    emotion_intensity: float = 0.5
    tts_instruct: Optional[str] = None         # Qwen3-TTS 自然语言指令

    # 合成参数
    sample_rate: int = 22050
    output_format: str = "wav"

    # 元数据
    novel_slug: str = ""
    chapter_num: int = 0
    seq_num: int = 0

@dataclass
class TTSResponse:
    """TTS 合成响应"""
    success: bool
    output_path: Optional[Path] = None
    duration_ms: int = 0
    error_message: Optional[str] = None
    retry_count: int = 0
```

---

## 4. 抽象基类

```python
from abc import ABC, abstractmethod

class BaseTTSClient(ABC):
    """TTS 客户端抽象基类"""

    def __init__(self, base_url: str, timeout: int = 300):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    @abstractmethod
    def synthesize(self, request: TTSRequest) -> TTSResponse:
        """合成音频"""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """服务健康检查"""
        ...

    @abstractmethod
    def get_engine_info(self) -> dict:
        """获取引擎信息（版本、能力等）"""
        ...
```

---

## 5. Index-TTS 客户端

### 5.1 Index-TTS 1.0/1.5

```python
import requests
import time
from pathlib import Path

class IndexTTSClient(BaseTTSClient):

    def __init__(self, base_url: str, model_version: str = "1.5", timeout: int = 300):
        super().__init__(base_url, timeout)
        self.model_version = model_version
        self.endpoint = f"{self.base_url}/api/v1/tts"

    def synthesize(self, request: TTSRequest) -> TTSResponse:
        start = time.time()

        payload = {
            "text": request.text,
            "output_file": str(request.output_path),
        }

        if request.voice_ref:
            payload["reference_audio"] = request.voice_ref

        try:
            resp = requests.post(
                self.endpoint,
                json=payload,
                timeout=self.timeout
            )
            elapsed = int((time.time() - start) * 1000)

            if resp.status_code == 200:
                return TTSResponse(
                    success=True,
                    output_path=request.output_path,
                    duration_ms=elapsed
                )
            else:
                return TTSResponse(
                    success=False,
                    error_message=f"HTTP {resp.status_code}: {resp.text[:200]}",
                    duration_ms=elapsed
                )
        except requests.RequestException as e:
            elapsed = int((time.time() - start) * 1000)
            return TTSResponse(
                success=False,
                error_message=str(e),
                duration_ms=elapsed
            )

    def health_check(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/docs", timeout=5)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def get_engine_info(self) -> dict:
        return {
            "engine": "Index-TTS",
            "version": self.model_version,
            "capabilities": {
                "voice_clone": True,
                "emotion_control": self.model_version == "2",
                "streaming": False,
                "instruct": False
            }
        }
```

### 5.2 IndexTTS-2

```python
class IndexTTSV2Client(BaseTTSClient):

    def __init__(self, base_url: str, timeout: int = 300):
        super().__init__(base_url, timeout)
        self.endpoint = f"{self.base_url}/api/v2/tts"

    def synthesize(self, request: TTSRequest) -> TTSResponse:
        start = time.time()

        payload = {
            "text": request.text,
            "output_file": str(request.output_path),
        }

        if request.speaker_embedding:
            payload["speaker_embedding"] = request.speaker_embedding
        if request.voice_ref:
            payload["reference_audio"] = request.voice_ref

        # IndexTTS-2 支持情绪参考音频
        if request.emotion != "neutral":
            payload["emotion"] = request.emotion

        try:
            resp = requests.post(self.endpoint, json=payload, timeout=self.timeout)
            elapsed = int((time.time() - start) * 1000)

            if resp.status_code == 200:
                return TTSResponse(success=True, output_path=request.output_path, duration_ms=elapsed)
            else:
                return TTSResponse(success=False, error_message=f"HTTP {resp.status_code}", duration_ms=elapsed)
        except requests.RequestException as e:
            return TTSResponse(success=False, error_message=str(e), duration_ms=int((time.time() - start) * 1000))

    def health_check(self) -> bool:
        try:
            return requests.get(f"{self.base_url}/docs", timeout=5).status_code == 200
        except requests.RequestException:
            return False

    def get_engine_info(self) -> dict:
        return {
            "engine": "IndexTTS-2",
            "version": "2.0",
            "capabilities": {
                "voice_clone": True,
                "emotion_control": True,
                "streaming": False,
                "instruct": False
            }
        }
```

---

## 6. Qwen3-TTS 客户端

### 6.1 三种合成模式

| 模式 | 说明 | 参数 |
|------|------|------|
| **CustomVoice** | 使用预设音色 + instruct 指令 | `voice_preset` + `instruct` |
| **VoiceDesign** | 用自然语言描述创建新声音 | `voice_description` |
| **VoiceClone** | 用参考音频克隆声音 | `reference_audio` / `voice_clone_prompt` |

### 6.2 实现

```python
import requests
import time
from typing import Optional

class QwenTTSClient(BaseTTSClient):

    def __init__(self, base_url: str, timeout: int = 300):
        super().__init__(base_url, timeout)
        self.endpoint = f"{self.base_url}/v1/audio/speech"

    def synthesize(self, request: TTSRequest) -> TTSResponse:
        start = time.time()

        payload = {
            "input": request.text,
            "response_format": request.output_format,
        }

        # 音色选择优先级：clone_prompt > voice_ref > preset
        if request.voice_clone_prompt:
            payload["voice_clone_prompt"] = request.voice_clone_prompt
        elif request.voice_ref:
            payload["reference_audio"] = request.voice_ref
        else:
            payload["voice"] = request.speaker_slug

        # 情感控制通过 instruct 参数
        if request.tts_instruct:
            payload["instruct"] = request.tts_instruct
        elif request.emotion != "neutral":
            payload["instruct"] = self._emotion_to_instruct(
                request.emotion,
                request.emotion_intensity
            )

        try:
            resp = requests.post(self.endpoint, json=payload, timeout=self.timeout)
            elapsed = int((time.time() - start) * 1000)

            if resp.status_code == 200:
                request.output_path.parent.mkdir(parents=True, exist_ok=True)
                request.output_path.write_bytes(resp.content)
                return TTSResponse(success=True, output_path=request.output_path, duration_ms=elapsed)
            else:
                return TTSResponse(success=False, error_message=f"HTTP {resp.status_code}", duration_ms=elapsed)
        except requests.RequestException as e:
            return TTSResponse(success=False, error_message=str(e), duration_ms=int((time.time() - start) * 1000))

    def voice_design(self, description: str, output_path: Path) -> TTSResponse:
        """VoiceDesign 模式：用自然语言创建新声音"""
        payload = {
            "input": "你好，很高兴认识你。今天天气真不错。",
            "voice_description": description,
            "response_format": "wav"
        }
        try:
            resp = requests.post(f"{self.base_url}/v1/audio/voice_design", json=payload, timeout=self.timeout)
            if resp.status_code == 200:
                output_path.write_bytes(resp.content)
                return TTSResponse(success=True, output_path=output_path)
            return TTSResponse(success=False, error_message=f"HTTP {resp.status_code}")
        except requests.RequestException as e:
            return TTSResponse(success=False, error_message=str(e))

    def create_clone_prompt(self, reference_audio: Path) -> Optional[bytes]:
        """从参考音频创建可复用的 voice_clone_prompt"""
        try:
            with open(reference_audio, 'rb') as f:
                resp = requests.post(
                    f"{self.base_url}/v1/audio/create_clone_prompt",
                    files={"audio": f},
                    timeout=60
                )
            if resp.status_code == 200:
                return resp.content
            return None
        except requests.RequestException:
            return None

    @staticmethod
    def _emotion_to_instruct(emotion: str, intensity: float) -> str:
        """将情感标签转换为 Qwen3-TTS instruct 自然语言"""
        intensity_word = "稍微" if intensity < 0.4 else ("" if intensity < 0.7 else "非常")
        mapping = {
            "happy": f"用{intensity_word}开心愉快的语气说",
            "sad": f"用{intensity_word}悲伤低沉的语气说",
            "angry": f"用{intensity_word}愤怒激动的语气说",
            "fear": f"用{intensity_word}恐惧紧张的语气说",
            "surprise": f"用{intensity_word}惊讶的语气说",
            "excited": f"用{intensity_word}兴奋激昂的语气说",
            "calm": "用平静舒缓的语气说",
            "confident": "用自信有力的语气说",
            "sarcastic": f"用{intensity_word}讽刺的语气说",
            "romantic": f"用{intensity_word}温柔浪漫的语气说",
        }
        return mapping.get(emotion, "")

    def health_check(self) -> bool:
        try:
            return requests.get(f"{self.base_url}/health", timeout=5).status_code == 200
        except requests.RequestException:
            return False

    def get_engine_info(self) -> dict:
        return {
            "engine": "Qwen3-TTS",
            "version": "1.0",
            "capabilities": {
                "voice_clone": True,
                "voice_design": True,
                "emotion_control": True,
                "streaming": True,
                "instruct": True
            }
        }
```

---

## 7. 重试管理器

```python
import time
import logging
from typing import Callable, TypeVar

T = TypeVar('T')
logger = logging.getLogger(__name__)

class RetryManager:
    """请求重试管理器（指数退避策略）"""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

    def execute(self, func: Callable[[], TTSResponse]) -> TTSResponse:
        last_response = None

        for attempt in range(self.max_retries + 1):
            response = func()

            if response.success:
                response.retry_count = attempt
                return response

            last_response = response
            if attempt < self.max_retries:
                delay = min(
                    self.base_delay * (self.backoff_factor ** attempt),
                    self.max_delay
                )
                logger.warning(
                    f"TTS 请求失败 (第 {attempt + 1} 次): {response.error_message}，"
                    f"{delay:.1f}s 后重试"
                )
                time.sleep(delay)

        last_response.retry_count = self.max_retries
        return last_response
```

---

## 8. 客户端工厂

```python
class TTSClientFactory:
    """TTS 客户端工厂"""

    @staticmethod
    def create(engine: str, base_url: str, **kwargs) -> BaseTTSClient:
        clients = {
            "index-tts-1.5": lambda: IndexTTSClient(base_url, model_version="1.5", **kwargs),
            "index-tts-2": lambda: IndexTTSV2Client(base_url, **kwargs),
            "qwen3-tts": lambda: QwenTTSClient(base_url, **kwargs),
        }

        factory = clients.get(engine)
        if factory is None:
            raise ValueError(f"未知 TTS 引擎: {engine}，支持: {list(clients.keys())}")
        return factory()
```

---

## 9. 服务端配置参考

### 9.1 Index-TTS 端点约定

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/tts` | POST | Index-TTS 1.0/1.5 合成 |
| `/api/v2/tts` | POST | IndexTTS-2 合成 |
| `/docs` | GET | Swagger 文档（兼做健康检查） |

### 9.2 Qwen3-TTS 端点约定

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/audio/speech` | POST | 语音合成 |
| `/v1/audio/voice_design` | POST | VoiceDesign 模式 |
| `/v1/audio/create_clone_prompt` | POST | 创建克隆特征 |
| `/health` | GET | 健康检查 |

---

## 10. 多引擎降级策略

```
请求到达
    ↓
首选引擎（Qwen3-TTS / IndexTTS-2）
    ↓ 失败
重试 N 次（指数退避）
    ↓ 仍然失败
降级到备用引擎（Index-TTS 1.5）
    ↓ 失败
标记任务失败，写入失败队列
    ↓
由任务管理器在服务恢复后重试
```

---

## 11. 关联文档

| 文档 | 关系 |
|------|------|
| [`novel-tts-design.md`](novel-tts-design.md) | 总纲 |
| [`index-tts-vllm-deployment.md`](index-tts-vllm-deployment.md) | 服务端部署 |
| [`module-voice-bank.md`](module-voice-bank.md) | 提供 voice_ref / voice_clone_prompt |
| [`module-emotion-system.md`](module-emotion-system.md) | 提供 emotion / tts_instruct |
| [`module-audio-processor.md`](module-audio-processor.md) | 下游消费音频文件 |
