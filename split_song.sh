#!/bin/bash

SONG_MP3="$1"

docker run --rm \
  -u $(id -u):$(id -g) \
  -v "$(pwd)":/audio \
  -v "$(pwd)/cache/model/2stems":/model/2stems \
  researchdeezer/spleeter separate \
  -i "/audio/${SONG_MP3}" \
  -p spleeter:2stems \
  -o /audio/current_queue

