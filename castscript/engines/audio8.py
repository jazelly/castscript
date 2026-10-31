"""Audio8-TTS Realistic 0.6B via transformers remote code (https://github.com/Edge0-AI/Audio8_TTS)."""

from __future__ import annotations

import sys

import numpy as np
import torch

from ..script import Voice
from . import torch_device

MODEL = "Edge0/Audio8-TTS-Realistic-0.6b"
SEED = 42


class Audio8Engine:
    events = {}

    def __init__(self):
        from transformers import AutoModel, AutoProcessor

        self.device = torch_device()
        dtype = torch.bfloat16 if self.device == "cuda" else torch.float32
        self.processor = AutoProcessor.from_pretrained(MODEL, trust_remote_code=True)
        self.model = AutoModel.from_pretrained(MODEL, trust_remote_code=True, dtype=dtype).eval().to(self.device)
        self.sample_rate = int(self.model.config.codec_sample_rate)

    def synthesize(self, text: str, voice: Voice, emotion: str | None) -> np.ndarray:
        if voice.kind != "ref":
            raise ValueError(f"Audio8 only clones ref voices; voice '{voice.name}' uses {voice.kind}")
        if emotion:
            print(f"warning: Audio8 cannot apply emotion '{emotion}' to voice '{voice.name}'; ignoring", file=sys.stderr)
        inputs = self.processor(text=[text], reference_audio=[voice.value], reference_text=[voice.ref_text], return_tensors="pt")
        inputs = {name: value.to(self.device) for name, value in inputs.items()}
        output = self.model.generate(
            **inputs,
            max_new_tokens=2000,
            temperature=0.8,
            top_p=0.95,
            top_k=50,
            do_sample=True,
            generator=torch.Generator(device=self.device).manual_seed(SEED),
            return_dict_in_generate=True,
        )
        if not bool(output.finished[0]):
            raise RuntimeError(f"Audio8 did not finish speaking: {text}")
        waveforms, lengths = self.model.decode_audio(output.codes)
        return waveforms[0, : int(lengths[0])].float().cpu().numpy()
