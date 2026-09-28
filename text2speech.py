#!/usr/bin/env python3
"""text2speech: Italian TTS -> MP3 with word-level ASS karaoke, played in native mpv."""
import argparse
import asyncio
from datetime import datetime
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

import edge_tts

VOICE = 'it-IT-IsabellaNeural'
RATE = '-5%'
MAX_CHARS = 100_000


def auto_workers(characters):
    """Practical defaults from the measured 1k/5k/10k/50k/100k benchmarks."""
    if characters <= 1_000:
        return 6
    if characters >= 40_000:
        return 12
    return 10


def split_text(text, limit=1100):
    """Keep paragraphs and sentence boundaries; split exceptionally long sentences."""
    pieces = []
    for paragraph in re.split(r'\n\s*\n', text.strip()):
        sentences = re.split(r'(?<=[.!?])\s+(?=[^\s])', paragraph.strip())
        current = ''
        for sentence in sentences:
            if len(sentence) > limit:
                if current:
                    pieces.append(current)
                    current = ''
                words = sentence.split()
                for word in words:
                    if len(word) > limit:
                        raise ValueError('Una parola supera il limite di 1100 caratteri')
                    if len(current) + len(word) + bool(current) > limit:
                        pieces.append(current)
                        current = ''
                    current = (current + ' ' + word).strip()
                if current:
                    pieces.append(current)
                    current = ''
            elif len(current) + len(sentence) + bool(current) > limit:
                pieces.append(current)
                current = sentence
            else:
                current = (current + ' ' + sentence).strip()
        if current:
            pieces.append(current)
    return pieces


async def speak(text, index, scratch, voice, rate):
    dest = scratch / f'{index:04}.mp3'
    for attempt in range(3):
        try:
            boundaries = []
            with dest.open('wb') as audio:
                stream = edge_tts.Communicate(text, voice=voice, rate=rate, boundary='WordBoundary')
                async for part in stream.stream():
                    if part['type'] == 'audio':
                        audio.write(part['data'])
                    elif part['type'] == 'WordBoundary':
                        boundaries.append((part['offset'] / 1e7,
                                           (part['offset'] + part['duration']) / 1e7,
                                           part['text']))
            if dest.stat().st_size < 1000 or not boundaries:
                raise RuntimeError('Risposta audio o tempi delle parole mancanti')
            return dest, boundaries
        except Exception:
            dest.unlink(missing_ok=True)
            if attempt == 2:
                raise
            await asyncio.sleep(2 ** attempt * 2)


def ass_time(seconds):
    centis = round(seconds * 100)
    h, centis = divmod(centis, 360000)
    m, centis = divmod(centis, 6000)
    s, centis = divmod(centis, 100)
    return f'{h}:{m:02}:{s:02}.{centis:02}'


def srt_time(seconds):
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


def subtitles(words, destination):
    header = '''[Script Info]
Title: Karaoke italiano
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 1280
PlayResY: 720

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,DejaVu Sans,44,&H0000D7FF,&H00C5C5C5,&H0013161A,&H7F000000,-1,0,0,0,100,100,0,0,1,3,1,2,45,45,125,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    lines = [header]
    captions = []
    for start_index in range(0, len(words), 12):
        group = words[start_index:start_index+12]
        start = group[0][0]
        next_group = words[start_index+12][0] if start_index+12 < len(words) else group[-1][1] + .7
        end = max(next_group, group[-1][1] + .05)
        syllables = []
        for i, (begin, _, text) in enumerate(group):
            following = group[i+1][0] if i+1 < len(group) else end
            duration = max(1, round((following - begin) * 100))
            safe = text.replace('\\', '\\\\').replace('{', r'\{').replace('}', r'\}').replace('\n', ' ')
            syllables.append(r'{\k' + str(duration) + '}' + safe + (' ' if i+1 < len(group) else ''))
        lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Karaoke,,0,0,0,,{''.join(syllables)}\n")
        captions.append(f"{len(captions)+1}\n{srt_time(start)} --> {srt_time(end)}\n" +
                        ' '.join(w[2] for w in group) + '\n\n')
    destination.with_suffix('.ass').write_text(''.join(lines), encoding='utf-8')
    destination.with_suffix('.srt').write_text(''.join(captions), encoding='utf-8')


def read_input(args):
    if args.text is not None:
        text = args.text
    elif args.input == '-':
        text = sys.stdin.read(MAX_CHARS + 1)
    elif args.input is not None:
        text = Path(args.input).expanduser().read_text(encoding='utf-8')
    else:
        tool = shutil.which('wl-paste') or shutil.which('xclip')
        if not tool:
            raise RuntimeError('Installa wl-paste o xclip per leggere gli appunti')
        cmd = [tool, '--no-newline', '--type', 'text/plain'] if Path(tool).name == 'wl-paste' else [tool, '-selection', 'clipboard', '-o']
        text = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    if not text.strip() or len(text) > MAX_CHARS:
        raise ValueError('Il testo deve contenere da 1 a 100.000 caratteri')
    return text


async def generate(text, destination, voice=VOICE, rate=RATE, workers=None):
    if workers is None:
        workers = auto_workers(len(text))
    if not 1 <= workers <= 12:
        raise ValueError('workers deve essere compreso tra 1 e 12')
    chunks = split_text(text)
    began = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='text2speech-karaoke-') as temp:
        scratch = Path(temp)
        raw = scratch / 'joined.s16le'
        words = []
        frames = 0
        semaphore = asyncio.Semaphore(workers)

        async def synthesize(i, chunk):
            async with semaphore:
                return await speak(chunk, i, scratch, voice, rate)

        tasks = [asyncio.create_task(synthesize(i, chunk)) for i, chunk in enumerate(chunks, 1)]
        try:
            with raw.open('wb') as joined:
                for i, task in enumerate(tasks, 1):
                    segment, marks = await task
                    result = await asyncio.to_thread(
                        subprocess.run, ['ffmpeg', '-v', 'error', '-i', str(segment), '-f', 's16le',
                                         '-ac', '1', '-ar', '24000', '-'], check=True, capture_output=True)
                    pcm = result.stdout
                    if not pcm or len(pcm) % 2:
                        raise RuntimeError(f'Segmento audio {i} non valido')
                    offset = frames / 24000
                    length = len(pcm) / 48000
                    words.extend((round(offset + begin, 3), round(min(offset + end, offset + length), 3), token)
                                 for begin, end, token in marks)
                    joined.write(pcm)
                    frames += len(pcm) // 2
                    print(f'\rSegmenti: {i}/{len(chunks)}', end='', flush=True)
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        print()
        encoded = scratch / 'output.mp3'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 's16le', '-ar', '24000', '-ac', '1',
                        '-i', str(raw), '-c:a', 'libmp3lame', '-b:a', '192k', '-ar', '48000',
                        str(encoded)], check=True)
        destination.parent.mkdir(parents=True, exist_ok=True)
        encoded.replace(destination)
        subtitles(words, destination)
    return frames / 24000, time.monotonic() - began


def main():
    parser = argparse.ArgumentParser(
        description='Crea un MP3 in italiano con karaoke parola per parola e lo apre in mpv.'
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('-d', '--text', help='Testo fra virgolette')
    source.add_argument('-i', '--input', help='File UTF-8 (.txt); usa - per leggere da stdin')
    source.add_argument('-c', '--clipboard', action='store_true', help='Testo dagli appunti (clipboard)')
    parser.add_argument('-o', '--output', type=Path, help='Percorso MP3 (default: ~/Music/VoceKaraoke/)')
    parser.add_argument('-np', '--no-play', action='store_true', help='Genera i file senza aprire mpv')
    parser.add_argument('--workers', type=int, choices=range(1, 13),
                        metavar='N', help='Richieste TTS simultanee (1-12; default automatico in base alla lunghezza)')
    parser.add_argument('--voice', default=VOICE, help='Voce edge-tts (default: it-IT-IsabellaNeural)')
    parser.add_argument('--rate', default=RATE, help='Regolazione velocità edge-tts (default: -5%%)')
    args = parser.parse_args()
    try:
        if not re.fullmatch(r'[+-]\d{1,2}%', args.rate):
            raise ValueError('Velocità: usa ad esempio -5% o +10%')
        text = read_input(args)
        output = (args.output.expanduser().resolve() if args.output else
                  Path.home() / 'Music' / 'VoceKaraoke' /
                  f'lettura-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}.mp3')
        if output.suffix.lower() != '.mp3':
            raise ValueError('Il percorso di output deve terminare in .mp3')
        if output.exists() or output.with_suffix('.ass').exists() or output.with_suffix('.srt').exists():
            raise ValueError(f'Output già esistente: {output}')
        if not shutil.which('ffmpeg'):
            raise RuntimeError('ffmpeg non è installato nel PATH')
        if not args.no_play and not shutil.which('mpv'):
            raise RuntimeError('mpv non è installato nel PATH')
        workers = args.workers if args.workers is not None else auto_workers(len(text))
        print(f'Worker TTS: {workers} ({"manuale" if args.workers is not None else "automatico"})', flush=True)
        duration, elapsed = asyncio.run(generate(text, output, args.voice, args.rate, workers))
        print(f'MP3: {output}\nKaraoke: {output.with_suffix(".ass")}')
        print(f'Durata audio: {duration:.1f} s | Generazione: {elapsed:.1f} s | Velocità: {duration/elapsed:.1f}×')
        if not args.no_play:
            subprocess.Popen(['mpv', '--force-window=yes', '--audio-display=no', '--sub-auto=no',
                              '--sub-visibility=yes', f'--sub-file={output.with_suffix(".ass")}', str(output)],
                             stdin=subprocess.DEVNULL, start_new_session=True)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'Errore: {exc}\n')


if __name__ == '__main__':
    main()
