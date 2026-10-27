"""Timing and registration invariants for hand-authored replacement animation."""
from dataclasses import FrozenInstanceError
from fractions import Fraction
import math

import numpy as np
import pytest
import skia

from bamboonimation.acting import DrawingBank, ExposureSheet, smear_path, volume_preserving_squash
from bamboonimation.drawing import Canvas, svg_path


def canvas(width=240, height=240):
    surface = skia.Surface(width, height)
    surface.getCanvas().clear(skia.ColorTRANSPARENT)
    return surface, Canvas(surface.getCanvas(), width, height)


def test_mixed_exposures_exact_boundaries_and_random_seek():
    sheet = ExposureSheet(fps=24).add("anticipate", frames=6).add("smear", frames=1).add("impact", frames=2).add("settle", frames=9)
    assert sheet.duration_fraction == Fraction(3, 4)
    assert sheet.total_frames == 18
    assert sheet.key(Fraction(5, 24)) == "anticipate"
    assert sheet.key(Fraction(6, 24)) == "smear"
    assert sheet.key(Fraction(7, 24)) == "impact"
    assert sheet.key(Fraction(9, 24)) == "settle"
    # Float source-frame boundaries and exact rational export timestamps agree.
    for frame in range(18):
        assert sheet.sample(frame / 24) == sheet.sample(Fraction(frame, 24))
    samples = {t: sheet.sample(t) for t in (0, .2, .25, .3, .375, 100)}
    for t in (100, .3, .25, .2, 0, .375):
        assert sheet.sample(t) == samples[t]
    assert sheet.key(100) == "settle"
    assert sheet.time(.34) == float(Fraction(7, 24))
    impact = sheet.sample(Fraction(8, 24))
    assert impact.drawing == "impact"
    assert impact.start_frame == 7
    assert impact.hold_frames == 2
    assert impact.local_frame == 1
    assert impact.local_time == float(Fraction(1, 24))
    with pytest.raises(FrozenInstanceError):
        impact.source_frame = 7


def test_rational_source_fps_is_independent_of_export_fps():
    sheet = ExposureSheet(source_fps="24000/1001").add("first", frames=2).add("second", frames=3)
    assert sheet.duration_fraction == Fraction(5005, 24000)
    assert sheet.key(Fraction(2002, 24000)) == "second"
    assert sheet.time(Fraction(3003, 24000)) == float(Fraction(2002, 24000))
    # Sampling a higher-FPS output repeats source drawings without interpolation.
    assert [sheet.key(Fraction(i, 60)) for i in range(6)] == ["first"] * 6
    assert sheet.key(Fraction(6, 60)) == "second"


def test_exposure_errors_are_explicit():
    for fps in (0, -1, "nan", "1/0", True):
        with pytest.raises(ValueError):
            ExposureSheet(fps=fps)
    with pytest.raises(ValueError, match="empty"):
        ExposureSheet().sample(0)
    for frames in (0, -1, 1.5, True):
        with pytest.raises(ValueError):
            ExposureSheet().add("pose", frames=frames)
    sheet = ExposureSheet().add("pose", frames=2)
    for time in (-.01, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            sheet.sample(time)


def test_named_anchor_matches_actual_canvas_registration_and_flip():
    local_anchor = (31, 15)
    observed = []
    def painter(c, t):
        point = c.raw.getTotalMatrix().mapXY(*local_anchor)
        observed.append((point.x(), point.y(), t))
    bank = DrawingBank().add("reach", painter, registration=(10, 20), anchors={"grip": local_anchor})
    _, c = canvas()
    before = c.raw.getTotalMatrix().get9()
    placement = dict(x=100, y=170, scale=(2, -.5), rotation=37)
    bank.draw(c, "reach", **placement, time=.25)
    target = bank.anchor("reach", "grip", **placement)
    assert observed[0][:2] == pytest.approx(target, abs=1e-5)
    assert observed[0][2] == .25
    assert c.raw.getTotalMatrix().get9() == before
    assert bank.anchor("reach", "grip", x=100, y=200, scale=(2, .5), rotation=90) == pytest.approx((102.5, 242))
    # Seeking/changing placement does not mutate either the local asset or anchors.
    bank.draw(c, "reach", x=20, y=30, time=4)
    bank.draw(c, "reach", **placement, time=.25)
    assert observed[2] == pytest.approx(observed[0])


def test_replacement_switch_is_hard_and_anchor_definitions_are_copied():
    anchors = {"feet": (10, 20)}
    bank = DrawingBank()
    bank.add("front", lambda c,t: c.rect(0, 0, 20, 20, "#ff0000"), registration=(10, 20), anchors=anchors)
    bank.add("back", lambda c,t: c.rect(0, 0, 20, 20, "#0000ff"), registration=(10, 20), anchors=anchors)
    anchors["feet"] = (999, 999)
    assert bank.anchor("front", "feet", 40, 50) == (40, 50)
    with pytest.raises(TypeError):
        bank.get("front").anchors["feet"] = (0, 0)
    sheet = ExposureSheet().add("front", frames=4).add("back", frames=4)
    colors = []
    for time in (Fraction(3, 24), Fraction(4, 24)):
        surface, c = canvas()
        bank.draw(c, sheet.key(time), 40, 50)
        pixels = surface.makeImageSnapshot().toarray(colorType=skia.ColorType.kRGBA_8888_ColorType)
        colors.append(tuple(pixels[40, 40]))
    assert colors == [(255, 0, 0, 255), (0, 0, 255, 255)]


def test_bank_missing_keys_anchors_and_invalid_transforms():
    bank = DrawingBank().add("idle", lambda c,t: None, anchors={"origin": (0, 0)})
    with pytest.raises(KeyError, match="Unknown drawing key"):
        bank.get("missing")
    with pytest.raises(KeyError, match="no anchor"):
        bank.anchor("idle", "grip")
    with pytest.raises(ValueError, match="already registered"):
        bank.add("idle", lambda c,t: None)
    with pytest.raises(ValueError):
        bank.anchor("idle", "origin", scale=0)
    _, c = canvas()
    with pytest.raises(ValueError, match="nonzero"):
        bank.draw(c, "idle", scale=0)
    with pytest.raises(ValueError):
        bank.add("broken", lambda c,t: None, registration=(math.nan, 0))


def test_image_replacement_uses_local_size_and_registration(tmp_path):
    surface, source = canvas(8, 8)
    source.rect(0, 0, 8, 8, "#ff0000")
    image = tmp_path / "drawing.png"
    image.write_bytes(bytes(surface.makeImageSnapshot().encodeToData(skia.kPNG, 100)))
    bank = DrawingBank().add("image", image, registration=(10, 10), anchors={"center": (10, 10)}, size=(20, 20))
    target, c = canvas()
    bank.draw(c, "image", 50, 60)
    pixels = target.makeImageSnapshot().toarray(colorType=skia.ColorType.kRGBA_8888_ColorType)
    assert tuple(pixels[60, 50]) == (255, 0, 0, 255)
    assert pixels[30, 30, 3] == 0
    assert bank.anchor("image", "center", 50, 60) == (50, 60)


def test_directional_smear_geometry_and_area_squash():
    horizontal = svg_path(smear_path((0, 0), (100, 0), width=20)).computeTightBounds()
    vertical = svg_path(smear_path((0, 0), (0, 100), width=20)).computeTightBounds()
    assert horizontal.width() == pytest.approx(100)
    assert horizontal.height() == pytest.approx(20)
    assert vertical.width() == pytest.approx(20)
    assert vertical.height() == pytest.approx(100)
    assert "nan" not in smear_path((10, 20), (60, 40), width=12, curve=-8)
    for scale in (.25, .8, 1, 1.6, 3):
        sx, sy = volume_preserving_squash(scale)
        assert sx * sy == pytest.approx(1)
    for scale in (0, -1, math.nan, math.inf):
        with pytest.raises(ValueError):
            volume_preserving_squash(scale)
    with pytest.raises(ValueError):
        smear_path((0, 0), (0, 0), 20)
    with pytest.raises(ValueError):
        smear_path((0, 0), (10, 20), -1)
