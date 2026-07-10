# AI Max VLM Server

Thin wrappers around the existing AI Max llama.cpp build and Qwen3-VL GGUF
cache. The scripts do not install or modify llama.cpp.

Defaults:

- Model: `qwen3vl8b`
- Port: `18082`
- Context: `4096`
- GPU layers: `999`
- Logs: `/home/user/ROS_Cui/vlm_server_logs`

Start a clean service:

```bash
bash restart_qwen3vl_server.sh
```

Use the smaller model explicitly:

```bash
MODEL=qwen3vl2b PORT=18081 bash restart_qwen3vl_server.sh
```

Health check:

```bash
bash check_llama_server.sh 192.168.64.246 18082
```

For normal three-host startup, use `../deploy/ai_max/start.sh` from the
repository root.
