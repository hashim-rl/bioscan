from app.screens.camera_capture import CameraCaptureScreen


def test_departed_capture_callback_discards_private_jpeg(tmp_path):
    screen = CameraCaptureScreen(name='camera_capture')
    screen.capture_generation = 2
    jpeg = tmp_path / 'pending.jpg'
    jpeg.write_bytes(b'old session')
    screen._native_captured(1, str(jpeg), (200, 400), (50, 100, 100, 200))
    assert not jpeg.exists()
    assert not screen.processing


def test_departed_error_and_cancel_cannot_modify_new_session():
    screen = CameraCaptureScreen(name='camera_capture')
    screen.capture_generation = 2
    screen.lbl_status.text = 'Current session'
    screen._native_error(1, 'Old error')
    screen._native_cancelled(1)
    assert screen.lbl_status.text == 'Current session'
