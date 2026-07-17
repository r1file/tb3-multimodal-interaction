#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 scripts/audit_repository.py
python3 deploy/host_manifest.py validate \
  --manifest config/host-manifest.example.toml --allow-template
git diff --check

while IFS= read -r -d '' script; do
  bash -n "$script"
done < <(find ai_max_vlm_server deploy scripts -type f -name '*.sh' -print0)

python3 -m compileall -q \
  ai_max_vlm_server deploy launch scripts tb3_multimodal_interaction tools

tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/tb3-repo-validate.XXXXXX")"
trap 'rm -rf "$tmp_dir"' EXIT
python3 - "$tmp_dir" <<'PY'
from pathlib import Path
import sys

root = Path.cwd()
target = Path(sys.argv[1])
for source, name in (
    (root / "tb3_multimodal_interaction/web/server_control.html", "server_control.js"),
    (root / "ai_max_vlm_server/dashboard/index.html", "ai_dashboard.js"),
):
    text = source.read_text(encoding="utf-8")
    start = text.index("<script>") + len("<script>")
    end = text.index("</script>", start)
    (target / name).write_text(text[start:end], encoding="utf-8")
PY

node --check "$tmp_dir/server_control.js"
node --check "$tmp_dir/ai_dashboard.js"

tests=(
  test/test_behavior_plan_contract.py
  test/test_dashboard_observability_contract.py
  test/test_demo_matrix.py
  test/test_evaluation_schema.py
  test/test_host_manifest.py
  test/test_role_status_contract.py
  test/test_tb3_browser_single_instance_contract.py
)
if python3 -c 'import rclpy' >/dev/null 2>&1; then
  tests+=(test/test_vlm_context_policy.py)
fi
python3 -m pytest -q "${tests[@]}"

echo "REPOSITORY_VALIDATION_PASS"
