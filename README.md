# text2speech

Utility da riga di comando per generare audio MP3 di alta qualità con sintesi vocale italiana e **karaoke sincronizzato parola per parola** (`.ass` e `.srt`), riproducibile nativamente con **mpv**.

Il testo viene inviato all'endpoint vocale di Microsoft Edge tramite la libreria open source `edge-tts`. I segmenti vengono sintetizzati in parallelo con adattamento automatico dei worker, combinati in PCM e codificati in MP3 a 192 kbit/s. Contestualmente viene calcolata e generata la traccia karaoke con timing al centesimo di secondo.

## Funzionalità

- **Sintesi rapida in parallelo:** segmentazione intelligente su frasi e paragrafi con worker paralleli automatici (6 per testi brevi, 10 intermedi, 12 per testi lunghi).
- **Karaoke sincronizzato:** genera file `.ass` compatibile con `mpv` per evidenziare le parole a tempo durante l'ascolto, più file `.srt` standard.
- **Tre modalità di input:**
  - Da riga di comando (`-d "testo"`)
  - Da file UTF-8 o stdin (`-i documento.txt` o `-i -`)
  - Direttamente dagli appunti di sistema (`-c`, supporta Wayland `wl-paste` e X11 `xclip`)
- **Riproduzione nativa immediata:** apre automaticamente `mpv` con finestra dedicata e testo karaoke attivo (disattivabile con `-np`).

## Prerequisiti

1. **Python 3.10+** con il pacchetto `edge-tts`:
   ```bash
   pip install edge-tts
   ```
2. **ffmpeg** installato nel sistema (`sudo apt install ffmpeg`).
3. **mpv** per la riproduzione nativa con karaoke (`sudo apt install mpv`).
4. (Opzionale) **wl-clipboard** o **xclip** per l'uso dell'opzione `-c` dagli appunti:
   ```bash
   sudo apt install wl-clipboard   # su Wayland / Ubuntu recente
   # oppure: sudo apt install xclip # su X11
   ```

## Installazione

Clona il repository e rendi eseguibile lo script o collegalo nel tuo `PATH`:

```bash
git clone https://github.com/mattiacentonze/text2speech.git
cd text2speech
chmod +x text2speech.py
ln -s "$(pwd)/text2speech.py" ~/.local/bin/text2speech
```

## Utilizzo

```bash
# Legge il testo passato tra virgolette
text2speech -d "Nel mezzo del cammin di nostra vita..."

# Legge da un file di testo UTF-8
text2speech -i appunti.txt

# Legge il testo attualmente copiato negli appunti
text2speech -c

# Genera solo i file MP3, ASS e SRT senza aprire il lettore
text2speech -i articolo.txt -np

# Specifica il percorso del file MP3 di destinazione
text2speech -i report.txt -o ~/Music/report.mp3

# Forza il numero di richieste TTS parallele (da 1 a 12)
text2speech -i libro.txt --workers 12

# Modifica velocità o voce
text2speech -d "Testo veloce" --rate "+15%" --voice "it-IT-DiegoNeural"
```

### Opzioni complete

| Opzione | Descrizione |
|---|---|
| `-d TEXT`, `--text TEXT` | Testo da sintetizzare |
| `-i INPUT`, `--input INPUT` | File di input UTF-8 (usa `-` per stdin) |
| `-c`, `--clipboard` | Legge il testo presente negli appunti |
| `-o OUTPUT`, `--output OUTPUT` | Percorso dell'MP3 di output (default: `~/Music/VoceKaraoke/lettura-<data>-<id>.mp3`) |
| `-np`, `--no-play` | Genera l'audio e i sottotitoli senza avviare `mpv` |
| `--workers N` | Numero di worker simultanei (1-12; default automatico in base alla lunghezza) |
| `--voice VOICE` | Voce sintetica Edge (default: `it-IT-IsabellaNeural`) |
| `--rate RATE` | Velocità della voce (default: `-5%`, es. `+10%`, `-10%`) |

## File generati

Per ogni esecuzione vengono salvati nella cartella di destinazione:
- `file.mp3`: traccia audio mono 48 kHz a 192 kbit/s.
- `file.ass`: sottotitoli Advanced SubStation Alpha con timing karaoke `{\k...}` parola per parola.
- `file.srt`: sottotitoli SubRip standard compatibili con la maggior parte dei lettori multimediali.

Per riprodurre in qualsiasi momento un file già generato con karaoke in `mpv`:
```bash
mpv --force-window=yes --audio-display=no --sub-auto=no --sub-file=lettura.ass lettura.mp3
```

## Note e privacy

Questo strumento invia il testo all'endpoint di sintesi vocale online di Microsoft Edge per generare la traccia audio e i metadati temporali. Non utilizzarlo per trattare dati confidenziali o soggetti a vincoli di segretezza. Progetto destinato a uso personale e di studio.

## Licenza

Distribuito sotto licenza [MIT](LICENSE).
