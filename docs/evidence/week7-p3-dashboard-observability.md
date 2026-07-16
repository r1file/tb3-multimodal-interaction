# Week 7 P3.5 Dashboard Observability

Date: 2026-07-16

## Implemented

- Server PC `CHAIN STATUS` replaces the former AI-chain and ROS-node panels.
  It shows the direct data path as a flow graph, gives every node an independent
  health light, highlights the currently active stage, exposes health/stage/
  latency details on hover, and places non-chain ROS nodes outside the graph
  using the same visual object.
- `SPEECH PIPELINE` again shows the full ASR status and transcript instead of a
  truncated payload.
- The completed-turn latency chart covers Request, recording, ASR inference,
  camera, VLM, validation, execution, TTS, and playback.
- AI Max `AI INPUT INSPECTOR` shows the exact submitted image and resolved text.
  User Prompt, generated JSON, and latest llama log are displayed together.
- llama.cpp process monitoring now runs with `procps` and the host PID namespace.

## Live validation

- Trace `server_ui_1784196175929`: 48,386-byte image, 904-character User Prompt,
  accepted 257-character generated JSON, VLM 4,642 ms, execution 132 ms, total
  4,844 ms.
- Trace `server_ui_1784196347588`: text plus camera dry-run completed with VLM
  2,734 ms, camera 150 ms, execution 135 ms, total 3,046 ms.
- A manual five-second ASR request activated and highlighted the ASR flow node;
  the completed status retained the full JSON and reported 358 ms adapter
  latency.
- Server discovery reported 18 ROS nodes with no expected nodes missing.
- AI Max process inspection reported exactly one real host llama-server process.
- Both dashboards were inspected at 1920 x 1080 with no horizontal overflow;
  the Server PC critical view fits within 900 px and the AI Max dashboard within
  1,071 px.

## Automated checks

- Dashboard observability contract tests: 4 passed.
- Evaluation schema tests: 6 passed.
- Complete Server ROS-container test suite after P3.5: 29 passed.
- Both standalone dashboard scripts passed `node --check`; modified Python
  modules passed byte-compilation; `git diff --check` passed.

## ASR latency semantics correction

The original `asr_ms` was an end-to-end ASR wait measured from publishing the
ASR request until text returned. It therefore included the configured recording
window and was not a model-inference-only value. The Server PC chain view now
splits this path into Request, Record, and ASR inference while retaining the
end-to-end value in the node tooltip.

Live dry-run trace `server_ui_1784197718733` measured 2 ms from the UI request
to ASR publication, a 5,000 ms recording window, 395 ms ASR inference, and
5,408 ms ASR end-to-end. The 1920 x 1080 view showed all nine latency bars with
no horizontal overflow and a 900 px page height.
