# 模块：任务管理器（Task Manager）

> 隶属系统：小说 TTS 配音系统
> 运行端：Mac 客户端
> 职责：调度、并发控制、进度追踪、断点续传
> 关联文档：[`novel-tts-design.md`](novel-tts-design.md)（总纲）

---

## 1. 模块职责

| 职责 | 说明 |
|------|------|
| 任务队列管理 | 将全书处理拆分为可独立执行的任务单元 |
| 并发控制 | 限制同时运行的任务数，匹配 GPU 并发能力 |
| 进度追踪 | 实时显示处理进度（百分比、已完成/总数、预计剩余时间） |
| 断点续传 | 中断后可从上次停止处继续，不重复已完成的工作 |
| 失败重试 | 失败任务自动重试，超限后进入失败队列 |
| 状态持久化 | 所有任务状态写入磁盘，进程重启后可恢复 |

---

## 2. 代码结构

> 项目路径：`src/xspy/task/`（完整项目结构见 [`novel-tts-design.md`](novel-tts-design.md) §4）

```
src/xspy/task/
├── __init__.py          # 公共导出：TaskQueue, WorkerPool, CheckpointManager
├── models.py            # Task / ProcessingPlan / TaskType / TaskStatus
├── queue.py             # TaskQueue（基于 DAG 依赖的任务队列）
├── worker.py            # WorkerPool（工作线程池）
├── progress.py          # ProgressTracker + CLIProgress（进度追踪与显示）
├── checkpoint.py        # CheckpointManager（断点续传、状态持久化）
└── planner.py           # PlanGenerator（根据解析结果生成处理计划）
```

**关联的数据目录：**

```
data/checkpoints/           # 断点续传状态文件（运行时，.gitignore）
```

**导入方式：**

```python
from xspy.task import TaskQueue, WorkerPool, CheckpointManager
from xspy.task.planner import PlanGenerator
from xspy.task.models import Task, TaskType, TaskStatus
```

---

## 3. 数据模型

### 3.1 任务类型

```python
from enum import Enum

class TaskType(Enum):
    PARSE = "parse"                    # 小说解析
    CHARACTER_ANALYSIS = "char_analysis"  # 角色分析（全局）
    VOICE_DESIGN = "voice_design"      # 音色设计
    SCREENWRITE = "screenwrite"        # 编剧（逐章）
    TTS_SYNTHESIZE = "tts_synthesize"  # TTS 合成（逐 utterance）
    AUDIO_MERGE = "audio_merge"        # 音频合并（逐章）
    POST_PROCESS = "post_process"      # 后处理
    BOOK_ASSEMBLE = "book_assemble"    # 全书组装
```

### 3.2 任务状态

```python
class TaskStatus(Enum):
    PENDING = "pending"        # 等待执行
    QUEUED = "queued"          # 已入队
    RUNNING = "running"        # 执行中
    SUCCESS = "success"        # 成功
    FAILED = "failed"          # 失败
    RETRYING = "retrying"      # 重试中
    CANCELLED = "cancelled"    # 已取消
    SKIPPED = "skipped"        # 跳过（断点续传时已完成的任务）
```

### 3.3 任务单元

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any

@dataclass
class Task:
    task_id: str
    task_type: TaskType
    status: TaskStatus = TaskStatus.PENDING

    # 任务参数
    params: dict = field(default_factory=dict)

    # 依赖关系
    depends_on: list[str] = field(default_factory=list)

    # 执行信息
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Any] = None

    # 进度（用于长时间任务）
    progress_current: int = 0
    progress_total: int = 0
```

### 3.4 全书处理计划

```python
@dataclass
class ProcessingPlan:
    """全书处理计划"""
    novel_slug: str
    total_chapters: int
    tasks: list[Task] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def completed_count(self) -> int:
        return sum(1 for t in self.tasks if t.status == TaskStatus.SUCCESS)

    @property
    def failed_count(self) -> int:
        return sum(1 for t in self.tasks if t.status == TaskStatus.FAILED)

    @property
    def progress_percent(self) -> float:
        if not self.tasks:
            return 0.0
        return self.completed_count / len(self.tasks) * 100
```

---

## 4. 任务 DAG（依赖关系图）

```
[parse]
    ↓
[char_analysis]  ← 全局一次
    ↓
[voice_design]   ← 全局一次（依赖 char_analysis）
    ↓
┌────────────────────────────────────────────┐
│  以下按章节并行（每章独立的任务链）           │
│                                            │
│  [screenwrite_ch01] ← 依赖 char_analysis   │
│       ↓                                    │
│  [tts_ch01_utt001] ← 依赖 screenwrite     │
│  [tts_ch01_utt002]    + voice_design       │
│  [tts_ch01_utt003]                         │
│       ↓ （所有 utt 完成后）                 │
│  [audio_merge_ch01]                        │
│       ↓                                    │
│  [post_process_ch01]                       │
│                                            │
│  [screenwrite_ch02] （可与 ch01 并行）      │
│       ↓                                    │
│  ...                                       │
└────────────────────────────────────────────┘
    ↓ （所有章节完成后）
[book_assemble]
```

---

## 5. 任务队列核心

```python
import threading
from collections import defaultdict
from typing import Callable

class TaskQueue:
    """基于依赖关系的任务队列"""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.tasks: dict[str, Task] = {}
        self.lock = threading.Lock()
        self.ready_event = threading.Event()
        self._callbacks: dict[str, list[Callable]] = defaultdict(list)

    def add_task(self, task: Task):
        with self.lock:
            self.tasks[task.task_id] = task
            if not task.depends_on:
                task.status = TaskStatus.QUEUED
        self.ready_event.set()

    def get_ready_tasks(self, limit: int = None) -> list[Task]:
        """获取所有依赖已满足的待执行任务"""
        with self.lock:
            ready = []
            for task in self.tasks.values():
                if task.status != TaskStatus.QUEUED:
                    continue
                deps_met = all(
                    self.tasks[dep].status == TaskStatus.SUCCESS
                    for dep in task.depends_on
                    if dep in self.tasks
                )
                if deps_met:
                    ready.append(task)
                    if limit and len(ready) >= limit:
                        break
            return ready

    def mark_complete(self, task_id: str, result: Any = None):
        with self.lock:
            task = self.tasks[task_id]
            task.status = TaskStatus.SUCCESS
            task.completed_at = datetime.now()
            task.result = result

            # 检查下游任务是否可以入队
            for t in self.tasks.values():
                if task_id in t.depends_on and t.status == TaskStatus.PENDING:
                    deps_met = all(
                        self.tasks[d].status == TaskStatus.SUCCESS
                        for d in t.depends_on
                        if d in self.tasks
                    )
                    if deps_met:
                        t.status = TaskStatus.QUEUED

        self.ready_event.set()

    def mark_failed(self, task_id: str, error: str):
        with self.lock:
            task = self.tasks[task_id]
            if task.retry_count < task.max_retries:
                task.status = TaskStatus.RETRYING
                task.retry_count += 1
                task.error_message = error
                task.status = TaskStatus.QUEUED
            else:
                task.status = TaskStatus.FAILED
                task.error_message = error
                task.completed_at = datetime.now()
```

---

## 6. 工作线程池

```python
import concurrent.futures
import logging

logger = logging.getLogger(__name__)

class WorkerPool:
    """工作线程池"""

    def __init__(
        self,
        task_queue: TaskQueue,
        task_executor: Callable[[Task], Any],
        max_workers: int = 4
    ):
        self.queue = task_queue
        self.executor = task_executor
        self.max_workers = max_workers
        self._running = False

    def start(self):
        self._running = True
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            while self._running:
                ready = self.queue.get_ready_tasks(limit=self.max_workers)
                if not ready:
                    if self._all_done():
                        break
                    self.queue.ready_event.wait(timeout=1.0)
                    self.queue.ready_event.clear()
                    continue

                futures = {}
                for task in ready:
                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.now()
                    future = pool.submit(self.executor, task)
                    futures[future] = task

                for future in concurrent.futures.as_completed(futures):
                    task = futures[future]
                    try:
                        result = future.result()
                        self.queue.mark_complete(task.task_id, result)
                        logger.info(f"任务完成: {task.task_id}")
                    except Exception as e:
                        self.queue.mark_failed(task.task_id, str(e))
                        logger.error(f"任务失败: {task.task_id} - {e}")

    def stop(self):
        self._running = False

    def _all_done(self) -> bool:
        return all(
            t.status in (TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.SKIPPED)
            for t in self.queue.tasks.values()
        )
```

---

## 7. 进度追踪器

### 7.1 进度数据

```python
from dataclasses import dataclass

@dataclass
class ProgressInfo:
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    running_tasks: int
    pending_tasks: int

    current_phase: str             # "解析" / "角色分析" / "TTS合成" 等
    current_chapter: int = 0
    total_chapters: int = 0

    elapsed_seconds: float = 0.0
    estimated_remaining_seconds: float = 0.0

    @property
    def percent(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.completed_tasks / self.total_tasks * 100
```

### 7.2 命令行进度显示

```python
import sys
import time

class CLIProgress:
    """命令行进度条"""

    def __init__(self, task_queue: TaskQueue):
        self.queue = task_queue
        self._start_time = time.time()

    def display(self):
        info = self._gather_info()
        bar_width = 40
        filled = int(bar_width * info.percent / 100)
        bar = '█' * filled + '░' * (bar_width - filled)

        eta = self._format_time(info.estimated_remaining_seconds)
        elapsed = self._format_time(info.elapsed_seconds)

        line = (
            f"\r[{bar}] {info.percent:.1f}% "
            f"({info.completed_tasks}/{info.total_tasks}) "
            f"| 阶段: {info.current_phase} "
            f"| 耗时: {elapsed} "
            f"| 预计剩余: {eta} "
            f"| 失败: {info.failed_tasks}"
        )
        sys.stdout.write(line)
        sys.stdout.flush()

    def _gather_info(self) -> ProgressInfo:
        tasks = list(self.queue.tasks.values())
        completed = sum(1 for t in tasks if t.status == TaskStatus.SUCCESS)
        failed = sum(1 for t in tasks if t.status == TaskStatus.FAILED)
        running = sum(1 for t in tasks if t.status == TaskStatus.RUNNING)
        elapsed = time.time() - self._start_time

        rate = completed / elapsed if elapsed > 0 else 0
        remaining = (len(tasks) - completed - failed) / rate if rate > 0 else 0

        return ProgressInfo(
            total_tasks=len(tasks),
            completed_tasks=completed,
            failed_tasks=failed,
            running_tasks=running,
            pending_tasks=len(tasks) - completed - failed - running,
            current_phase=self._detect_phase(tasks),
            elapsed_seconds=elapsed,
            estimated_remaining_seconds=remaining
        )

    @staticmethod
    def _detect_phase(tasks: list[Task]) -> str:
        running = [t for t in tasks if t.status == TaskStatus.RUNNING]
        if not running:
            return "等待中"
        types = {t.task_type for t in running}
        phase_names = {
            TaskType.PARSE: "小说解析",
            TaskType.CHARACTER_ANALYSIS: "角色分析",
            TaskType.VOICE_DESIGN: "音色设计",
            TaskType.SCREENWRITE: "剧本生成",
            TaskType.TTS_SYNTHESIZE: "TTS 合成",
            TaskType.AUDIO_MERGE: "音频合并",
            TaskType.POST_PROCESS: "后处理",
            TaskType.BOOK_ASSEMBLE: "全书组装",
        }
        return " + ".join(phase_names.get(t, str(t)) for t in types)

    @staticmethod
    def _format_time(seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.0f}m{seconds%60:.0f}s"
        else:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            return f"{h}h{m}m"
```

---

## 8. 断点续传管理器

### 8.1 状态持久化

```python
import json
from pathlib import Path
from dataclasses import asdict

class CheckpointManager:
    """断点续传管理器"""

    def __init__(self, checkpoint_dir: Path):
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _checkpoint_path(self, novel_slug: str) -> Path:
        return self.checkpoint_dir / f"{novel_slug}_checkpoint.json"

    def save(self, plan: ProcessingPlan):
        data = {
            "novel_slug": plan.novel_slug,
            "total_chapters": plan.total_chapters,
            "created_at": plan.created_at.isoformat(),
            "saved_at": datetime.now().isoformat(),
            "tasks": [self._serialize_task(t) for t in plan.tasks]
        }
        path = self._checkpoint_path(plan.novel_slug)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def load(self, novel_slug: str) -> Optional[ProcessingPlan]:
        path = self._checkpoint_path(novel_slug)
        if not path.exists():
            return None

        data = json.loads(path.read_text())
        plan = ProcessingPlan(
            novel_slug=data["novel_slug"],
            total_chapters=data["total_chapters"]
        )
        for task_data in data["tasks"]:
            task = self._deserialize_task(task_data)
            plan.tasks.append(task)
        return plan

    def resume(self, plan: ProcessingPlan) -> ProcessingPlan:
        """恢复处理计划：已完成的任务标记为 SKIPPED，未完成的重新入队"""
        for task in plan.tasks:
            if task.status == TaskStatus.SUCCESS:
                task.status = TaskStatus.SKIPPED
            elif task.status in (TaskStatus.RUNNING, TaskStatus.RETRYING, TaskStatus.QUEUED):
                task.status = TaskStatus.PENDING
                task.started_at = None
                task.completed_at = None
                task.error_message = None
        return plan

    def has_checkpoint(self, novel_slug: str) -> bool:
        return self._checkpoint_path(novel_slug).exists()

    def delete_checkpoint(self, novel_slug: str):
        path = self._checkpoint_path(novel_slug)
        path.unlink(missing_ok=True)

    @staticmethod
    def _serialize_task(task: Task) -> dict:
        return {
            "task_id": task.task_id,
            "task_type": task.task_type.value,
            "status": task.status.value,
            "params": task.params,
            "depends_on": task.depends_on,
            "retry_count": task.retry_count,
            "error_message": task.error_message,
        }

    @staticmethod
    def _deserialize_task(data: dict) -> Task:
        return Task(
            task_id=data["task_id"],
            task_type=TaskType(data["task_type"]),
            status=TaskStatus(data["status"]),
            params=data.get("params", {}),
            depends_on=data.get("depends_on", []),
            retry_count=data.get("retry_count", 0),
            error_message=data.get("error_message"),
        )
```

### 8.2 断点续传使用流程

```
启动时检查：
    ↓
有 checkpoint？
    ├── 是 → 提示用户"发现未完成的处理，是否继续？"
    │         ├── 继续 → resume(plan)，跳过已完成任务
    │         └── 重新开始 → delete_checkpoint() → 全新处理
    └── 否 → 全新处理

处理中定期保存：
    每完成 10 个任务 / 每 30 秒 → save(plan)

处理完成：
    delete_checkpoint() → 清理
```

---

## 9. 处理计划生成器

```python
class PlanGenerator:
    """根据解析结果生成全书处理计划"""

    @staticmethod
    def generate(novel_slug: str, chapters: list[Chapter]) -> ProcessingPlan:
        plan = ProcessingPlan(
            novel_slug=novel_slug,
            total_chapters=len(chapters)
        )

        # 全局任务
        parse_task = Task(task_id="parse", task_type=TaskType.PARSE)
        char_task = Task(
            task_id="char_analysis",
            task_type=TaskType.CHARACTER_ANALYSIS,
            depends_on=["parse"]
        )
        voice_task = Task(
            task_id="voice_design",
            task_type=TaskType.VOICE_DESIGN,
            depends_on=["char_analysis"]
        )
        plan.tasks.extend([parse_task, char_task, voice_task])

        # 逐章任务
        chapter_merge_ids = []
        for ch in chapters:
            ch_id = f"ch{ch.chapter_num:04d}"

            # 编剧任务
            sw_id = f"screenwrite_{ch_id}"
            sw_task = Task(
                task_id=sw_id,
                task_type=TaskType.SCREENWRITE,
                params={"chapter_num": ch.chapter_num},
                depends_on=["char_analysis"]
            )
            plan.tasks.append(sw_task)

            # TTS 合成任务（编剧完成后才知道具体数量，这里先创建占位）
            tts_id = f"tts_{ch_id}"
            tts_task = Task(
                task_id=tts_id,
                task_type=TaskType.TTS_SYNTHESIZE,
                params={"chapter_num": ch.chapter_num},
                depends_on=[sw_id, "voice_design"]
            )
            plan.tasks.append(tts_task)

            # 合并任务
            merge_id = f"merge_{ch_id}"
            merge_task = Task(
                task_id=merge_id,
                task_type=TaskType.AUDIO_MERGE,
                params={"chapter_num": ch.chapter_num},
                depends_on=[tts_id]
            )
            plan.tasks.append(merge_task)

            # 后处理
            pp_id = f"postprocess_{ch_id}"
            pp_task = Task(
                task_id=pp_id,
                task_type=TaskType.POST_PROCESS,
                params={"chapter_num": ch.chapter_num},
                depends_on=[merge_id]
            )
            plan.tasks.append(pp_task)
            chapter_merge_ids.append(pp_id)

        # 全书组装
        assemble_task = Task(
            task_id="book_assemble",
            task_type=TaskType.BOOK_ASSEMBLE,
            depends_on=chapter_merge_ids
        )
        plan.tasks.append(assemble_task)

        return plan
```

---

## 10. 并发配置建议

| 任务类型 | 建议并发数 | 瓶颈 |
|----------|-----------|------|
| 小说解析 | 1 | CPU（单文件） |
| 角色分析 | 1 | LLM（全局一次） |
| 音色设计 | 1 | TTS GPU（串行避免 OOM） |
| 编剧 Agent | 2-4 | LLM（可并行多章） |
| TTS 合成 | 2-4 | GPU 显存 |
| 音频合并 | 4-8 | CPU（轻量） |
| 后处理 | 4-8 | CPU（轻量） |

---

## 11. 关联文档

| 文档 | 关系 |
|------|------|
| [`novel-tts-design.md`](novel-tts-design.md) | 总纲 |
| [`module-novel-parser.md`](module-novel-parser.md) | PARSE 任务的执行者 |
| [`auto-character-voice-engine.md`](auto-character-voice-engine.md) | CHARACTER_ANALYSIS / VOICE_DESIGN 任务的执行者 |
| [`novel-audio-screenwriter-agent.md`](novel-audio-screenwriter-agent.md) | SCREENWRITE 任务的执行者 |
| [`module-tts-api-client.md`](module-tts-api-client.md) | TTS_SYNTHESIZE 任务的执行者 |
| [`module-audio-processor.md`](module-audio-processor.md) | AUDIO_MERGE / POST_PROCESS / BOOK_ASSEMBLE 任务的执行者 |
| [`module-web-ui.md`](module-web-ui.md) | 进度信息的展示层 |
