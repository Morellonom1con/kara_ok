SONG_URL="$1"

if [ -z "$SONG_URL" ]; then
    echo "Usage: $0 <spotify-song-url>"
    exit 1
fi


docker run --rm -v "$(pwd)":/music spotdl/spotify-downloader download "$SONG_URL"


SONG_MP3=$(ls *.mp3 | head -n 1)
SONG_NAME="${SONG_MP3%.mp3}"


docker run --rm -v "$(pwd)":/audio researchdeezer/spleeter separate \
  -i "/audio/${SONG_MP3}" \
  -p spleeter:2stems \
  -o /audio/output

node lyrics_fetcher.js "$SONG_URL"
node json_to_lrc.js

TRACK_ID=$(python3 -c "from urllib.parse import urlparse; print(urlparse('$SONG_URL').path.split('/')[-1])")
python3 lyrics_fetcher.py "$TRACK_ID" "$SPOTIFY_TOKEN"
mv "$TRACK_ID.lrc" "${SONG_NAME}.lrc"


ffmpeg -i "output/${SONG_NAME}/accompaniment.wav" \
        -f lavfi -i color=c=black:s=1280x720 \
        -vf "subtitles='output.lrc':force_style='Alignment=2'"\
        -shortest "${SONG_NAME}_karaoke.mp4"
