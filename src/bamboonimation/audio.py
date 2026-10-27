"""Audio placement and lightweight offline speech-envelope helpers.

An RMS envelope is useful for stylized mouth opening, not phonetic lip sync.
No speech recognition, model weights, network services, or paid APIs are used.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import wave
import numpy as np


@dataclass(frozen=True)
class AudioClip:
    path: str | Path
    start: float = 0.0
    volume: float = 1.0
    offset: float = 0.0

    def __post_init__(self):
        for name in ("start", "volume", "offset"):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"AudioClip {name} must be finite and nonnegative")


class Envelope:
    """Random-access RMS envelope extracted from uncompressed PCM WAV.

    ``envelope.at(t)`` returns a normalized mouth opening in [0, 1].
    A fixed supplied ``peak`` can keep multiple utterances at consistent gain.
    """

    def __init__(self, values, step: float):
        self.values = np.asarray(values, dtype=np.float32)
        if step <= 0 or not math.isfinite(step):
            raise ValueError("step must be positive and finite")
        self.step = step

    def at(self, t: float) -> float:
        if not math.isfinite(t) or t < 0 or t >= len(self.values) * self.step:
            return 0.0
        return float(self.values[min(int(t / self.step), len(self.values) - 1)])

    __call__ = at

    @classmethod
    def from_wav(cls, path, *, step=1 / 24, threshold=0.025, peak=None):
        if step <= 0 or not math.isfinite(step):
            raise ValueError("step must be positive and finite")
        if not 0 <= threshold < 1:
            raise ValueError("threshold must be in [0, 1)")
        with wave.open(str(path), "rb") as wav:
            width, channels, rate = wav.getsampwidth(), wav.getnchannels(), wav.getframerate()
            raw = wav.readframes(wav.getnframes())
        if width == 1:
            samples = (np.frombuffer(raw, np.uint8).astype(np.float32) - 128) / 128
        elif width == 2:
            samples = np.frombuffer(raw, "<i2").astype(np.float32) / 32768
        elif width == 3:
            triples = np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(np.int32)
            integers = triples[:, 0] | (triples[:, 1] << 8) | (triples[:, 2] << 16)
            integers = (integers ^ 0x800000) - 0x800000
            samples = integers.astype(np.float32) / 8388608
        elif width == 4:
            samples = np.frombuffer(raw, "<i4").astype(np.float32) / 2147483648
        else:
            raise ValueError("Only 8/16/24/32-bit PCM WAV is supported")
        # Average channel energy, avoiding cancellation of opposite-phase channels.
        samples = samples.reshape(-1, channels)
        chunk = max(1, round(rate * step))
        values = [float(np.sqrt(np.mean(samples[i:i + chunk] ** 2))) for i in range(0, len(samples), chunk)]
        maximum = max(values, default=0.0) if peak is None else float(peak)
        if not math.isfinite(maximum) or maximum < 0:
            raise ValueError("peak must be finite and nonnegative")
        values = np.clip((np.array(values) / max(maximum, 1e-8) - threshold) / (1 - threshold), 0, 1)
        return cls(values, chunk / rate)


def viseme(t: float, cues: list[tuple[float, str]], default="rest") -> str:
    """Select a manually authored or externally aligned mouth cue at time t.

    Cues are (seconds, mouth_name). This does not infer phonemes from audio.
    """
    previous = -math.inf
    result = default
    for time, name in cues:
        if not math.isfinite(time) or time < previous:
            raise ValueError("Viseme cues must be finite and sorted")
        previous = time
        if time <= t:
            result = name
    return result
