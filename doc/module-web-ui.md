# 模块：Web UI

> 隶属系统：小说 TTS 配音系统
> 运行端：Mac 客户端（前端 + 后端）
> 职责：提供图形化操作界面，管理全流程
> 关联文档：[`novel-tts-design.md`](novel-tts-design.md)（总纲）

---

## 1. 模块职责

| 职责 | 说明 |
|------|------|
| 小说上传与管理 | 上传 TXT/EPUB/PDF 文件，查看解析状态 |
| 角色管理 | 查看/编辑自动识别的角色画像、别名、关系 |
| 音色试听与调整 | 试听自动生成的音色，手动替换不满意的音色 |
| 剧本预览与编辑 | 查看编剧 Agent 生成的结构化剧本，修改情绪/语气词 |
| 任务监控 | 实时查看处理进度、任务状态、失败详情 |
| 音频预览 | 逐章/逐句试听合成音频 |
| 导出管理 | 导出章节音频或全书有声书 |

---

## 2. 技术栈

| 层 | 技术 | 说明 |
|-----|------|------|
| 后端 | Python + FastAPI | 与现有 Python 代码栈统一 |
| 前端 | Vue 3 + TypeScript + Element Plus | 参考 easyVoice 的成熟方案 |
| 通信 | REST API + WebSocket | REST 用于 CRUD，WebSocket 用于进度推送 |
| 状态管理 | Pinia | Vue 3 推荐 |
| 打包 | Vite | 快速构建 |

---

## 3. 代码结构

> 后端路径：`src/xspy/web/`；前端路径：`frontend/`（完整项目结构见 [`novel-tts-design.md`](novel-tts-design.md) §4）

**后端（FastAPI）：**

```
src/xspy/web/
├── __init__.py
├── app.py                  # FastAPI 主入口（创建 app、挂载路由）
├── deps.py                 # 依赖注入（数据库/服务实例）
├── routes/                 # REST API 路由
│   ├── __init__.py
│   ├── novels.py           #   小说管理 API
│   ├── characters.py       #   角色管理 API
│   ├── voices.py           #   音色管理 API
│   ├── scripts.py          #   剧本预览/编辑 API
│   ├── tasks.py            #   任务监控 API
│   └── audio.py            #   音频播放/导出 API
└── ws/                     # WebSocket
    ├── __init__.py
    └── progress.py         #   实时进度推送
```

**前端（Vue 3）：**

```
frontend/
├── package.json
├── vite.config.ts
└── src/
    ├── App.vue
    ├── main.ts
    ├── views/                      # 页面组件
    │   ├── NovelList.vue           #   小说列表页
    │   ├── NovelDetail.vue         #   小说详情页（含章节）
    │   ├── CharacterPanel.vue      #   角色管理面板
    │   ├── VoiceBank.vue           #   音色库管理
    │   ├── ScriptEditor.vue        #   剧本编辑器
    │   ├── TaskMonitor.vue         #   任务监控仪表盘
    │   └── AudioPlayer.vue         #   音频播放器
    ├── components/                 # 通用组件
    │   ├── CharacterCard.vue       #   角色卡片
    │   ├── EmotionBadge.vue        #   情绪标签
    │   ├── WaveformPlayer.vue      #   波形播放器
    │   ├── ProgressBar.vue         #   进度条
    │   └── RelationGraph.vue       #   角色关系图谱（D3.js）
    ├── stores/                     # Pinia 状态管理
    │   ├── novel.ts
    │   ├── character.ts
    │   └── task.ts
    └── api/
        └── client.ts              # Axios API 调用封装
```

**导入方式：**

```python
# 后端
from xspy.web.app import create_app
from xspy.web.routes import novels, characters, voices
```

---

## 4. 页面设计

### 4.1 小说列表页

```
┌─────────────────────────────────────────────────┐
│  📚 小说 TTS 配音工作台                          │
├─────────────────────────────────────────────────┤
│  [+ 上传小说]  [搜索...]                         │
│                                                  │
│  ┌─────────────────────────────────────┐        │
│  │ 📖 斗破苍穹                          │        │
│  │ 状态: ✅ 已完成  章节: 1523          │        │
│  │ 角色: 45  音频: 12.3GB              │        │
│  │ [查看详情] [继续处理] [导出]          │        │
│  └─────────────────────────────────────┘        │
│                                                  │
│  ┌─────────────────────────────────────┐        │
│  │ 📖 无声书店                          │        │
│  │ 状态: 🔄 处理中 (63%)               │        │
│  │ 当前: TTS 合成 - 第 32/50 章         │        │
│  │ [████████████████░░░░░░░░] 63%      │        │
│  │ [查看详情] [暂停] [取消]             │        │
│  └─────────────────────────────────────┘        │
└─────────────────────────────────────────────────┘
```

### 4.2 角色管理面板

```
┌────────────────────────────────────────────────────────────┐
│  👥 角色管理 — 无声书店                                      │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────┐  林晚 (晚晚、阿晚、林姑娘)      [主角]           │
│  │ 👩   │  性别: 女  年龄: 23  职业: 书店店员               │
│  │      │  性格: 温柔、内敛、坚韧                           │
│  │      │  音色: "23岁年轻女性，声音轻柔清澈..."            │
│  └──────┘  [▶ 试听音色] [✏ 编辑画像] [🔄 重新生成音色]     │
│                                                            │
│  ┌──────┐  赵明 (赵队、老赵)              [主角]           │
│  │ 👨   │  性别: 男  年龄: 28  职业: 刑警                  │
│  │      │  性格: 正直、刚毅、偶尔温柔                       │
│  │      │  音色: "28岁青年男性，嗓音低沉有力..."            │
│  └──────┘  [▶ 试听音色] [✏ 编辑画像] [🔄 重新生成音色]     │
│                                                            │
│  ───── 关系图谱 ─────                                      │
│  [可视化关系图：节点=角色，边=关系类型]                       │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 4.3 剧本编辑器

```
┌────────────────────────────────────────────────────────────────┐
│  📝 剧本编辑 — 无声书店 · 第五章 重逢                           │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  场景 1: 书店门口，黄昏  [情绪基调: nostalgic, 紧张度: 0.4]    │
│  ─────────────────────────────────────────────────             │
│                                                                │
│  #1 [旁白] calm                                                │
│  "黄昏的光斜斜地照在书店的玻璃门上，林晚正准备翻转              │
│   '营业中'的牌子。"                                             │
│  [▶ 播放] [✏ 编辑文本] [🎭 修改情绪]                           │
│                                                                │
│  #2 [林晚] surprise 💨(gasp)                                   │
│  "赵……赵明？"                                                  │
│  TTS指令: "用惊讶且带点紧张的语气说，第一个字有轻微结巴"        │
│  [▶ 播放] [✏ 编辑文本] [🎭 修改情绪] [🔊 编辑语气词]           │
│                                                                │
│  #3 [赵明] happy 😊(chuckle)                                   │
│  "好久不见，林晚。"                                             │
│  TTS指令: "用温暖而克制的笑意说，语调轻柔"                      │
│  [▶ 播放] [✏ 编辑文本] [🎭 修改情绪] [🔊 编辑语气词]           │
│                                                                │
│  ⚠ 一致性警告: 无                                              │
│                                                                │
│  [保存修改] [重新生成本章剧本] [合成本章音频]                    │
└────────────────────────────────────────────────────────────────┘
```

### 4.4 任务监控仪表盘

```
┌───────────────────────────────────────────────────────────────┐
│  📊 任务监控 — 无声书店                                        │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  总进度: [█████████████████████░░░░░░░░░░] 63%                │
│  已完成: 315/500 任务 | 失败: 2 | 运行中: 4 | 等待: 179       │
│  耗时: 2h 15m | 预计剩余: 1h 20m                              │
│                                                               │
│  ── 各阶段状态 ──                                              │
│  ✅ 小说解析      1/1                                         │
│  ✅ 角色分析      1/1                                         │
│  ✅ 音色设计      15/15                                       │
│  🔄 剧本生成     32/50 章 [████████████████░░░░░░] 64%        │
│  🔄 TTS 合成     258/420 句 [████████████░░░░░░░░] 61%       │
│  ⏳ 音频合并      8/50 章                                     │
│  ⏳ 后处理        0/50 章                                     │
│  ⏳ 全书组装      0/1                                         │
│                                                               │
│  ── 失败任务 ──                                                │
│  ❌ tts_ch0012_utt045: 服务端超时 (已重试 3 次)                │
│     [重试] [跳过] [查看详情]                                   │
│  ❌ tts_ch0023_utt102: GPU OOM                                │
│     [重试] [跳过] [查看详情]                                   │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

## 5. API 设计

### 5.1 小说管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/novels/upload` | 上传小说文件 |
| GET | `/api/novels` | 获取小说列表 |
| GET | `/api/novels/{slug}` | 获取小说详情 |
| POST | `/api/novels/{slug}/process` | 开始处理 |
| POST | `/api/novels/{slug}/pause` | 暂停处理 |
| POST | `/api/novels/{slug}/resume` | 恢复处理 |
| DELETE | `/api/novels/{slug}` | 删除小说及所有数据 |

### 5.2 角色管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/novels/{slug}/characters` | 获取角色列表 |
| GET | `/api/novels/{slug}/characters/{id}` | 获取角色详情（含画像） |
| PUT | `/api/novels/{slug}/characters/{id}` | 修改角色画像 |
| GET | `/api/novels/{slug}/relationships` | 获取关系图谱 |

### 5.3 音色管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/novels/{slug}/voices` | 获取音色列表 |
| GET | `/api/novels/{slug}/voices/{speaker}/preview` | 试听音色 |
| POST | `/api/novels/{slug}/voices/{speaker}/regenerate` | 重新生成音色 |
| POST | `/api/novels/{slug}/voices/{speaker}/upload` | 手动上传参考音频 |

### 5.4 剧本管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/novels/{slug}/chapters/{num}/script` | 获取章节剧本 |
| PUT | `/api/novels/{slug}/chapters/{num}/script` | 修改剧本 |
| POST | `/api/novels/{slug}/chapters/{num}/regenerate` | 重新生成剧本 |

### 5.5 任务监控

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/novels/{slug}/tasks` | 获取任务列表 |
| GET | `/api/novels/{slug}/tasks/summary` | 获取进度摘要 |
| POST | `/api/novels/{slug}/tasks/{id}/retry` | 重试失败任务 |
| WS | `/ws/novels/{slug}/progress` | 实时进度推送 |

### 5.6 音频播放

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/novels/{slug}/chapters/{num}/audio` | 获取章节音频 |
| GET | `/api/novels/{slug}/chapters/{num}/utterances/{seq}/audio` | 获取单句音频 |
| GET | `/api/novels/{slug}/audiobook` | 下载完整有声书 |

---

## 6. WebSocket 进度推送

```python
from fastapi import WebSocket
import json

class ProgressWebSocket:

    async def handler(self, websocket: WebSocket, novel_slug: str):
        await websocket.accept()

        try:
            while True:
                progress = self._get_progress(novel_slug)
                await websocket.send_json({
                    "type": "progress_update",
                    "data": {
                        "total_tasks": progress.total_tasks,
                        "completed_tasks": progress.completed_tasks,
                        "failed_tasks": progress.failed_tasks,
                        "running_tasks": progress.running_tasks,
                        "percent": progress.percent,
                        "current_phase": progress.current_phase,
                        "elapsed_seconds": progress.elapsed_seconds,
                        "estimated_remaining": progress.estimated_remaining_seconds,
                    }
                })
                await asyncio.sleep(1)
        except Exception:
            pass
```

---

## 7. 依赖清单

### 后端

```
fastapi>=0.100
uvicorn>=0.23
websockets>=11.0
python-multipart>=0.0.6  # 文件上传
```

### 前端

```json
{
  "dependencies": {
    "vue": "^3.4",
    "element-plus": "^2.5",
    "pinia": "^2.1",
    "vue-router": "^4.2",
    "axios": "^1.6",
    "wavesurfer.js": "^7.0",
    "d3": "^7.8"
  }
}
```

---

## 8. 关联文档

| 文档 | 关系 |
|------|------|
| [`novel-tts-design.md`](novel-tts-design.md) | 总纲 |
| [`module-task-manager.md`](module-task-manager.md) | 进度数据来源 |
| [`module-voice-bank.md`](module-voice-bank.md) | 音色试听/管理 |
| [`auto-character-voice-engine.md`](auto-character-voice-engine.md) | 角色画像数据来源 |
| [`novel-audio-screenwriter-agent.md`](novel-audio-screenwriter-agent.md) | 剧本数据来源 |
