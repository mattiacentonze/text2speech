# text2speech

A fast command-line utility for converting text to high-quality MP3 audio with **word-synchronized karaoke subtitles** (`.ass` and `.srt`), played natively in **mpv**.

It uses Microsoft Edge's text-to-speech engine via the open-source `edge-tts` library. Text is automatically segmented at sentence and paragraph boundaries, synthesized concurrently with adaptive worker scaling, joined seamlessly into PCM audio, and encoded to 192 kbit/s MP3 alongside centisecond-accurate karaoke timing files.

## Features

- **Parallel synthesis with auto-scaling:** Intelligent text segmentation with concurrency tailored to text size (6 workers for short text, 10 for medium text, 12 for long documents).
- **Synchronized word-level karaoke:** Generates Advanced SubStation Alpha (`.ass`) karaoke subtitles compatible with `mpv` to highlight words in real-time as they are spoken, plus standard `.srt` subtitle files.
- **Three input modes:**
  - Directly from the command line (`-d "Your text here"`)
  - From UTF-8 text files or standard input (`-i document.txt` or `-i -`)
  - Directly from the system clipboard (`-c`, supports Wayland `wl-paste` and X11 `xclip`)
- **Instant native playback:** Automatically launches `mpv` in a minimal window with live karaoke highlighting (can be bypassed with `-np`).

## Prerequisites

1. **Python 3.10+** and the `edge-tts` package:
   ```bash
   pip install edge-tts
   ```
2. **ffmpeg** installed on the system:
   ```bash
   sudo apt install ffmpeg
   ```
3. **mpv** for native playback with karaoke subtitles:
   ```bash
   sudo apt install mpv
   ```
4. (Optional) **wl-clipboard** or **xclip** to enable clipboard input via `-c`:
   ```bash
   sudo apt install wl-clipboard   # On Wayland / Ubuntu 22.04+
   # or: sudo apt install xclip    # On X11
   ```

## Installation

Clone the repository and symlink the script to your local `bin`:

```bash
git clone https://github.com/mattiacentonze/text2speech.git
cd text2speech
chmod +x text2speech.py
ln -s "$(pwd)/text2speech.py" ~/.local/bin/text2speech
```

## Usage

```bash
# Read quoted text directly
text2speech -d "Nel mezzo del cammin di nostra vita..."

# Read from a UTF-8 text file
text2speech -i notes.txt

# Read the current content of the system clipboard
text2speech -c

# Generate audio and subtitles without opening mpv
text2speech -i article.txt -np

# Specify a custom MP3 output path
text2speech -i report.txt -o ~/Music/report.mp3

# Override the number of parallel TTS workers (1 to 12)
text2speech -i book.txt --workers 12

# Customize voice or playback rate
text2speech -d "Fast speaking voice" --rate "+15%" --voice "en-US-EmmaMultilingualNeural"
```

### Options

| Option | Description |
|---|---|
| `-d TEXT`, `--text TEXT` | Text to synthesize (in quotes) |
| `-i INPUT`, `--input INPUT` | Input text file (UTF-8); use `-` for stdin |
| `-c`, `--clipboard` | Read text from system clipboard |
| `-o OUTPUT`, `--output OUTPUT` | Target MP3 output path (default: `~/Music/VoceKaraoke/reading-<date>-<id>.mp3`) |
| `-np`, `--no-play` | Generate MP3 and subtitle files without opening `mpv` |
| `--workers N` | Number of simultaneous TTS requests (1–12; default: auto based on text length) |
| `--voice VOICE` | Edge TTS voice identifier (default: `it-IT-IsabellaNeural`) |
| `--rate RATE` | Speech rate adjustment (default: `-5%`, e.g. `+10%`, `-10%`) |

## Output Files

For each run, the destination directory receives:
- `file.mp3`: 48 kHz mono MP3 audio at 192 kbit/s.
- `file.ass`: Advanced SubStation Alpha subtitles with word-by-word `{\k...}` karaoke timing.
- `file.srt`: Standard SubRip subtitles compatible with most media players.

To replay an existing output file with karaoke in `mpv`:
```bash
mpv --force-window=yes --audio-display=no --sub-auto=no --sub-file=reading.ass reading.mp3
```

## Privacy & Service Notice

This tool connects to the Microsoft Edge online speech synthesis endpoint to generate audio and word-level timing metadata. Do not use it with confidential, proprietary, or sensitive data. Designed for personal and educational use.

## License

Distributed under the [MIT](LICENSE) License.
