# AI Max VLM Dashboard

Dockerized read-only monitoring for llama.cpp and the Server PC interaction
chain. It mounts `/home/user/ROS_Cui/vlm_server_logs` read-only and accepts
Server PC status through the relay endpoint.

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
