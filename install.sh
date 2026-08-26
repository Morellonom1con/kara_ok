#!/usr/bin/env bash
# Sets up the Python and Node environments for kara_ok.
# Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v python3.10 >/dev/null 2>&1; then
  echo "error: python3.10 not found." >&2
  echo "spleeter pins tensorflow, which has no wheels for 3.11+. Install Python 3.10." >&2
  exit 1
fi

for cmd in ffmpeg node npm; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "error: $cmd not found on PATH." >&2; exit 1; }
done

[ -d venv310 ] || python3.10 -m venv venv310
venv310/bin/python -m pip install --upgrade pip

venv310/bin/pip install -r requirements.txt
# spleeter's declared pins (httpx<0.20, tensorflow==2.12.1) conflict with
# SpotiFLAC and with the tensorflow version this project works on. See the
# comments in requirements.txt.
venv310/bin/pip install --no-deps spleeter==2.4.2

npm install
npx playwright install chromium

[ -f .env ] || cp .env.example .env

echo
echo "Done. Next:"
echo "  node save_session.js      # log in to Spotify once"
echo "  source venv310/bin/activate && python3 kara_ok.py"
