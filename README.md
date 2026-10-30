# castscript

A plain-text format for multi-voice audiobooks and radio plays, plus a renderer that turns it into MP3 and SRT with a local TTS engine.

```
@voice 旁白 = ref: voices/narrator.wav
@voice 林风 = ref: voices/hero.wav

旁白：那天夜里，雨下得很大。
林风（低声，疲惫）：掌柜的，还有空房吗？[叹气]
```

The format is engine-independent. See [SPEC.md](SPEC.md) for the full format and what each engine supports.

## Engines

| Engine | Status |
|---|---|
| Breeze TTS 2 (Apple Silicon, via [breeze-tts-mlx](https://github.com/rishikksh20/breeze-tts-mlx)) | supported |
| Qwen3-TTS 1.7B (official `qwen-tts` package, Chinese) | supported |

## Usage (Breeze on Apple Silicon)

castscript runs inside the engine's Python environment.

1. Set up [breeze-tts-mlx](https://github.com/rishikksh20/breeze-tts-mlx) and download its checkpoint. Also install `ffmpeg` (`brew install ffmpeg`).
2. Put reference voices next to your script. Each `voice.wav` needs a `voice.txt` that contains its exact transcript.
3. Render:

```bash
PYTHONPATH=. uv run --project ../breeze-tts-mlx python -m castscript examples/rain-night.cast.txt \
  --breeze-dir ../breeze-tts-mlx --breeze-checkpoint ../breeze-tts-mlx/chkpt-mlx-int8
```

This writes `examples/rain-night.wav`, `.mp3` (loudness-normalized), and `.srt` next to the script.

## Usage (Qwen3-TTS)

Run inside an environment with the `qwen-tts` package installed. Models download from Hugging Face on first use: Base for `ref`, CustomVoice for `preset`, and VoiceDesign for `design`.

```bash
PYTHONPATH=. python -m castscript examples/rain-night-qwen.cast.txt --engine qwen
```

## Licenses

castscript is MIT-licensed. TTS engines and model weights carry their own licenses. Breeze TTS 2 weights and their outputs are for research and non-commercial use only.
