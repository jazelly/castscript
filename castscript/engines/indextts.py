"""IndexTTS-2.5 from an index-tts checkout (https://github.com/index-tts/index-tts)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import torch

from ..script import Voice

SEED = 42
EMO_ALPHA = 0.6  # upstream recommends 0.6 or lower for text-derived emotion


class IndexTTSEngine:
    events = {}

    def __init__(self, index_dir: Path, language: str):
        sys.path.insert(0, str(index_dir))
        checkpoints = index_dir / "checkpoints"
        # IndexTTS sets HF_HUB_CACHE to "./checkpoints/hf_cache" on import; load from the checkout so it lands there.
        cwd = os.getcwd()
        os.chdir(index_dir)
        try:
            from indextts.infer_v2_5 import IndexTTS2

            self.model = IndexTTS2(cfg_path=str(checkpoints / "config.yaml"), model_dir=str(checkpoints), use_qwen_emo=True)
        finally:
            os.chdir(cwd)
        self.sample_rate = self.model.cfg.s2mel.preprocess_params.sr
        self.language = language.upper()

    def synthesize(self, text: str, voice: Voice, emotion: str | None) -> np.ndarray:
        if voice.kind != "ref":
            raise ValueError(f"IndexTTS only clones ref voices; voice '{voice.name}' uses {voice.kind}")
        torch.manual_seed(SEED)
        emo = {"use_emo_text": True, "emo_text": emotion, "emo_alpha": EMO_ALPHA} if emotion else {}
        sr, wav = self.model.infer(spk_audio_prompt=voice.value, text=text, output_path=None, lang=self.language, **emo)
        if sr != self.sample_rate:
            raise ValueError(f"unexpected IndexTTS sample rate {sr}")
        return (np.asarray(wav, dtype=np.float32).reshape(-1) / 32768.0).astype(np.float32)
