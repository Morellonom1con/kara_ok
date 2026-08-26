## Kara_OK

A desktop karaoke player. Paste a Spotify track link and it fetches the
time-synced lyrics, downloads the track, strips the vocals with
[spleeter](https://github.com/deezer/spleeter), and plays the instrumental back
with scrolling lyrics over a reactive OpenGL visualizer.

Tracks queue up in a side panel, so you can keep adding songs while one plays.

### Requirements

- **Python 3.10** — spleeter 2.4.2 pins `tensorflow==2.10.1`, which does not
  build on 3.11+
- **Node.js >= 18**
- **ffmpeg** on your `PATH` (used for transcoding and by spleeter)
- A system audio loopback device (PulseAudio / PipeWire). The visualizer reads
  the speaker output, and startup fails without one.

### Setup

```bash
git clone https://github.com/Morellonom1con/kara_ok
cd kara_ok

# Python
python3.10 -m venv venv310
source venv310/bin/activate
pip install -r requirements.txt

# Node
npm install
npx playwright install chromium

# Config
cp .env.example .env
```

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
