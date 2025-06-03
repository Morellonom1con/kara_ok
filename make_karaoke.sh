slugify() {
  echo "$1" | \
    tr '[:upper:]' '[:lower:]' | \
    sed -E 's/[^a-z0-9]+/-/g' | \
    sed -E 's/^-+|-+$//g' | \
    sed -E 's/-+/-/g'
}

SONG_URL="$1"

if [ -z "$SONG_URL" ]; then
    echo "Usage: $0 <spotify-song-url>"
    exit 1
fi

# 🧠 Let SpotDL do its thing first
docker run --rm -v "$(pwd)":/music spotdl/spotify-downloader download "$SONG_URL"

# 🎯 Grab the newest .mp3 file (assumes it's the one SpotDL just made)
ORIG_MP3=$(find . -maxdepth 1 -type f -name "*.mp3" -printf "%T@ %p\n" | sort -n | tail -n 1 | cut -d' ' -f2-)
ORIG_MP3="${ORIG_MP3#./}"

# 🏷 Save original name for later steps (no slugify yet)
RAW_NAME="${ORIG_MP3%.mp3}"

# ✅ Only slugify for consistent processing after download
SONG_NAME=$(slugify "$RAW_NAME")
SONG_MP3="${SONG_NAME}.mp3"

# Rename the original mp3 to slugified version
mv "$ORIG_MP3" "$SONG_MP3"

# 🔀 Run Spleeter
docker run --rm \
  -v "$(pwd)":/audio \
  -v "$(pwd)/cache/model/2stems":/model/2stems \
  researchdeezer/spleeter separate \
  -i "/audio/${SONG_MP3}" \
  -p spleeter:2stems \
  -o /audio/output

# 📝 Grab lyrics and convert to .lrc
node lyrics_fetcher.js "$SONG_URL"
node json_to_lrc.js

# 🎥 Generate karaoke video
ffmpeg -f lavfi -i color=c=teal:s=1280x720:d=9999 \
       -i "output/${SONG_NAME}/accompaniment.wav" \
       -vf "subtitles='lyrics.lrc':force_style='Alignment=2,FontName=Arial,FontSize=36,PrimaryColour=&HFFFFFF&'" \
       -shortest "${SONG_NAME}_karaoke.mp4"