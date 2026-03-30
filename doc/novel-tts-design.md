# 小说 TTS 配音系统设计方案

## 📋 1. 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        小说 TTS 配音系统                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   │
│  │   Mac OpenClaw│────▶│  Windows API │────▶│  RTX 3070 Ti  │   │
│  │   (客户端)    │     │  (中间层)    │     │  (推理引擎)  │   │
│  └──────────────┘     └──────────────┘     └──────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 2. 系统组件

### 2.1 客户端（Mac OpenClaw）

**职责：**
- 小说文件管理（读取、解析、章节分割）
- 任务调度（批量配音任务队列）
- 音频合成请求（调用 Windows API）
- 音频文件管理（保存、索引、合并）

**技术栈：**
- Python + OpenClaw 集成
- 文本解析：`epublib3`, `PyPDF2`
- 音频处理：`pydub`

### 2.2 服务端（Windows PC）

**职责：**
- 提供 TTS API 服务
- GPU 推理加速
- 请求队列管理

**技术栈：**
- FastAPI
- vLLM + Index-TTS
- RTX 3070 Ti (8GB 显存)

---

## 🏗️ 3. 详细设计

### 3.1 客户端架构

```
小说配音客户端/
├── config.py              # 配置文件
├──小说解析器/
│   ├── __init__.py
│   ├── txt_parser.py      # TXT 文件解析
│   ├── epub_parser.py     # EPUB 文件解析
│   └── pdf_parser.py      # PDF 文件解析
├──章节分割器/
│   ├── __init__.py
│   └── chapter_splitter.py # 按章节分割文本
├── TTS 客户端/
│   ├── __init__.py
│   ├── api_client.py      # API 调用客户端
│   └── retry_manager.py   # 重试机制
├── 音频处理器/
│   ├── __init__.py
│   ├── audio_generator.py # 音频生成器
│   └── audio_merger.py    # 音频合并器
├── 任务管理器/
│   ├── __init__.py
│   └── task_queue.py      # 任务队列管理
├── main.py                # 主程序入口
└── cli.py                 # 命令行工具
```

### 3.2 服务端架构

```
Windows 服务端/
├── api_server.py          # Index-TTS 1.0/1.5 API
├── api_server_v2.py       # IndexTTS-2 API
├── config.py              # 服务端配置
└── requirements.txt       # 依赖
```

---

## 📦 4. 技术选型

### 4.1 文本解析

| 格式 | 库 | 说明 |
|------|-----|------|
| TXT | `io` (内置) | 直接读取 |
| EPUB | `epublib3` | 支持 EPUB3 |
| PDF | `PyPDF2` | 基础 PDF 解析 |

### 4.2 TTS 引擎

| 引擎 | 优势 | 劣势 |
|------|------|------|
| **Index-TTS 1.5** | 中文优化，质量高 | 需要 GPU |
| **IndexTTS-2** | 最新，多语言 | 更重，需要更多显存 |

### 4.3 音频处理

| 库 | 用途 |
|-----|------|
| `pydub` | 音频剪辑、合并、格式转换 |
| `ffmpeg` | 底层音频处理 |

---

## 💻 5. 实现方案

### 5.1 客户端实现

#### 配置文件 (config.py)

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ServerConfig:
    """服务端配置"""
    host: str = "192.168.x.x"  # Windows 局域网 IP
    port: int = 6006
    model_version: str = "1.5"  # 1.0, 1.5, or 2

@dataclass
class TTSConfig:
    """TTS 配置"""
    output_format: str = "mp3"
    sample_rate: int = 22050
    batch_size: int = 10  # 批量处理大小

@dataclass
class AppConfig:
    """应用配置"""
    server: ServerConfig = None
    tts: TTSConfig = None
    output_dir: str = "output"
    
    def __post_init__(self):
        if self.server is None:
            self.server = ServerConfig()
        if self.tts is None:
            self.tts = TTSConfig()
```

#### 文本解析器 (parsers/txt_parser.py)

```python
from pathlib import Path
from typing import Generator, Tuple

class TXTParser:
    """TXT 文件解析器"""
    
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.content = filepath.read_text(encoding='utf-8')
    
    def get_chapters(self) -> Generator[Tuple[str, str], None, None]:
        """按章节分割文本
        
        支持以下章节标记：
        - "第 X 章"
        - "Chapter X"
        - "=== 章节名 ==="
        """
        import re
        
        # 中文章节标记
        chapter_pattern = r'第 [一二三四五六七八九十百千万 0-9]+[章回节]'
        
        matches = list(re.finditer(chapter_pattern, self.content))
        
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(self.content)
            chapter_title = match.group()
            chapter_text = self.content[start:end].strip()
            
            yield chapter_title, chapter_text
```

#### TTS 客户端 (tts_client/api_client.py)

```python
import requests
import json
from typing import Optional

class TTSApiClient:
    """TTS API 客户端"""
    
    def __init__(self, base_url: str, model_version: str = "1.5"):
        self.base_url = base_url.rstrip('/')
        self.model_version = model_version
        
        if model_version == "2":
            self.endpoint = f"{self.base_url}/api/v2/tts"
        else:
            self.endpoint = f"{self.base_url}/api/v{model_version}/tts"
    
    def synthesize(self, text: str, output_path: str) -> bool:
        """合成音频
        
        Args:
            text: 要合成的文本
            output_path: 输出文件路径
            
        Returns:
            是否成功
        """
        try:
            response = requests.post(
                self.endpoint,
                json={
                    "text": text,
                    "output_file": output_path
                },
                timeout=300  # 长时间超时，因为 TTS 可能需要很久
            )
            
            if response.status_code == 200:
                return True
            else:
                print(f"TTS 失败：{response.status_code}")
                return False
                
        except Exception as e:
            print(f"TTS 请求失败：{e}")
            return False
```

#### 音频生成器 (audio/audio_generator.py)

```python
from pathlib import Path
from typing import Generator
from tts_client.api_client import TTSApiClient
from config import AppConfig

class AudioGenerator:
    """音频生成器"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.api_client = TTSApiClient(
            f"http://{config.server.host}:{config.server.port}",
            config.server.model_version
        )
    
    def generate_audio(self, chapter_title: str, chapter_text: str) -> str:
        """生成章节音频
        
        Returns:
            输出文件路径
        """
        output_path = Path(self.config.output_dir) / f"{chapter_title}.mp3"
        
        if self.api_client.synthesize(chapter_text, str(output_path)):
            return str(output_path)
        else:
            raise Exception(f"音频生成失败：{chapter_title}")
```

#### 任务管理器 (task_manager/task_queue.py)

```python
import queue
import threading
from typing import Callable, Any
from pathlib import Path

class TaskQueue:
    """任务队列管理器"""
    
    def __init__(self, max_workers: int = 4):
        self.task_queue = queue.Queue()
        self.max_workers = max_workers
        self.workers = []
        self._start_workers()
    
    def _start_workers(self):
        """启动工作线程"""
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker_loop, daemon=True)
            worker.start()
            self.workers.append(worker)
    
    def _worker_loop(self):
        """工作线程循环"""
        while True:
            task = self.task_queue.get()
            if task is None:
                break
            
            func, args, kwargs = task
            try:
                func(*args, **kwargs)
            except Exception as e:
                print(f"任务执行失败：{e}")
            
            self.task_queue.task_done()
    
    def add_task(self, func: Callable, *args, **kwargs):
        """添加任务"""
        self.task_queue.put((func, args, kwargs))
    
    def wait_completion(self):
        """等待所有任务完成"""
        self.task_queue.join()
    
    def shutdown(self):
        """关闭工作线程"""
        for _ in range(self.max_workers):
            self.task_queue.put(None)
```

---

## 🚀 6. 使用示例

### 6.1 命令行使用

```bash
# 基本使用
python main.py novel.epub --output output/

# 指定服务端
python main.py novel.txt --host 192.168.1.100 --port 6006

# 指定版本
python main.py novel.pdf --version 2

# 批量处理多个文件
python main.py *.epub --batch
```

### 6.2 Python API 使用

```python
from pathlib import Path
from小说解析器.txt_parser import TXTParser
from tts_client.api_client import TTSApiClient
from audio.audio_generator import AudioGenerator
from task_manager.task_queue import TaskQueue
from config import AppConfig

# 配置
config = AppConfig(
    server=ServerConfig(host="192.168.1.100", port=6006, model_version="1.5"),
    output_dir="output/"
)

# 解析小说
parser = TXTParser(Path("novel.txt"))

# 创建任务队列
queue = TaskQueue(max_workers=4)

# 创建音频生成器
generator = AudioGenerator(config)

# 处理每个章节
for chapter_title, chapter_text in parser.get_chapters():
    # 添加任务到队列
    queue.add_task(generator.generate_audio, chapter_title, chapter_text)

# 等待所有任务完成
queue.wait_completion()
queue.shutdown()

print("所有章节音频生成完成！")
```

---

## 📋 7. 部署步骤

### 7.1 Windows 服务端部署

1. **安装 WSL2**（如未安装）
   ```bash
   wsl --install
   ```

2. **安装 CUDA 和依赖**
   ```bash
   # WSL 内执行
   conda create -n index-tts-vllm python=3.12 -y
   conda activate index-tts-vllm
   pip install uv
   uv pip install -r requirements.txt -c overrides.txt
   ```

3. **下载模型权重**
   ```bash
   # 下载 Index-TTS 1.5 权重
   huggingface-cli download ksuriuri/Index-TTS-1.5-vLLM --local-dir ./checkpoints/Index-TTS-1.5-vLLM
   ```

4. **启动 API 服务**
   ```bash
   python api_server.py \
     --model_dir ./checkpoints/Index-TTS-1.5-vLLM \
     --host 0.0.0.0 \
     --port 6006 \
     --gpu_memory_utilization 0.25
   ```

### 7.2 Mac 客户端部署

```bash
# 克隆客户端代码
git clone https://github.com/your-repo/novel-tts-client.git
cd novel-tts-client

# 安装依赖
pip install -r requirements.txt

# 配置服务端 IP
cp config.example.py config.py
# 编辑 config.py，设置正确的服务端 IP

# 开始配音
python main.py novel.epub
```

---

## 🔧 8. 配置说明

### 8.1 服务端配置 (config.py)

```python
SERVER_CONFIG = {
    "host": "0.0.0.0",      # 监听地址
    "port": 6006,           # 端口
    "gpu_memory_utilization": 0.25,  # GPU 显存占用比例
}
```

### 8.2 客户端配置 (config.py)

```python
SERVER_CONFIG = {
    "host": "192.168.1.100",  # Windows 局域网 IP
    "port": 6006,
    "model_version": "1.5",   # 1.0, 1.5, or 2
}

TTS_CONFIG = {
    "output_format": "mp3",
    "sample_rate": 22050,
    "batch_size": 10,
}

OUTPUT_CONFIG = {
    "output_dir": "output",
    "file_naming": "{chapter_title}.mp3",
}
```

---

## 📊 9. 性能预估

| 项目 | 预估 | 说明 |
|------|------|------|
| 单章文本 | ~5000 字 | 平均小说章节长度 |
| 合成时间 | ~10-30 秒 | 取决于 GPU 性能和文本长度 |
| 并发数 | 4-8 个 | 取决于 RTX 3070 Ti 显存 |
| 每小时处理量 | ~100-200 章 | 4 并发下 |

---

## ✅ 10. 验证清单

- [ ] Windows 服务已启动并监听 0.0.0.0:6006
- [ ] Mac 可以访问 Windows 服务（`curl http://192.168.x.x:6006/docs`）
- [ ] 客户端配置了正确的服务端 IP
- [ ] 测试文件可以成功合成音频
- [ ] 批量处理功能正常工作
- [ ] 音频文件可以正常播放

---

## 🎭 11. 角色音色与情绪控制

### 11.1 角色音色库系统

```
角色音色库
├── 每个角色有唯一的 reference_audio
├── 从 reference_audio 提取 speaker_embedding
└── 同一个角色的所有对话使用相同的 speaker_embedding
```

**实现要点：**
- 为每个角色录制 5-10 秒清晰朗读音频
- 使用 IndexTTS-2 的 speaker embedding 机制保持音色一致性
- 保存角色音色配置到 JSON 文件

### 11.2 情绪控制系统

**四种情绪控制方法：**

| 方法 | 说明 | 适用场景 |
|------|------|----------|
| **方法 1：默认模式** | 从 speaker reference 提取情绪 | 保持自然情感连贯性 |
| **方法 2：情绪参考音频** | 提供额外音频控制情绪 | 精确控制特定情绪 |
| **方法 3：情绪向量** | 使用向量精确控制 | 技术型控制 |
| **方法 4：文本情绪描述** | 使用文本描述情绪 | 简单快速控制 |

**情绪类型定义：**

```python
class EmotionType(Enum):
    HAPPY = "happy"           # 快乐
    SAD = "sad"               # 悲伤
    ANGRY = "angry"           # 愤怒
    FEAR = "fear"             # 恐惧
    SURPRISE = "surprise"     # 惊讶
    NEUTRAL = "neutral"       # 中性
    EXCITED = "excited"       # 兴奋
    CALM = "calm"             # 平静
    CONFIDENT = "confident"   # 自信
    SARCASTIC = "sarcastic"   # 讽刺
    ROMANTIC = "romantic"     # 浪漫
```

### 11.3 小说文本处理流程

```
小说文本 → 章节分割 → ┌──────────────────────────┐ → TTS 合成 → 音频合并
                      │  编剧 Agent（剧本结构化）  │
                      │  · 对话提取               │
                      │  · 角色识别 & 绑定         │
                      │  · 情绪标注               │
                      └──────────────────────────┘
                                    ↓
                         结构化剧本（JSON）
                                    ↓
                      speaker_embedding + emotion_control
```

> 编剧 Agent 的详细设计见 [`doc/novel-audio-screenwriter-agent.md`](novel-audio-screenwriter-agent.md)

**处理流程：**
1. 按章节分割文本（客户端解析器，见 3.1 节）
2. **编剧 Agent** 接收章节正文，输出结构化剧本：
   - 2a. 提取对话、旁白、内心独白（支持多种对话标记格式）
   - 2b. 识别说话人角色并绑定 `speaker_slug`
   - 2c. 为每条话语单元标注 `emotion`（对齐 `EmotionType`）
   - 2d. 输出 `cast_registry` + `scenes[].utterances[]`（Schema 见编剧 Agent 文档第 4 节）
3. 由剧本中的 `speaker_id` 查表获取角色的 speaker embedding
4. 调用 TTS 引擎合成音频

---

### 11.4 音频文件命名规范

#### 11.4.1 命名格式设计原则

1. **排序友好** - 文件名按字母顺序排序时，能保持逻辑顺序（章节→角色→顺序）
2. **唯一性** - 每个音频文件有唯一标识，避免重名冲突
3. **可读性** - 文件名包含足够的信息，便于人工识别
4. **兼容性** - 避免特殊字符，兼容所有文件系统
5. **引擎友好** - 便于 TTS 引擎解析和生成

#### 11.4.2 命名格式

```
{novel_slug}-{chapter_num:04d}-{speaker_slug}-{emotion}-{seq_num:06d}.mp3
```

**字段说明：**

| 字段 | 说明 | 示例 | 说明 |
|------|------|------|------|
| `novel_slug` | 小说名（简化） | `dragon_ball` | 去除空格和特殊字符，转为小写，下划线分隔 |
| `chapter_num` | 章节号（4 位） | `0001` | 固定 4 位，不足补 0（支持最多 9999 章） |
| `speaker_slug` | 角色名（简化） | `goku` | 去除特殊字符，转为小写，英文用拼音或英文名 |
| `emotion` | 情绪类型 | `happy` | 固定英文情绪标签 |
| `seq_num` | 全局序号（6 位） | `000001` | 章节内全局序号（包含角色对话、旁白等），支持最多 999999 条 |

#### 11.4.3 文件名生成器

```python
from pathlib import Path
from typing import NamedTuple
from datetime import datetime

class AudioFileInfo(NamedTuple):
    """音频文件信息"""
    novel_slug: str           # 小说名（简化）
    chapter_num: int          # 章节号
    speaker_slug: str         # 角色名（简化）
    emotion: str              # 情绪类型
    seq_num: int              # 全局序号（章节内）
    timestamp: datetime       # 生成时间

class AudioFilenameGenerator:
    """音频文件名生成器"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def sanitize_slug(self, text: str) -> str:
        """简化文本为 slug
        
        规则：
        1. 转为小写
        2. 移除特殊字符（保留字母、数字、下划线）
        3. 替换空格为下划线
        """
        import re
        text = text.lower()
        text = re.sub(r'[^a-z0-9\u4e00-\u9fa5_]', '', text)
        text = re.sub(r'[\s]+', '_', text)
        return text
    
    def generate_filename(self, info: AudioFileInfo) -> Path:
        """生成音频文件名
        
        格式：{novel_slug}-{chapter_num:04d}-{speaker_slug}-{emotion}-{seq_num:06d}.mp3
        """
        filename = (
            f"{info.novel_slug}-"
            f"{info.chapter_num:04d}-"
            f"{info.speaker_slug}-"
            f"{info.emotion}-"
            f"{info.seq_num:06d}.mp3"
        )
        return self.output_dir / filename
    
    def generate_full_path(self, info: AudioFileInfo) -> Path:
        """生成完整文件路径
        
        格式：{output_dir}/{novel_slug}/{novel_slug}-{chapter_num:04d}-{speaker_slug}-{emotion}-{seq_num:06d}.mp3
        """
        novel_dir = self.output_dir / info.novel_slug
        novel_dir.mkdir(parents=True, exist_ok=True)
        return novel_dir / self.generate_filename(info)
```

#### 11.4.4 使用示例

```python
from pathlib import Path
from novel_tts_design import AudioFilenameGenerator, AudioFileInfo
from datetime import datetime

# 初始化生成器
generator = AudioFilenameGenerator(Path("output"))

# 示例 1：孙悟空 - 第 1 章 - 快乐情绪 - 全局第 1 句
info1 = AudioFileInfo(
    novel_slug="dragon_ball",
    chapter_num=1,
    speaker_slug="goku",
    emotion="happy",
    seq_num=1,        # 全局序号
    timestamp=datetime.now()
)

path1 = generator.generate_full_path(info1)
print(path1)
# 输出：output/dragon_ball/dragon_ball-0001-goku-happy-000001.mp3

# 示例 2：贝吉塔 - 第 1 章 - 平静情绪 - 全局第 2 句
info2 = AudioFileInfo(
    novel_slug="dragon_ball",
    chapter_num=1,
    speaker_slug="vegeta",
    emotion="calm",
    seq_num=2,        # 全局序号
    timestamp=datetime.now()
)

path2 = generator.generate_full_path(info2)
print(path2)
# 输出：output/dragon_ball/dragon_ball-0001-vegeta-calm-000002.mp3

# 示例 3：孙悟空 - 第 1 章 - 愤怒情绪 - 全局第 3 句
info3 = AudioFileInfo(
    novel_slug="dragon_ball",
    chapter_num=1,
    speaker_slug="goku",
    emotion="angry",
    seq_num=3,        # 全局序号
    timestamp=datetime.now()
)

path3 = generator.generate_full_path(info3)
print(path3)
# 输出：output/dragon_ball/dragon_ball-0001-goku-angry-000003.mp3

# 示例 4：旁白 - 第 1 章 - 中性情绪 - 全局第 4 句
info4 = AudioFileInfo(
    novel_slug="dragon_ball",
    chapter_num=1,
    speaker_slug="narrator",  # 旁白特殊标记
    emotion="neutral",
    seq_num=4,        # 全局序号
    timestamp=datetime.now()
)

path4 = generator.generate_full_path(info4)
print(path4)
# 输出：output/dragon_ball/dragon_ball-0001-narrator-neutral-000004.mp3
```

#### 11.4.5 文件排序效果

生成的文件会按以下顺序排列：

```
dragon_ball/
├── dragon_ball-0001-goku-happy-000001.mp3
├── dragon_ball-0001-vegeta-calm-000002.mp3
├── dragon_ball-0001-goku-angry-000003.mp3
├── dragon_ball-0001-narrator-neutral-000004.mp3
├── dragon_ball-0002-goku-happy-000001.mp3
├── dragon_ball-0002-goku-angry-000002.mp3
└── dragon_ball-0002-vegeta-calm-000003.mp3
```

**排序特点：**
1. 按小说名分组
2. 同一小说内按章节号排序
3. 同一章节内按角色名排序
4. **同一角色内按全局序号排序**（不是角色序号）

**全局序号优势：**
- 引擎可以按序号直接播放整个章节
- 不需要维护每个角色的独立计数器
- 旁白、场景描述等都可以统一编号

#### 11.4.6 旁白与特殊元素处理

**特殊元素类型：**

| 类型 | 角色名标记 | 说明 |
|------|------------|------|
| 角色对话 | 角色名（如 `goku`） | 正常对话 |
| 旁白 | `narrator` | 叙述性文字 |
| 场景描述 | `desc` | 场景、环境描述 |
| 内心独白 | `inner` | 角色内心活动 |
| 音效提示 | `sfx` | 音效说明（不生成音频） |

**旁白处理示例：**

```python
# 旁白使用 narrator 作为角色名
info_narrator = AudioFileInfo(
    novel_slug="dragon_ball",
    chapter_num=1,
    speaker_slug="narrator",  # 旁白特殊标记
    emotion="neutral",
    seq_num=4,        # 全局序号
    timestamp=datetime.now()
)

# 场景描述使用 desc 作为角色名
info_desc = AudioFileInfo(
    novel_slug="dragon_ball",
    chapter_num=1,
    speaker_slug="desc",  # 场景描述特殊标记
    emotion="neutral",
    seq_num=5,        # 全局序号
    timestamp=datetime.now()
)

# 内心独白使用 inner 作为角色名
info_inner = AudioFileInfo(
    novel_slug="dragon_ball",
    chapter_num=1,
    speaker_slug="inner",  # 内心独白特殊标记
    emotion="sad",
    seq_num=6,        # 全局序号
    timestamp=datetime.now()
)
```

**旁白音色策略：**

1. **统一旁白音色** - 所有旁白使用同一个 speaker embedding
2. **可配置** - 在音色库中为 narrator 配置专门的音色
3. **中性情绪** - 旁白通常使用 neutral 情绪

---

#### 11.4.7 TTS 引擎集成

```python
from tts_engine import TTSEngine
from novel_tts_design import AudioFilenameGenerator, AudioFileInfo

def synthesize_audio(
    tts_engine: TTSEngine,
    info: AudioFileInfo,
    text: str,
    speaker_embedding: torch.Tensor
):
    """合成音频
    
    1. 生成文件名
    2. 调用 TTS 引擎合成
    3. 返回文件路径
    """
    generator = AudioFilenameGenerator(Path("output"))
    output_path = generator.generate_full_path(info)
    
    # 调用 TTS 引擎
    tts_engine.synthesize(
        text=text,
        speaker_embedding=speaker_embedding,
        output_path=output_path,
        emotion=info.emotion
    )
    
    return output_path
```

---

## 📝 12. 后续优化方向

1. **Web UI** - 提供图形化界面
2. **进度显示** - 实时显示处理进度
3. **断点续传** - 支持中断后继续处理
4. **音频后处理** - 添加淡入淡出、音量标准化
5. **角色声线库扩展** - 支持更多角色和声线类型
6. **自动情绪标注** - 使用 NLP 模型自动标注情绪（已由编剧 Agent 部分覆盖，见下方关联文档）
7. **情感曲线** - 支持长文本的情感变化曲线
8. **多角色对话合并** - 将同一场景的对话合并为场景音频（编剧 Agent 已输出 `scene` 粒度分组）

---

## 📎 13. 关联文档

| 文档 | 说明 |
|------|------|
| [`doc/novel-audio-screenwriter-agent.md`](novel-audio-screenwriter-agent.md) | 有声书编剧 Agent 设计：剧本结构化、角色表、情绪标注、输出 Schema |
| [`doc/index-tts-vllm-deployment.md`](index-tts-vllm-deployment.md) | Index-TTS vLLM 部署指南 |

> **变更同步提醒：** 若本文档的 `EmotionType`（11.2 节）或音频命名规范（11.4 节）发生变更，需同步更新编剧 Agent 文档的第 3、4、7 节。

## 14. 参考资料
1. https://github.com/DrewThomasson/ebook2audiobookSTYLETTS2
2. https://github.com/cosin2077/easyVoice
3. https://github.com/suno-ai/bark
4. https://github.com/QwenLM/Qwen3-TTS
