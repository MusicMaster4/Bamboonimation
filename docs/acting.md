# Acting with replacement drawings and variable exposures

The `bamboonimation.acting` module adds three authoring tools: an exposure sheet, a registered drawing bank, and small squash/smear helpers. They make authored cartoon acting easier to schedule and keep attached. They do **not** generate poses, turn one drawing into every camera angle, infer grips, or guarantee a particular film's animation quality. Strong silhouettes and useful replacements still need to be authored in code or supplied as images.

```python
from bamboonimation.acting import (
    ExposureSheet, DrawingBank, Exposure,
    smear_path, volume_preserving_squash,
)
```

## Count holds in source frames

Use an exposure sheet when a uniform `floor(t*12)/12` makes every movement feel equally timed.

```python
from fractions import Fraction
from bamboonimation.acting import ExposureSheet

acting = (
    ExposureSheet(fps=24)
    .add("anticipate", frames=6)
    .add("smear", frames=1)
    .add("impact", frames=2)
    .add("recover", frames=9)
    .add("rest", frames=12)
)

assert acting.key(Fraction(5, 24)) == "anticipate"
assert acting.key(Fraction(6, 24)) == "smear"
assert acting.key(Fraction(7, 24)) == "impact"
assert acting.total_frames == 30
assert acting.duration == 1.25
```

The end of one exposure is the beginning of the next; there is no ambiguous shared endpoint. Exact `Fraction` timestamps preserve rational source boundaries. Normal float timestamps allow one ULP of multiplication rounding at a source-frame boundary. Sampling is deterministic and can happen in any order. Negative or nonfinite times are errors. An empty sheet cannot be sampled. After the sheet ends, the final drawing holds indefinitely.

The source rate can also be rational:

```python
acting = ExposureSheet(source_fps="24000/1001")
acting.add("hold", frames=12).add("turn", frames=2)
```

`sheet.duration_fraction` returns the exact rational duration; `sheet.duration` returns seconds as a float.

### Inspect a sample

`sheet.sample(t)` returns a frozen `Exposure` object:

| Field/property | Meaning |
|---|---|
| `drawing_key` / `drawing` | Selected authored drawing name. |
| `source_frame` / `frame` | Zero-based current source frame, clamped at the last sheet frame. |
| `start_frame` | First source frame of this exposure. |
| `hold_frames` | Number of source frames assigned to this exposure. |
| `fps` | Source rate as `Fraction`. |
| `start_time` / `time` | Exposure's absolute source start time in seconds. |
| `source_time` | Current source frame's absolute time in seconds. |
| `local_frame` | Source frames elapsed within the exposure. |
| `local_time` | Seconds elapsed within the exposure. |

`sheet.key(t)` is shorthand for `sheet.sample(t).drawing_key`. `sheet.time(t)` is the **exposure start time**, useful for holding a procedural pose or choreography while another layer continues moving.

```python
# Independent timing: a held actor and a continuously moving camera/effect.
a = actor_sheet.time(t)
actor_x = authored_walk_position(a)
actor_pose = authored_pose_at(a)
camera_x = authored_camera_position(t)
```

Repeated drawing keys can still have separate exposures. For a moving procedural drawing on twos, append the same key with `frames=2` for each authored update; its exposure start time advances on every pair. A long `frames=12` exposure genuinely holds that drawing's sampled time for half a second at 24 fps.

Export FPS is independent of source FPS. At 60 fps, a source 24 fps drawing repeats across output frames. At a lower output rate, short source exposures can be skipped: a one-source-frame smear may not be sampled by a 12 fps export. Use source 24 fps or higher output for a 24 fps exposure sheet when every one-frame accent must remain visible, or retime the sheet for the target output. Arbitrary output FPS does not manufacture missing drawings.

## Register replacement drawings

`DrawingBank` switches named drawings immediately, without blending their topology. Each drawing may be a `painter(canvas, time)` callable or an image path. Its `registration` point is the local coordinate that will land at the placement `(x, y)`.

```python
from bamboonimation.acting import DrawingBank

bank = DrawingBank()
bank.add(
    "open",
    paint_open_hand,                # callable(canvas, time)
    registration=(12, 30),          # wrist inside the authored drawing
    anchors={"wrist": (12, 30), "grip": (48, 20)},
)
bank.add(
    "closed",
    paint_closed_hand,
    registration=(8, 26),           # different local art, same semantic wrist
    anchors={"wrist": (8, 26), "grip": (39, 14)},
)
```

The registration coordinates may differ between drawings. If both register at the wrist, replacing open with closed keeps the wrist planted. Named attachment anchors are measured in each drawing's **untransformed local coordinates**.

```python
placement = dict(x=640, y=360, scale=1.25, rotation=-18)
key = hand_sheet.key(t)

bank.draw(c, key, **placement, time=hand_sheet.time(t))
gx, gy = bank.anchor(key, "grip", **placement)
draw_prop(c, gx, gy)
```

The anchor calculation uses the same order as drawing: subtract registration, scale, rotate, then translate. Positive rotation follows screen coordinates, clockwise in degrees. `scale` may be one nonzero number or an `(sx, sy)` pair; negative values allow mirroring. If drawing occurs inside an enclosing canvas/camera transform, returned coordinates are in that parent's logical coordinate system. Apply the same enclosing transform to the prop. This helper does not inspect a scene graph to infer parent/world transforms.

Keep placement arguments identical between `.draw()` and `.anchor()`. Missing keys and missing anchors raise explicit `KeyError`s. Duplicate drawing names raise `ValueError`; a typo cannot silently replace registered artwork. The bank copies anchor definitions and exposes them read-only, so later mutation of the caller's original anchor dictionary does not move existing attachments. `.get(key)` returns a frozen `RegisteredDrawing`; `.keys()` returns registered names.

### Grip and occlusion

A registered grip establishes position, not visible contact by itself. To make a hand enclose a prop, author separate back and front finger shapes:

1. Draw palm/back fingers.
2. Draw the attached prop at the matching anchor.
3. Draw thumb/front fingers.

Separate banks or ordinary painters can represent these layers. Match their registration/anchor definitions for every replacement. For a turn or foreshortened reach, author the new silhouette, finger spacing and occlusion order; a scale transform of the same frontal hand will not produce convincing perspective.

### Image drawings

```python
bank.add(
    "profile",
    "assets/profile.png",
    registration=(180, 480),
    anchors={"feet": (180, 480), "grip": (278, 260)},
)

# To deliberately redraw the image at a local size, specify size=(w,h).
bank.add("insert", "assets/insert.png", size=(400, 300),
         registration=(200, 150), anchors={"center": (200, 150)})
```

Image anchor coordinates must match the local size used for drawing. Resolve file paths against your scene file with `Path(__file__).parent` when the CLI may be launched from another directory. Vector painters remain resolution independent; image replacements have the usual raster resolution limits.

## Brief directional smears

```python
from bamboonimation.acting import smear_path

bank.add(
    "smear",
    lambda c, t: c.path(
        smear_path((0, 0), (150, -35), width=34, curve=-18),
        fill="#d67f4f", stroke="#302d3c", width=2,
    ),
    registration=(0, 0),
    anchors={"grip": (150, -35)},
)
```

`smear_path(start, end, width, curve=0)` returns a closed SVG lens silhouette. `width` is the full midpoint thickness. `curve` is signed midpoint displacement perpendicular to start→end. Start and end must differ; width must be positive. The helper creates a directional filled shape, not an anatomical character drawing. Author a custom replacement when the smear needs a recognizable head, fingers, costume, or multiple limbs. Expose it for the intended short accent rather than smoothing it over many frames. Many fast actions read better with a strong extreme drawing and no smear.

## Preserve area during squash

```python
from bamboonimation.acting import volume_preserving_squash
sx, sy = volume_preserving_squash(0.8)   # (1.25, 0.8)
bank.draw(c, "crouch", x=640, y=650, scale=(sx, sy))
```

Despite the conventional helper name, this preserves **2D area** (`sx*sy == 1`), not 3D volume. It does not automatically keep knees, hands or a prop attached. Register a planted foot, or recompute the appropriate attachment anchor, and author shoulders/head/follow-through separately when the action needs them.

## A useful acting workflow

1. Write the beat and attention direction before drawing movement.
2. Author a neutral drawing, anticipation, action extreme, contact and recovery. Add profile/back or foreground inserts when the story requires them.
3. Register the same semantic foot/wrist/root across replacements. Add explicit grip/eye/prop anchors.
4. Assign variable holds. Keep actor, companion, prop and effects on independent schedules where appropriate.
5. Review every output frame around a drawing switch, prop contact, shot cut, smear or impact; then watch at normal speed.
6. Check silhouette readability, planted contacts, volume/design consistency and deliberate stillness. More jitter or more moving parts is not automatically better acting.

The module supplies timing and registration infrastructure. A finished short still needs design, acting choices, drawing replacements, shot composition and visual review.
