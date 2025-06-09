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

docker run --rm -v "$(pwd)":/music spotdl/spotify-downloader download "$SONG_URL"


ORIG_MP3=$(find . -maxdepth 1 -type f -name "*.mp3" -printf "%T@ %p\n" | sort -n | tail -n 1 | cut -d' ' -f2-)
ORIG_MP3="${ORIG_MP3#./}"

RAW_NAME="${ORIG_MP3%.mp3}"

SONG_NAME=$(slugify "$RAW_NAME")
SONG_MP3="${SONG_NAME}.mp3"

mv "$ORIG_MP3" "$SONG_MP3"

docker run --rm \
  -u $(id -u):$(id -g) \
  -v "$(pwd)":/audio \
  -v "$(pwd)/cache/model/2stems":/model/2stems \
  researchdeezer/spleeter separate \
  -i "/audio/${SONG_MP3}" \
  -p spleeter:2stems \
  -o /audio/current_queue

node lyrics_fetcher.js "$SONG_URL"
node json_to_lrc.js