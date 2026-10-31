"""Engine adapters. Each one exposes sample_rate, events (castscript event name -> engine tag), and synthesize(text, voice, emotion)."""


def torch_device() -> str:
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"
