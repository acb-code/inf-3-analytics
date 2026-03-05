#!/usr/bin/env bash
# Convert a screen recording to an optimized GIF using ffmpeg two-pass palette.
#
# Usage:
#   bash demo/gif-convert.sh <input> [output]
#
# Environment overrides:
#   WIDTH=800      Output width in pixels (height scales automatically)
#   FRAMERATE=10   Output frames per second
#   START=0        Start time in seconds (trim)
#   DURATION=      Duration in seconds (omit to use full file)
#
# Examples:
#   bash demo/gif-convert.sh recording.mp4
#   WIDTH=720 FRAMERATE=8 bash demo/gif-convert.sh recording.mp4
#   START=5 DURATION=40 bash demo/gif-convert.sh recording.mp4

set -euo pipefail

INPUT="${1:?Usage: $0 <input.mp4> [output.gif]}"
OUTPUT="${2:-$(dirname "$0")/demo.gif}"
WIDTH="${WIDTH:-800}"
FRAMERATE="${FRAMERATE:-10}"
START="${START:-0}"

if ! command -v ffmpeg &>/dev/null; then
  echo "Error: ffmpeg not found. Install it with: brew install ffmpeg  (macOS) or  sudo apt install ffmpeg  (Linux)" >&2
  exit 1
fi

PALETTE_FILE="$(mktemp /tmp/palette_XXXXXX.png)"
trap 'rm -f "$PALETTE_FILE"' EXIT

# Build optional trim flags
TRIM_FLAGS=(-ss "$START")
if [[ -n "${DURATION:-}" ]]; then
  TRIM_FLAGS+=(-t "$DURATION")
fi

FILTER_SCALE="fps=${FRAMERATE},scale=${WIDTH}:-1:flags=lanczos"

echo "Pass 1/2: generating palette from ${INPUT} ..."
ffmpeg -y "${TRIM_FLAGS[@]}" -i "$INPUT" \
  -vf "${FILTER_SCALE},palettegen=max_colors=256:stats_mode=diff" \
  "$PALETTE_FILE" -loglevel warning

echo "Pass 2/2: rendering GIF to ${OUTPUT} ..."
ffmpeg -y "${TRIM_FLAGS[@]}" -i "$INPUT" -i "$PALETTE_FILE" \
  -lavfi "${FILTER_SCALE} [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" \
  "$OUTPUT" -loglevel warning

SIZE_MB=$(du -m "$OUTPUT" | cut -f1)
echo "Done: ${OUTPUT}  (${SIZE_MB} MB)"

if (( SIZE_MB > 10 )); then
  echo "Warning: file is ${SIZE_MB} MB — GitHub will not display GIFs larger than 10 MB inline."
  echo "Try: WIDTH=720 FRAMERATE=8 bash $0 ${INPUT}"
fi
