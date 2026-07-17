# AI Max VLM server

These are thin wrappers around an external llama.cpp build and Qwen3-VL
GGUF/mmproj assets. They do not install or modify those dependencies.

Normal operation uses the repository role entrypoint, which validates and
exports the release manifest before invoking these wrappers:

```bash
bash deploy/role.sh ai_max start --manifest PATH
bash deploy/role.sh ai_max status --manifest PATH
```

The direct wrappers intentionally require explicit model, path, port and GPU
environment variables; they contain no host/model fallback path. Use them only
for component diagnosis after loading the same manifest.
