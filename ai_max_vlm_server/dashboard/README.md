# AI Max VLM Dashboard

Dockerized read-only monitoring for llama.cpp and the Server PC interaction
chain. It mounts `/home/user/ROS_Cui/vlm_server_logs` read-only and accepts
Server PC status through the relay endpoint.

The dashboard includes:

- an AI Input Inspector showing the exact frame and resolved text sent to VLM;
- side-by-side User Prompt, generated JSON, and latest llama log views;
- current chain latency and evaluation status; and
- host llama.cpp process monitoring.

Default URL: `http://192.168.64.246:18181/`.

Start directly:

```bash
LLAMA_PORT=18082 bash run_dashboard.sh
```

Server PC relay:

```bash
python3 server_status_relay.py
```

The role entrypoint `deploy/ai_max/start.sh` configures the dashboard together
with the selected VLM service.

`run_dashboard.sh` starts the container with the host PID namespace so the
process view reports the real llama.cpp service. The dashboard image installs
`procps`; rebuild the image after changing the Dockerfile rather than relying
on an older cached image that does not provide `ps`.
