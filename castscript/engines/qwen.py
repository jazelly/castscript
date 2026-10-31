"""Qwen3-TTS via the official qwen-tts package (https://github.com/QwenLM/Qwen3-TTS)."""

from __future__ import annotations

import sys

import numpy as np
import torch

from ..script import Voice
from . import torch_device

MODELS = {
    "ref": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    "preset": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "design": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
}
LANGUAGES = {
    "zh": "Chinese", "en": "English", "ja": "Japanese", "ko": "Korean", "de": "German",
    "fr": "French", "ru": "Russian", "pt": "Portuguese", "es": "Spanish", "it": "Italian",
}
SEED = 42


class QwenEngine:
    events = {}
    sample_rate = 24000

    def __init__(self, language: str):
        from qwen_tts import Qwen3TTSModel

        if language not in LANGUAGES:
            raise ValueError(f"Qwen3-TTS supports languages {sorted(LANGUAGES)}, not '{language}'")
        self._model_cls = Qwen3TTSModel
        self._device = torch_device()
        self.language = LANGUAGES[language]
        self._models = {}
        self._prompts = {}

    def _model(self, kind: str):
        # One model per voice kind; loaded on first use and kept for the run.
        if kind not in self._models:
            self._models[kind] = self._model_cls.from_pretrained(
                MODELS[kind], device_map=self._device, dtype=torch.bfloat16
            )
        return self._models[kind]

    def synthesize(self, text: str, voice: Voice, emotion: str | None) -> np.ndarray:
        model = self._model(voice.kind)
        torch.manual_seed(SEED)
        if voice.kind == "ref":
            if emotion:
                print(f"warning: Qwen cannot apply emotion to ref voice '{voice.name}'; ignoring '{emotion}'", file=sys.stderr)
            if voice.name not in self._prompts:
                self._prompts[voice.name] = model.create_voice_clone_prompt(ref_audio=voice.value, ref_text=voice.ref_text)
            wavs, sr = model.generate_voice_clone(text=text, language=self.language, voice_clone_prompt=self._prompts[voice.name])
        elif voice.kind == "preset":
            wavs, sr = model.generate_custom_voice(text=text, language=self.language, speaker=voice.value, instruct=emotion)
        else:
            instruct = f"{voice.value}{'这句话的语气：' + emotion if emotion else ''}"
            wavs, sr = model.generate_voice_design(text=text, language=self.language, instruct=instruct)
        if sr != self.sample_rate:
            raise ValueError(f"unexpected Qwen sample rate {sr}")
        return np.asarray(wavs[0], dtype=np.float32)
