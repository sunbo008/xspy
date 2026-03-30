# index-tts-vllm 部署方案（Windows PC + Mac OpenClaw 调用）

## 1. 目标与架构

| 项目 | 说明 |
|------|------|
| **服务侧** | Windows 11 台式机：NVIDIA RTX 3070 Ti（8GB 显存）、32GB 内存 |
| **客户端** | Mac 上 OpenClaw 通过局域网 HTTP 调用 API |
| **项目** | [index-tts-vllm](https://github.com/Ksuriuri/index-tts-vllm)（Index-TTS + vLLM 加速 GPT 推理） |
| **对外能力** | FastAPI：`api_server.py`（v1 / v1.5）、`api_server_v2.py`（IndexTTS-2）；README 另含 OpenAI 风格 `/audio/speech` 等 |

```
[Mac OpenClaw] --HTTP--> [Windows 局域网 IP:端口] --index-tts-vllm API--> [RTX 3070 Ti]
```

---

## 2. 可行性结论（8GB 显存）

- **可以部署并提供 Web/API 服务**；显存是主要约束。
- **建议优先 Index-TTS 1.0 或 1.5**，`gpu_memory_utilization` 从偏低开始试（例如 `0.2`～`0.35`），再按 OOM 情况微调。
- **IndexTTS-2** 子模块更多、更重，8GB 上可能吃紧或需更低占用/关闭其它占 GPU 程序，需实测。
- **Windows 上跑 vLLM**：优先 **WSL2（Ubuntu）+ CUDA** 或项目 **Docker**，成功率通常高于原生 Windows Python（以当时 vLLM 官方说明为准）。

---

## 3. 推荐路径：WSL2 + CUDA（主方案）

### 3.1 前置条件

1. Windows 11 已安装 **WSL2**，发行版建议 **Ubuntu 22.04 LTS**。
2. 安装 **NVIDIA 显卡驱动**（Windows 侧，支持 WSL 的版本）。
3. WSL 内安装与 vLLM / PyTorch 匹配的 **CUDA Toolkit** 组合（版本以 [vLLM 安装文档](https://docs.vllm.ai) 与当前 `requirements.txt` 为准）。
4. 确保 `nvidia-smi` 在 **WSL 终端**内可看到 GPU。

### 3.2 获取代码与 Python 环境

```bash
# 在 WSL 内执行
git clone https://github.com/Ksuriuri/index-tts-vllm.git
cd index-tts-vllm

# README 推荐 Python 3.12
conda create -n index-tts-vllm python=3.12 -y
conda activate index-tts-vllm

pip install uv
uv pip install -r requirements.txt -c overrides.txt
```

### 3.3 模型权重

将对应版本权重放到 `checkpoints/`（与 README 一致）：

- **国内**：ModelScope `modelscope download ...`（见仓库 README）。
- **IndexTTS-2**：也可 `huggingface-cli download ksuriuri/IndexTTS-2-vLLM ...`。

路径示例（按你实际下载目录填写）：

- `./checkpoints/Index-TTS-vLLM`
- `./checkpoints/Index-TTS-1.5-vLLM`
- `./checkpoints/IndexTTS-2-vLLM`

### 3.4 启动 API（供局域网访问）

**必须**监听 `0.0.0.0`，否则只有 WSL/本机可访问，Mac 连不上。

**Index-TTS 1.0 / 1.5：**

```bash
conda activate index-tts-vllm
cd /path/to/index-tts-vllm

python api_server.py \
  --model_dir ./checkpoints/Index-TTS-vLLM \
  --host 0.0.0.0 \
  --port 6006 \
  --gpu_memory_utilization 0.25
```

1.5 版本将 `model_dir` 换为 `Index-TTS-1.5-vLLM` 路径即可（若仓库另有 `--version` 等参数，以 `api_server.py --help` 为准）。

**IndexTTS-2：**

```bash
python api_server_v2.py \
  --model_dir ./checkpoints/IndexTTS-2-vLLM \
  --host 0.0.0.0 \
  --port 6006 \
  --gpu_memory_utilization 0.25
```

若 **CUDA OOM**：逐步降低 `--gpu_memory_utilization`（如 `0.2`），或先换 v1 / v1.5 权重再测。

### 3.5 WSL2 网络说明（Mac 访问 Windows 上的服务）

- 服务监听 `0.0.0.0:6006` 后，在 **Windows 主机**上查看局域网 IP（如 `192.168.x.x`）。
- 新版 WSL 常可通过 **Windows IP + 端口转发** 访问；若 Mac 无法连通，可在仓库或微软文档中查阅 **WSL2 端口转发 / `localhostForwarding`**，必要时用 **Windows 防火墙入站规则** 放行 **TCP 6006**，或配置 `netsh interface portproxy` 将 Windows 端口转发到 WSL 内服务端口。

**Mac 上 Base URL 示例：** `http://192.168.x.x:6006`（具体 path 以 `api_example.py` / `api_example_v2.py` 与 README 为准）。

---

## 4. 备选：Docker（若仓库 Dockerfile 与当前驱动匹配）

适合希望环境可复现、少折腾 WSL 内 CUDA 的情况：

1. 安装 **Docker Desktop for Windows**（启用 WSL2 后端）。
2. 分配足够 GPU 给容器（Docker Desktop GPU 支持按官方文档开启）。
3. 按仓库内 `Dockerfile` / `docker-compose.yaml` 与 README 挂载 `checkpoints`、映射端口（如 `6006:6006`），并确保 **绑定 `0.0.0.0`**。

镜像构建失败或 CUDA 版本不匹配时，回到 **3. WSL2 直装**。

---

## 5. Windows 防火墙与安全

1. **入站规则**：允许 **TCP 6006**（或你实际端口）来自 **专用/域网络**；公网勿裸奔。
2. **仅内网**：路由器不设端口映射时，一般只有同局域网设备可访问。
3. **生产或跨网段**：建议 **反向代理（HTTPS）+ 鉴权**；index-tts-vllm 默认 API 若无令牌，勿直接暴露公网。

---

## 6. Mac OpenClaw 侧配置要点

1. **URL**：`http://<Windows局域网IP>:6006`，路径与请求体格式对齐仓库中的 **API 示例**（v1/v1.5 用 `api_example.py`，v2 用 `api_example_v2.py`）。
2. **OpenAI 兼容**：若使用 `/audio/speech` 等，在 OpenClaw 中按 OpenAI 客户端习惯填写 base URL（是否需 `/v1` 前缀以实际路由为准，以 README 为准）。
3. **连通性测试**：Mac 终端执行 `curl http://192.168.x.x:6006/docs`（若启用 FastAPI Swagger）或按示例发一条最小请求。

---

## 7. 验证清单

- [ ] WSL（或容器）内 `nvidia-smi` 正常  
- [ ] `uv pip install ...` 无致命冲突  
- [ ] 权重目录与 `--model_dir` 一致  
- [ ] 服务以 `--host 0.0.0.0` 启动且无启动即 OOM  
- [ ] Windows 防火墙放行端口  
- [ ] Mac 能访问 `http://<IP>:<端口>` 或示例 API  

---

## 8. 常见问题（简要）

| 现象 | 可能原因 | 处理方向 |
|------|----------|----------|
| CUDA out of memory | 8GB 显存不足 | 降低 `gpu_memory_utilization`；换 v1/v1.5；关其它 GPU 程序 |
| Mac 连接超时 | 仅监听 127.0.0.1 / 防火墙 / WSL 未转发 | `--host 0.0.0.0`；检查防火墙与 WSL 端口转发 |
| vLLM 在 Windows 原生失败 | 官方以 Linux/CUDA 为主 | 改用 WSL2 或 Docker |
| 依赖冲突 | protobuf 等 | 按 README 使用 `uv pip install -r requirements.txt -c overrides.txt` |

---

## 9. 参考链接

- 项目仓库：<https://github.com/Ksuriuri/index-tts-vllm>  
- vLLM 文档：<https://docs.vllm.ai>  
- WSL + CUDA：<https://docs.nvidia.com/cuda/wsl-user-guide/index.html>  

---

*文档根据当前公开 README 与常见部署习惯整理；具体参数以仓库最新说明与 `python api_server.py --help` 为准。*
