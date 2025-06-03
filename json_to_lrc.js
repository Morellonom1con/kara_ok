const fs = require('fs');
const path = require('path');

const inputPath = './lyrics.json';
const outputPath = './lyrics.lrc';

function msToTimestamp(ms) {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  const centiseconds = Math.floor((ms % 1000) / 10);
  return `[${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}.${String(centiseconds).padStart(2, '0')}]`;
}

function jsonToLRC(json) {
  if (!json || !json.lyrics || !json.lyrics.lines) {
    throw new Error("Invalid JSON format: No lyrics found.");
  }

  const lines = json.lyrics.lines;
  return lines
    .filter(line => line.words.trim() !== '')
    .map(line => {
      const timestamp = msToTimestamp(parseInt(line.startTimeMs));
      return `${timestamp}${line.words}`;
    })
    .join('\n');
}

try {
  const jsonData = JSON.parse(fs.readFileSync(inputPath, 'utf-8'));
  const lrcData = jsonToLRC(jsonData);
  fs.writeFileSync(outputPath, lrcData, 'utf-8');
  console.log(`LRC file saved as: ${outputPath}`);
} catch (err) {
  console.error('Error converting to LRC:', err.message);
}
