# Paper Moon

`examples/paper_moon.py` is an original fifteen-second vector cartoon: a folded crane becomes a five-tailed fox, catches a falling moon-seed, plants it and watches a moth emerge from the flower.

The scene demonstrates a different subject and topology from the other examples. The renderer has no required character, prop library or theme: these subjects are defined with ordinary vector paths and drawing functions. New content still requires authored designs, poses, timing and staging. This is programmable animation authoring, rather than an automatic prompt-to-finished-film claim.

## Render

```powershell
python -m bamboonimation render examples/paper_moon.py -o renders/paper_moon/paper_moon.mp4 --width 1280 --height 720 --fps 24 --overwrite
```

The original optional score is loaded from `assets/audio/paper_moon.wav`. No reference footage, frames, soundtrack, paid model calls or generated raster frames are used by the scene.

## Directing the example

The five cuts share one world painter and absolute story time. The establishing shot shows the stem tearing at 1.8 seconds. A close-up reveals the wings unfolding; two protected impact exposures and a connected smear lead into the leap. A wide shot carries the catch and descent, a close-up shows the planting, and the final wide shot holds the flower and moth payoff.

`DrawingBank` stores independently authored crane, fox, smear and lowering drawings. Their registered feet, beak and paw anchors let actions use the drawing actually displayed. Thirteen explicit contour pairs progressively gather the airborne limbs under the torso. The seed follows the registered reaching paw after the catch, including the eight lowering drawings. The transition uses cached arc-length contour samples as an inbetweening aid for deliberately paired shapes; this is a local scene technique, not an automatic morphing or volume-preservation guarantee.

`ExposureSheet` holds drawings on different frame counts. Protected boundaries preserve the one-frame smear, two impact frames, cuts and contact changes. The camera, flower and atmosphere retain separate clocks. Five tails share a hip root and use `LatticeWarp` for small delayed tip movement. `StaticLayer` caches the painted garden; seeded paper texture and clipped hatching add surface detail without external assets.

To make a new film, replace the drawings, named anchors and story beats instead of recoloring this fox. Arbitrary drawn creatures, people, objects, environments and abstract shapes can use the same mechanisms. Choose replacements or deformation according to the required silhouette, rather than forcing every subject into one rig.

## Verification

The refined export contains 360 H.264 frames at 1280?720 and 24 fps, with a 48 kHz AAC stream. Both streams are exactly 15 seconds. Local render time was 23.152 seconds with two raster threads and no supersampling, producing 2,274,557 bytes; this is one machine measurement, not a general performance guarantee.

Every frame was inspected in fifteen sequential contact sheets. Review corrected detached tail roots, fragmented impact silhouettes, the catch body jump and seed/paw separation during lowering. The final inspection covered frames 0?359 without gaps. The passage into the landing now gathers the whole connected body rather than replacing an airborne horizontal fox with a standing body in one frame.

The design intentionally has a quiet opening and a held final reaction. It does not demonstrate dialogue, complex perspective rotation, crowds or every possible animation style. Those require their own authored scene and review. Review the export for motion, contour, overlap, contact, timing and staging; API availability alone does not establish artistic quality.
