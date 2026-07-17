# AI Max VLM Dashboard

Dockerized read-only monitoring for llama.cpp and the Server PC interaction
chain. It mounts the manifest-selected VLM log directory read-only and accepts
Server PC status through the relay endpoint.

The dashboard includes:

- an AI Input Inspector showing the exact frame and resolved text sent to VLM;
- side-by-side User Prompt, generated JSON, and latest llama log views;
- current chain latency and evaluation status; and
- host llama.cpp process monitoring.

The role entrypoint `deploy/role.sh ai_max start --manifest PATH` supplies the
container name/image, public port, llama port, log root and Server status URL.
Direct startup intentionally fails unless all of those inputs are explicit.

`run_dashboard.sh` starts the container with the host PID namespace so the
process view reports the real llama.cpp service. The dashboard image installs
`procps`; rebuild the image after changing the Dockerfile rather than relying
on an older cached image that does not provide `ps`.
