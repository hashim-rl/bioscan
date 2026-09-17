import pytest
from app.services.camera_geometry import map_guide_to_image


def test_landscape_sensor_fills_portrait_without_stretch():
    # 400x300 image fills 200x400 view at scale 4/3: horizontal edges cropped.
    assert map_guide_to_image((400, 300), (200, 400), (50, 100, 100, 200)) == (162, 75, 238, 225)


def test_rotated_sensor_and_already_cropped_jpeg_agree():
    assert map_guide_to_image((4000, 3000), (300, 400), (75, 100, 150, 200), rotation=90) == (750, 1000, 2250, 3000)
    assert map_guide_to_image((3000, 4000), (300, 400), (75, 100, 150, 200)) == (750, 1000, 2250, 3000)


def test_mirrored_preview_maps_to_unmirrored_image():
    assert map_guide_to_image((400, 400), (400, 400), (0, 100, 100, 200), mirrored=True) == (300, 100, 400, 300)


def test_invalid_geometry_is_rejected():
    with pytest.raises(ValueError):
        map_guide_to_image((400, 300), (0, 400), (0, 0, 20, 20))
    with pytest.raises(ValueError):
        map_guide_to_image((400, 300), (200, 400), (-10, 0, 100, 100))
