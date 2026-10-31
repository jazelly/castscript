"""VoxCPM2 via the voxcpm package (https://github.com/OpenBMB/VoxCPM)."""

from __future__ import annotations

import numpy as np
import torch

from ..script import Voice

MODEL = "openbmb/VoxCPM2"
SEED = 42


class VoxCPMEngine:
    events = {}

    def __init__(self):
        from voxcpm import VoxCPM

        # device=None picks CUDA, MPS, or CPU.
        self.model = VoxCPM.from_pretrained(MODEL, load_denoiser=False)
        self.sample_rate = self.model.tts_model.sample_rate

    def synthesize(self, text: str, voice: Voice, emotion: str | None) -> np.ndarray:
        # VoxCPM reads voice descriptions and style directions from a leading "(...)".
        kwargs = {"cfg_value": 2.0, "inference_timesteps": 10}
        torch.manual_seed(SEED)
        if voice.kind == "ref" and emotion:
            # Controllable cloning: keeps the timbre and follows the direction.
            wav = self.model.generate(text=f"({emotion}){text}", reference_wav_path=voice.value, **kwargs)
        elif voice.kind == "ref":
            # Ultimate cloning continues from the reference and its transcript.
            wav = self.model.generate(
                text=text, prompt_wav_path=voice.value, prompt_text=voice.ref_text, reference_wav_path=voice.value, **kwargs
            )
        elif voice.kind == "design":
            wav = self.model.generate(text=f"({voice.value}{'，' + emotion if emotion else ''}){text}", **kwargs)
        else:
            raise ValueError(f"VoxCPM has no preset voices; voice '{voice.name}' uses preset")
        return np.asarray(wav, dtype=np.float32)
