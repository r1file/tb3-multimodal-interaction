# Current limitations and deferred research

This repository delivers the current synchronous, single-turn TurtleBot3
platform. It does not claim the future research architecture or general robot
capability.

## Current platform limitations

- No live internet facts: weather, news, and other current facts return a
  capability-boundary response.
- No manipulation: the Burger base cannot pick up, carry, or hand over objects.
- No autonomous navigation or mapping workflow is exposed through the VLM plan.
- No move-then-observe planning: the current request uses one captured frame and
  cannot move, acquire a new image, and answer within the same coordinated turn.
- Camera/OCR quality depends on lighting, framing, focus, and readable text size.
- ASR includes a configured recording window and may produce no-audio, timeout,
  or low-quality text; these outcomes remain in evaluation data.
- The VLM may still require deterministic validator/policy repair. A one-time
  format-only retry remains deferred until measured failures justify it.
- ROS discovery depends on the static Fast DDS peer profile and matching domain
  configuration. Address changes require a coordinated profile update.
- AI Max receives Server status through a push relay because routed connectivity
  is asymmetric; direct dashboard fetch is best-effort.
- Runtime hosts assume the ROBOTIS Jazzy Compose workspace/container contract.

## Explicitly deferred research

The following are outside the current semester release and must not be implied
by demos or documentation:

- low-risk immediate response while a model request is still running;
- asynchronous LLM/VLM pipeline execution;
- Continue/Adjust/Repair behavior coordination;
- SSAM-specific semantic time alignment or dynamic programming;
- autonomous multi-stage perception/action planning;
- participant studies or claims about user outcomes.

The P3 trace/timing schema is deliberately research-neutral so future work can
reuse it without pretending these mechanisms already exist.
