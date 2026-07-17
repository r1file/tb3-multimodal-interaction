#!/usr/bin/env bash
set -euo pipefail

DEVICE="${TB3_MIC_ALSA_DEVICE:?TB3_MIC_ALSA_DEVICE is required from the host manifest}"
DURATION="${1:-5}"
OUT="${2:-/tmp/tb3_usb_mic_test.wav}"

if ! command -v arecord >/dev/null 2>&1; then
  echo "Error: arecord is not installed on the TurtleBot3 host." >&2
  echo "Install it with: sudo apt install alsa-utils" >&2
  exit 1
fi

echo "Capture devices:"
arecord -l || true
echo
echo "Recording ${DURATION}s from ${DEVICE} to ${OUT}"
arecord -D "$DEVICE" -f S16_LE -c 1 -r 48000 -d "$DURATION" "$OUT"

python3 - "$OUT" <<'PY'
import json
import math
import os
import wave

path = os.sys.argv[1]
with wave.open(path, 'rb') as w:
    raw = w.readframes(w.getnframes())
    width = w.getsampwidth()
    if width != 2:
        raise SystemExit(f'Unsupported sample width: {width}')
    samples = memoryview(raw).cast('h')
    if not samples:
        rms = peak = 0
    else:
        total = sum(int(s) * int(s) for s in samples)
        rms = int(math.sqrt(total / len(samples)))
        peak = max(abs(int(s)) for s in samples)
    maxamp = 32768.0
    rms_db = 20 * math.log10(rms / maxamp) if rms else None
    peak_db = 20 * math.log10(peak / maxamp) if peak else None
    print(json.dumps({
        'file': path,
        'channels': w.getnchannels(),
        'rate': w.getframerate(),
        'duration_sec': round(w.getnframes() / w.getframerate(), 3),
        'rms': rms,
        'rms_dbfs': round(rms_db, 1) if rms_db is not None else '-inf',
        'peak': peak,
        'peak_dbfs': round(peak_db, 1) if peak_db is not None else '-inf',
        'size': os.path.getsize(path),
    }, indent=2))
PY
