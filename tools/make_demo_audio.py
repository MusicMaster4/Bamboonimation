"""Rebuild the original procedural soundtracks shipped with the demo scenes.

No downloaded recordings, reference-film audio, TTS, paid services or external
synthesizers are used. NumPy oscillators/noise and the standard-library WAV
writer produce fifteen-second mono48kHz PCM16 soundtracks under project license.

Run from any directory:
    python tools/make_demo_audio.py
    python tools/make_demo_audio.py --output-dir /path/to/audio

The default output is assets/audio relative to this script's repository. Hashes
and measurements are printed for audit; no machine paths enter the WAV files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import wave

import numpy as np

RATE = 48_000
DURATION = 15.0
SAMPLES = int(RATE * DURATION)
MASTER_PEAK = .60


def timeline(seconds):
    return np.arange(max(1, round(seconds * RATE)), dtype=np.float64) / RATE


def envelope(t, *, attack=.008, release=.04):
    """Raised-cosine edges keep synthesized cues free from accidental clicks."""
    duration = len(t) / RATE
    attack = min(attack, duration / 2)
    release = min(release, duration / 2)
    edge_in = .5 - .5 * np.cos(np.pi * np.clip(t / max(attack, 1 / RATE), 0, 1))
    edge_out = .5 - .5 * np.cos(np.pi * np.clip((duration - t) / max(release, 1 / RATE), 0, 1))
    return edge_in * edge_out


def noise(rng, seconds, low=150, high=2500):
    """Smooth spectral band selection avoids the harshness of raw white noise."""
    n = max(1, round(seconds * RATE))
    frequencies = np.fft.rfftfreq(n, 1 / RATE)
    spectrum = np.fft.rfft(rng.normal(0, 1, n))
    low_edge = np.clip((frequencies - low * .55) / max(low * .45, 1), 0, 1)
    high_edge = np.clip((high * 1.2 - frequencies) / max(high * .2, 1), 0, 1)
    band = (.5 - .5 * np.cos(np.pi * low_edge)) * (.5 - .5 * np.cos(np.pi * high_edge))
    result = np.fft.irfft(spectrum * band, n)
    return result / max(float(np.max(np.abs(result))), 1e-12)


def add(track, sound, start, level=1):
    start_sample = round(start * RATE)
    if start_sample < 0:
        sound = sound[-start_sample:]
        start_sample = 0
    count = min(len(sound), len(track) - start_sample)
    if count > 0:
        track[start_sample:start_sample + count] += level * sound[:count]


def glide(seconds, begin, end, *, vibrato=0):
    t = timeline(seconds)
    u = t / max(seconds, 1 / RATE)
    frequency = begin * np.power(end / begin, u)
    if vibrato:
        frequency *= 1 + vibrato * np.sin(2 * np.pi * 5 * t)
    phase = 2 * np.pi * np.cumsum(frequency) / RATE
    return t, phase


def celesta(frequency, seconds=1.2):
    t = timeline(seconds)
    # Original inharmonic glass-like timbre; the note sequence is authored below.
    result = (.72 * np.sin(2 * np.pi * frequency * t) * np.exp(-3.3 * t)
              + .18 * np.sin(2 * np.pi * frequency * 2.003 * t) * np.exp(-6 * t)
              + .08 * np.sin(2 * np.pi * frequency * 4.01 * t) * np.exp(-10 * t))
    return result * envelope(t, attack=.004, release=.12)


def ceramic(seconds=.4):
    t = timeline(seconds)
    result = (.52 * np.sin(2 * np.pi * 1260 * t) * np.exp(-20 * t)
              + .27 * np.sin(2 * np.pi * 1973 * t) * np.exp(-28 * t)
              + .12 * np.sin(2 * np.pi * 3037 * t) * np.exp(-40 * t)
              + .18 * np.sin(2 * np.pi * 270 * t) * np.exp(-32 * t))
    return result * envelope(t, attack=.0015, release=.06)


def pop(seconds=.16, begin=310, end=95):
    t, phase = glide(seconds, begin, end)
    return (.8 * np.sin(phase) + .12 * np.sin(phase * 2)) * np.exp(-t * 15) * envelope(t, attack=.003, release=.04)


def hop(rng, seconds=.25):
    t, phase = glide(seconds, 210, 520)
    body = np.sin(phase) * np.exp(-t * 7)
    air = noise(rng, seconds, 450, 1800) * np.exp(-t * 10)
    return (.65 * body + .1 * air) * envelope(t, attack=.012, release=.06)


def landing(rng, seconds=.22):
    t = timeline(seconds)
    return (np.sin(2 * np.pi * 105 * t) * np.exp(-t * 24)
            + .19 * noise(rng, seconds, 100, 850) * np.exp(-t * 20)) * envelope(t, attack=.005, release=.08)


def room(rng):
    t = timeline(DURATION)
    # Very quiet diffuse room texture; no recorded identifiable environment.
    return noise(rng, DURATION, 80, 700) * (.0018 + .0005 * np.sin(2 * np.pi * .21 * t))


def cup_whistle(rng, seconds=1.9):
    """Airborne arc: pitch rises through apex and relaxes on the descent."""
    t = timeline(seconds)
    u = t / seconds
    pitch = np.interp(u, [0, .525, 1], [480, 1130, 370])
    phase = 2 * np.pi * np.cumsum(pitch) / RATE
    air = noise(rng, seconds, 400, 2100)
    airy = .58 * np.sin(phase) + .06 * np.sin(phase * 2.01) + .12 * air
    return airy * envelope(t, attack=.16, release=.3) * (.65 + .35 * np.sin(np.pi * u))


def sneeze(rng):
    seconds = .42
    t, phase = glide(seconds, 345, 115)
    # A soft breathy burst and falling voiced tone suggest a comic sneeze without
    # synthesizing speech or imitating a voice from the source film.
    burst = noise(rng, seconds, 650, 3700) * np.exp(-t * 14)
    voice = (np.sin(phase) + .23 * np.sin(phase * 2)) * np.exp(-t * 8)
    return (.72 * burst + .35 * voice) * envelope(t, attack=.007, release=.12)


def tea_for_two():
    rng = np.random.default_rng(17017)
    track = room(rng)
    # Sparse, newly authored notes leave room for the acting and sound effects.
    for start, frequency in [(0.22, 440), (.77, 659.255), (1.3, 493.883),
                             (3.18, 587.33), (3.72, 783.991),
                             (8.72, 523.251), (9.55, 659.255), (10.4, 880),
                             (12.05, 659.255), (12.82, 587.33), (13.58, 523.251)]:
        add(track, celesta(frequency), start, .028)
    add(track, ceramic(), 44 / 24, .13)              # Fingers contact/lift cup.
    inhale_t = timeline(.29)
    inhale = noise(rng, .29, 300, 1900) * (inhale_t / .29) ** 1.4
    add(track, inhale * envelope(inhale_t, attack=.07, release=.025), 4.36, .075)
    add(track, sneeze(rng), 4 + 16 / 24, .53)      # Sneeze on the cut/exposure.
    add(track, cup_whistle(rng, 34 / 24), 115 / 24, .10)        # Cup airborne until frame149.
    add(track, landing(rng), 139 / 24, .09)       # Planted landing before catch.
    add(track, pop(.17, 250, 100), 149 / 24, .18)      # Catch/contact.
    add(track, ceramic(.55), 7.5, .15)            # Cup settles on table.
    add(track, ceramic(.25), 7.63, .035)          # Gentle ceramic follow-through.
    add(track, hop(rng, .24), 9.0, .09)           # Small resolution hop.
    add(track, landing(rng), 9.27, .05)
    add(track, ceramic(.3), 12.25, .025)          # Quiet shared-tea resolution.
    add(track, celesta(261.626, seconds=1.8), 13.58, .012)
    return master(track)


def the_last_cookie():
    rng = np.random.default_rng(33033)
    track = room(rng)
    for start, frequency in [(.2, 523.251), (1.1, 783.991), (2.0, 659.255),
                             (4.6, 587.33), (8.6, 440), (9.65, 659.255),
                             (10.35, 523.251), (12.0, 659.255), (12.72, 587.33),
                             (13.50, 523.251)]:
        add(track, celesta(frequency), start, .026)
    add(track, hop(rng), 2.70, .13)
    add(track, landing(rng), 4.20, .15)
    add(track, hop(rng, .22), 5.10, .11)
    t, phase = glide(.58, 420, 1050)
    toss = (np.sin(phase) + .12 * noise(rng, .58, 300, 1800)) * envelope(t, attack=.04, release=.15)
    add(track, toss, 5.60, .09)
    add(track, pop(.11, 390, 220), 3.10, .07)     # Plate-to-paw snatch.
    add(track, pop(.18, 280, 95), 6.75, .21)
    add(track, landing(rng, .26), 7.50, .12)
    add(track, paper_rustle(rng, .18, crisp=True), 9.80, .05)  # Cookie break.
    add(track, pop(.12, 410, 190), 10.95, .055)   # Offered share reaches companion.
    nibble_t = timeline(.12)
    for start in (11.15, 11.38, 11.58):
        nibble = noise(rng, .12, 600, 2400) * np.exp(-nibble_t * 23)
        add(track, nibble * envelope(nibble_t, attack=.004, release=.04), start, .018)
    # Soft original chuckle-like falling tones, not speech or a sampled voice.
    for start in (11.9, 12.2, 12.5):
        add(track, pop(.16, 240, 170), start, .024)
    add(track, celesta(261.626, seconds=1.8), 13.50, .012)
    return master(track)


def paper_rustle(rng, seconds=.4, *, crisp=False):
    t = timeline(seconds)
    sound = noise(rng, seconds, 450 if crisp else 200, 4200 if crisp else 2600)
    flutter = .45 + .55 * np.sin(2 * np.pi * (13 * t + 8 * t * t)) ** 2
    return sound * flutter * envelope(t, attack=.035, release=.12)


def shimmer(rng, seconds=1.1, root=880):
    t = timeline(seconds)
    result = np.zeros_like(t)
    for ratio, level, decay in [(1, .55, 2.6), (1.5, .28, 3.5), (2.01, .13, 5.2)]:
        result += level * np.sin(2 * np.pi * root * ratio * t) * np.exp(-t * decay)
    result += .045 * noise(rng, seconds, 1200, 4300) * np.exp(-t * 5)
    return result * envelope(t, attack=.012, release=.24)


def paper_moon():
    """An original fifteen-second miniature scored to paper, ink and a bloom."""
    rng = np.random.default_rng(51051)
    track = room(rng)
    for start, frequency in [(.28, 391.995), (1.12, 587.33), (2.0, 493.883),
                             (3.45, 440), (4.25, 659.255), (5.35, 783.991),
                             (6.12, 587.33), (8.05, 880), (9.65, 659.255),
                             (11.8, 523.251), (12.6, 659.255), (13.4, 783.991),
                             (14.05, 523.251)]:
        add(track, celesta(frequency, seconds=1.3), start, .035)
    # Final authored visual beats: tear1.8, unfold2.3..3, accent3.125,
    # leap3.333..5.75, catch5.75, landing6.5, plant7.6..8.4, bloom8.55..10.
    add(track, paper_rustle(rng, .28, crisp=True), 1.80, .11)
    add(track, paper_rustle(rng, .65), 2.30, .065)
    add(track, pop(.12, 290, 175), 3.125, .055)
    add(track, shimmer(rng, .85, root=739.989), 3.125, .048)
    add(track, hop(rng, .35), 3 + 8 / 24, .13)
    t, phase = glide(2.0, 510, 820)
    flight = np.sin(phase) * envelope(t, attack=.22, release=.35)
    add(track, flight, 3.65, .035)
    add(track, paper_rustle(rng, .32), 5.75, .09)
    add(track, pop(.18, 245, 110), 5.75, .13)
    add(track, landing(rng, .3), 6.50, .095)
    add(track, paper_rustle(rng, .75), 7.60, .045)
    add(track, pop(.14, 170, 95), 8.38, .035)
    add(track, shimmer(rng, 1.5, root=1046.502), 8.55, .065)
    # Small paper-wing flutter supports the final moth payoff without a new burst.
    for index, start in enumerate((12.30, 12.82, 13.40, 14.05)):
        add(track, paper_rustle(rng, .2), start, .018 + .003 * (index % 2))
    add(track, celesta(261.626, seconds=1.8), 13.4, .018)
    return master(track)


def master(track):
    if not np.all(np.isfinite(track)):
        raise ValueError("Nonfinite audio generated")
    # Normalize below full scale, then fade both ends to prevent abrupt edges.
    peak = float(np.max(np.abs(track)))
    if peak:
        track = track * (MASTER_PEAK / peak)
    t = timeline(DURATION)
    return track * envelope(t, attack=.08, release=.3)


def write_wav(path, samples):
    if len(samples) != SAMPLES:
        raise ValueError("Demo soundtracks must be exactly15seconds")
    if float(np.max(np.abs(samples))) > .65:
        raise ValueError("Demo soundtrack exceeds safe peak ceiling")
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.rint(samples * 32767).astype("<i2")
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(pcm.tobytes())
    # Measure the actual quantized file, rather than assuming synthesis settings.
    with wave.open(str(path), "rb") as wav:
        data = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").astype(np.float64) / 32768
        report = {"file": path.name, "sample_rate": wav.getframerate(), "channels": wav.getnchannels(),
                  "sample_width_bits": wav.getsampwidth() * 8, "frames": wav.getnframes(),
                  "duration_seconds": wav.getnframes() / wav.getframerate(),
                  "peak": float(np.max(np.abs(data))), "rms": float(np.sqrt(np.mean(data ** 2)))}
    report["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[1] / "assets" / "audio")
    args = parser.parse_args()
    reports = [write_wav(args.output_dir / "tea_for_two.wav", tea_for_two()),
               write_wav(args.output_dir / "the_last_cookie.wav", the_last_cookie()),
               write_wav(args.output_dir / "paper_moon.wav", paper_moon())]
    print(json.dumps({"provenance": "Original procedural synthesis; no external audio samples", "seed": [17017, 33033, 51051], "assets": reports}, indent=2))


if __name__ == "__main__":
    main()
