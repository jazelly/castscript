"""Breeze TTS 2 on Apple Silicon via breeze-tts-mlx (https://github.com/rishikksh20/breeze-tts-mlx)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from ..script import Voice

SEED = 42
GUIDED_CFG = 4.0


class BreezeEngine:
    supports_events = True

    def __init__(self, checkpoint: Path, breeze_dir: Path):
        sys.path.insert(0, str(breeze_dir))
        from breeze_tts_mlx.runtime import BreezeMLXRuntime, MLXRuntimeConfig
        from breeze_tts_mlx.sampling import NumpySampler, SamplingConfig
        from breeze_tts_mlx.templates import get_template, prepare_inputs

        self._sampler_cls = NumpySampler
        self._get_template = get_template
        self._prepare_inputs = prepare_inputs
        sampling = SamplingConfig(temperature=0.9, top_k=50, top_p=1.0, do_sample=True)
        self.runtime = BreezeMLXRuntime(
            checkpoint,
            seed=SEED,
            config=MLXRuntimeConfig(
                max_new_tokens=1500,
                max_seq_len=2048,
                repetition_penalty=1.1,
                codec_chunk_frames=2,
                backbone_sampling=sampling,
                depth_sampling=sampling,
            ),
        )
        self.sample_rate = self.runtime.sample_rate
        self._count = 0

    def synthesize(self, text: str, voice: Voice, emotion: str | None) -> np.ndarray:
        request = {"text": text, "speaker": "S0"}
        if voice.kind == "ref":
            request["ref_audio_path"] = voice.value
            request["ref_text"] = voice.ref_text
            if emotion:
                request["instruction"] = emotion
            template, cfg = ("ref_edit_tata", GUIDED_CFG) if emotion else ("ref_clone_tata", 1.0)
        elif voice.kind == "design":
            request["instruction"] = f"{voice.value}{'这句话的语气：' + emotion if emotion else ''}"
            template, cfg = "tts_instruction", GUIDED_CFG
        else:
            raise ValueError(f"Breeze has no preset voices; voice '{voice.name}' uses preset")

        self._count += 1
        request["id"] = f"line-{self._count}"
        self.runtime.sampler = self._sampler_cls(SEED)
        inputs = self._prepare_inputs(
            self.runtime.tokenizer, self.runtime.audio_tokenizer, self.runtime, [request],
            self._get_template(template),
            guidance_scale=cfg, guidance_scale_ref=None, guidance_scale_ins=None,
        )
        chunks = [c.audio for c in self.runtime.iter_audio_chunks(inputs, request_id=request["id"])]
        return np.concatenate(chunks).astype(np.float32)
