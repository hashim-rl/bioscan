"""Small pyjnius boundary. Keep listener alive until native completion."""
from kivy.clock import Clock
from jnius import autoclass, PythonJavaClass, java_method


class CameraListener(PythonJavaClass):
    __javainterfaces__ = ['org/bioscan/camera/ScanCamera$Listener']
    __javacontext__ = 'app'

    def __init__(self, captured, cancelled, error):
        super().__init__()
        self.captured, self.cancelled, self.error = captured, cancelled, error

    @java_method('(Ljava/lang/String;IIFFFF)V')
    def onCaptured(self, path, width, height, x, y, w, h):
        Clock.schedule_once(lambda dt: self.captured(str(path), (width, height), (x, y, w, h)), 0)

    @java_method('()V')
    def onCancelled(self):
        Clock.schedule_once(lambda dt: self.cancelled(), 0)

    @java_method('(Ljava/lang/String;)V')
    def onError(self, message):
        Clock.schedule_once(lambda dt: self.error(str(message)), 0)


class AndroidCamera:
    def __init__(self, captured, cancelled, error):
        self.listener = CameraListener(captured, cancelled, error)
        activity = autoclass('org.kivy.android.PythonActivity').mActivity
        self.native = autoclass('org.bioscan.camera.ScanCamera')(activity, self.listener)

    def open(self, title, config):
        self.native.open(title, config['width_ratio'], config['height_ratio'])

    def close(self):
        self.native.close()
