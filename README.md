## Kara_OK

A desktop karaoke player. Paste a Spotify track link and it fetches the
time-synced lyrics, downloads the track, strips the vocals with
[spleeter](https://github.com/deezer/spleeter), and plays the instrumental back
with scrolling lyrics over a reactive OpenGL visualizer.

Tracks queue up in a side panel, so you can keep adding songs while one plays.

### Requirements

- **Python 3.10** — this project pins `tensorflow==2.10.1`, which has no
  wheels for 3.11+
- **Node.js >= 18**
- **ffmpeg** on your `PATH` (used for transcoding and by spleeter)
- A system audio loopback device (PulseAudio / PipeWire). The visualizer reads
  the speaker output, and startup fails without one.

### Setup

```bash
git clone https://github.com/Morellonom1con/kara_ok
cd kara_ok
./install.sh
```

`install.sh` creates the venv, installs the Python and Node dependencies,
downloads the Playwright browser, and seeds `.env`. It is safe to re-run.

To do it by hand instead:

```bash
python3.10 -m venv venv310
source venv310/bin/activate
pip install -r requirements.txt
pip install --no-deps spleeter==2.4.2   # see note below

npm install
npx playwright install chromium
cp .env.example .env
```

**Why the extra spleeter line:** spleeter 2.4.2 declares `httpx<0.20.0` and
`tensorflow==2.12.1`. SpotiFLAC requires `httpx>=0.27.0`, so those two cannot
be resolved together, and this project runs on tensorflow 2.10.1. Since
kara_ok only invokes spleeter as a subprocess (`python -m spleeter separate`),
installing it with `--no-deps` against the versions pinned in
`requirements.txt` works. `pip check` will report the mismatch; that is
expected.

The first run downloads the spleeter 2stems model (~75 MB) into
`pretrained_models/`.

### Log in to Spotify (once)

Lyrics are read from the Spotify web player, so it needs a browser session.
This opens a window for you to log in and saves the cookies to
`spotify-session.json`:

```bash
node save_session.js
```

`spotify-session.json` holds live account credentials and is gitignored —
**never commit it.**

### Run

```bash
source venv310/bin/activate
python3 kara_ok.py
```

Paste a Spotify **track** link into the field in the side panel and press `+`.
Right-click a queue entry to remove it.

Lyric size and audio/lyric sync offset are under the Options menu.

### Notes

- The track must have time-synced lyrics on Spotify, or it will be rejected.
- Downloaded audio and separated stems live in `current_queue/` and are
  gitignored.
