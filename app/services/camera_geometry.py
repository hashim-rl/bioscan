"""Preview (top-left coordinates) to upright still-image ROI.

First normalize EXIF/sensor rotation. For aspect-fill, s=max(Vw/Iw,Vh/Ih).
The image loses dx=(Iw*s-Vw)/2 and dy=(Ih*s-Vh)/2 at its edges.
Map each guide corner with ((x+dx)/s,(y+dy)/s); undo preview mirroring.

CameraX must bind Preview and ImageCapture with ONE ViewPort: otherwise their
sensor fields of view may differ and dimensions alone cannot determine a map.
CameraX saves its viewport crop into JPEG; EXIF transpose produces the upright
image used here. Rotation is only for callers providing pre-transpose dimensions.
Returned bounds index the UPRIGHT image, never the unrotated sensor buffer.
"""
import math


def map_guide_to_image(image_size, preview_size, guide, rotation=0, mirrored=False):
    iw, ih = image_size
    vw, vh = preview_size
    x, y, w, h = guide
    if rotation not in (0, 90, 180, 270):
        raise ValueError("Rotation must be a quarter turn")
    if min(iw, ih, vw, vh, w, h) <= 0 or x < 0 or y < 0 or x+w > vw or y+h > vh:
        raise ValueError("Invalid preview or guide bounds")
    if rotation in (90, 270):
        iw, ih = ih, iw
    if mirrored:
        x = vw - x - w
    scale = max(vw / iw, vh / ih)
    dx, dy = (iw * scale - vw) / 2, (ih * scale - vh) / 2
    return (max(0, math.floor((x+dx)/scale)), max(0, math.floor((y+dy)/scale)),
            min(iw, math.ceil((x+w+dx)/scale)), min(ih, math.ceil((y+h+dy)/scale)))
