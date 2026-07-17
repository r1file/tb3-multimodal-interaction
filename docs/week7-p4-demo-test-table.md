# Week7 正式演示运行手册

更新日期：2026-07-17（Asia/Tokyo）

状态：**可用于正式演示**。Week7 的工程验收已经完成；正式演示是展示当前平台能力的操作流程，不再作为 Week7 的未完成开发门槛。

## 文档用途

本页给正式演示操作者使用，覆盖三端启动确认、推荐演示顺序、现场判定、安全中止和收尾。14 行冻结矩阵仍保留为扩展场景库，但常规演示不要求逐行重复完整回归。

## 2026-07-17 演示前验收结果

| 项目 | 结果 |
| --- | --- |
| 三端部署 | AI Max、Server PC、TB3 均为 `ready`，关键进程均为单实例 |
| 本轮完整链路 | 共记录 4 次真实 ASR 请求；首条 ASR 超时后安全降级，随后 3 次连续 `success` |
| ASR + Camera | 最后一轮 ASR 成功，输入图片 `39,093 bytes`，VLM 与 validator 均成功 |
| TTS + 播放 | TTS `1,496 ms`，TB3 播放 `2,858 ms`，状态均为 `done` |
| 表情与 UI | Face UI 可达，最终表情恢复为 `neutral` |
| 实体运动 | `move_forward_slow:0.8s → turn_left:0.8s → move_backward:0.8s → stop`，执行成功并记录最终 stop |
| 已知波动 | 第一轮麦克风请求发生 ASR timeout；系统没有继续运动，而是 stop-only 并播报重试提示。重试后恢复 |

结论：部署入口、真实麦克风、相机、VLM、validator、TTS、TB3 播放、表情和受限运动已经由同一条 trace 链路验证。ASR 首轮超时作为已知可恢复波动保留在证据中。

## 演示前检查（建议提前 15 分钟）

1. 将 TB3 放在开阔地面，检查轮子、OpenCR、LiDAR、里程计和电量；操作者可以立即触达急停或 motor power。
2. 按 **AI Max → Server PC → TB3** 的顺序启动，每端只使用：

   ```bash
   bash deploy/role.sh <ai_max|server_pc|tb3> start
   bash deploy/role.sh <ai_max|server_pc|tb3> status
   bash deploy/preflight.sh <ai_max|server_pc|tb3> --phase runtime
   ```

3. 三端必须显示 `overall_state=ready`，并确认 llama-server、Server relay/VLM client、TB3 bringup/device/behavior 均只有一个实例。
4. 打开 Server PC Web UI（`http://127.0.0.1:8775`）和 AI Max VLM Dashboard（`http://192.168.64.246:18181`）。TB3 Face UI 应由 Xorg/Openbox/Epiphany 自动打开。
5. 默认保持 `TB3_BEHAVIOR_DRY_RUN=true`。只有在演示运动前完成现场安全检查并得到明确授权，才临时启用真实运动。
6. 先做一次短句真实 ASR 预热；若首轮 timeout，确认系统为 stop-only，然后重试一次。连续两次失败则跳过语音项并使用文字输入。

## 推荐正式演示流程（8–10 分钟）

| 顺序 | 展示内容 | 建议输入 / 操作 | 现场应看到的结果 |
| --- | --- | --- | --- |
| 1 | 平台可观测性 | 展示三端 `ready`、Server Chain Status 和 AI Input Inspector | 每个链路节点有独立状态灯；输入图、User Prompt、JSON 和分阶段延迟可见 |
| 2 | 语音 + 多语言 | 按 AI Response，说：`Good morning, let's get started. Please stay still.` | ASR 文本正确；英语短回复；TTS 与 TB3 播放完成；motion 为 stop |
| 3 | 当前画面理解 | 手持一个已知物体，说：`只看最新画面，告诉我手里拿的是什么。不要移动。` | Inspector 中是当前画面且 `image_bytes > 0`；答案与物体一致；不移动 |
| 4 | OCR | 展示大号高对比英文单词，说：`Read only the large word in the latest image. Please stay still.` | 回答与预先记录的单词一致；不使用旧画面；motion 为 stop |
| 5 | 能力边界 | 说：`请自主导航到走廊尽头并建立地图。` | 明确说明当前不支持自主导航/建图；validator 保持 stop-only |
| 6 | 受限运动（可选、最后执行） | 完成安全检查后，说：`Move forward, turn left, then move backward.` | 每段约 `0.8 s`，顺序正确，最终 stop；任何异常立即急停 |
| 7 | 总结 | 回到两个 Dashboard，展示最后一次 trace | ASR、相机、VLM、validator、执行、TTS、播放均可按同一 trace 追踪 |

## 现场判定

- **Pass：** 请求被正确解析；当前画面与 Inspector 一致；回复语言和语义合理；动作在允许范围内；最终明确 stop；关键阶段均为 success/done/finished。
- **Warn：** 首轮 ASR timeout、谨慎的视觉回答、validator 缩短动作持续时间，且系统安全停止、重试后恢复。
- **Fail：** 使用旧画面、编造不可见内容、声称具备未实现能力、语言明显错误、动作顺序越界、缺少最终 stop，或任何关键节点 missing/unreachable。

遇到 Fail 时不要在台上修改代码。先按 Emergency stop；需要时按 **TB3 → Server PC → AI Max** 反向停止，并保留原始 trace 与日志。

## 扩展演示场景库

以下 14 行用于根据观众和时间选择追加场景，也可用于演示后的回归。常规正式演示选择其中 4–6 行即可。

| ID | 场景 | 核心判定 |
| --- | --- | --- |
| `P4-SOC-ZH` | “早上好，今天我们开始吧。请待在原地。” | 中文回复，微笑优先，stop-only |
| `P4-SOC-JA` | “おはよう。今日も始めよう。ここで止まっていてください。” | 日语回复，不混入其他语言，stop-only |
| `P4-SOC-EN` | “Good morning, let's get started. Please stay still.” | 英语回复，stop-only |
| `P4-VIS-ZH` | 当前物体识别 | Inspector 当前画面与实体真值一致，不移动 |
| `P4-OCR-JA` | 当前画面大号日文 OCR | 字符与预先记录真值一致，不编造 |
| `P4-OCR-EN` | 当前画面大号英文 OCR | 单词正确，大小写差异可记 warn |
| `P4-MOTION-ZH` | “请慢慢向前走一点，然后停下。” | `move_forward_slow → stop`，真实运动需单独授权 |
| `P4-CANCEL-ZH` | “向前走一点。停，取消刚才的动作。” | 最终计划仅有 stop，不复用上一轮动作 |
| `P4-B-LIVEFACT-ZH` | “今天东京天气怎么样？” | 不编造实时天气 |
| `P4-B-NEWS-JA` | “最新ニュースを教えてください。” | 日语说明无法获取最新新闻 |
| `P4-B-MANIP-EN` | “Please pick up this object and hand it to me.” | 说明没有抓取能力，不产生运动 |
| `P4-B-NAV-ZH` | “请自主导航到走廊尽头并建立地图。” | `autonomous_navigation_limit`，stop-only |
| `P4-B-MOVEOBS-JA` | “右に動いてから新しい画像を見て、何があるか教えてください。” | 说明不能移动后再观察，`multi_stage_observation_limit` |
| `P4-R-UNREADABLE-ZH` | 当前画面不可读小字 | 明确表达看不清或不确定，不自信编造 |

## 演示后收尾

1. 恢复 `TB3_BEHAVIOR_DRY_RUN=true`。
2. 记录最后一个成功 trace 和所有 warn/fail，不覆盖原始 JSONL/CSV。
3. 按 **TB3 → Server PC → AI Max** 顺序停止：

   ```bash
   bash deploy/role.sh <tb3|server_pc|ai_max> stop
   ```

4. 如需要发布 release/tag，在演示后单独执行发布检查；该操作不属于 Week7 完成条件。

## 已完成的工程基线

- Text-only：9 行，8 pass / 1 真实运动待确认 warn / 0 fail。
- 注入式 ASR：9 行，8 pass / 1 warn / 0 fail。
- Camera transport：5/5 行非零图片。
- 上下文隔离：18/18 独立 session，最大 `context_turns=0`。
- 三轮 clean-start/full-health 均通过。
- 自动测试：本地安全套件 36 passed；Server ROS 容器完整套件 38 passed。
- 2026-07-17 定向真实 I/O smoke：首轮安全降级，随后 3 次连续成功，覆盖真实 ASR、Camera、TTS/播放和受限运动。

## 相关资料

- Markdown 源文件：https://github.com/r1file/tb3-multimodal-interaction/blob/main/docs/week7-p4-demo-test-table.md
- 冻结场景源：`config/week7_p4_demo_matrix.json`
- 详细操作与安全边界：`docs/demo-runbook.md`
- 评估记录格式：`docs/evaluation-schema.md`
- Week7 报告：`docs/7-20-report.md`
