import collections, cv2
from config import *
from PyQt5 import QtCore, QtGui, QtWidgets

# -----------------------
# Worker: ejecuta en su propio QThread y gestiona cv2.VideoCapture + cache + lectura secuencial
# -----------------------
class VideoWorker(QtCore.QObject):
    frames_ready = QtCore.pyqtSignal(object)  # dict
    opened = QtCore.pyqtSignal(float, int)
    error = QtCore.pyqtSignal(str)

    def __init__(self, cache_size=CACHE_SIZE, parent=None):
        super().__init__(parent)
        self.cap = None
        self.path = None
        self.fps = 25.0
        self.frame_count = 0
        self.cache = collections.OrderedDict()
        self.cache_size = cache_size
        self.last_sequential = None
        self._running = True
        self._lock = QtCore.QMutex()

    @QtCore.pyqtSlot(str)
    def open(self, path):
        with QtCore.QMutexLocker(self._lock):
            try:
                if self.cap is not None:
                    try:
                        self.cap.release()
                    except Exception:
                        pass
                    self.cap = None
                self.cap = cv2.VideoCapture(path)
                if not self.cap.isOpened():
                    self.error.emit(f"No se pudo abrir: {path}")
                    return
                self.path = path
                self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 25.0
                self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
                self.cache.clear()
                self.last_sequential = None
                self.opened.emit(self.fps, self.frame_count)
            except Exception as e:
                self.error.emit(str(e))

    @QtCore.pyqtSlot()
    def close(self):
        with QtCore.QMutexLocker(self._lock):
            try:
                if self.cap is not None:
                    self.cap.release()
                self.cap = None
                self.cache.clear()
                self.last_sequential = None
            except Exception:
                pass

    def _cache_put(self, idx, rgb_array):
        if idx in self.cache:
            self.cache.move_to_end(idx)
            return
        self.cache[idx] = rgb_array
        while len(self.cache) > self.cache_size:
            self.cache.popitem(last=False)

    def _get_from_cache(self, idx):
        v = self.cache.get(idx, None)
        if v is not None:
            self.cache.move_to_end(idx)
        return v

    def _read_frame_at(self, idx):
        if self.cap is None:
            return None
        ok = self.cap.set(cv2.CAP_PROP_POS_FRAMES, float(idx))
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.last_sequential = idx
        return rgb

    def _read_next_sequential(self):
        if self.cap is None:
            return None, None
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return None, None
        pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES) - 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.last_sequential = pos
        return pos, rgb

    @QtCore.pyqtSlot(int, bool)
    def request_frames(self, center_frame, show_adjacent):
        with QtCore.QMutexLocker(self._lock):
            if self.cap is None:
                self.error.emit("No hay video abierto.")
                return
            center_frame = max(0, min(center_frame, self.frame_count - 1))
            if show_adjacent:
                need = [i for i in range(center_frame - 2, center_frame + 3) if 0 <= i < self.frame_count]
            else:
                need = [center_frame]

            result = {}
            missing = []
            for idx in need:
                v = self._get_from_cache(idx)
                if v is not None:
                    result[idx] = v
                else:
                    missing.append(idx)

            if not missing:
                self.frames_ready.emit(result)
                return

            missing_sorted = sorted(missing)
            runs = []
            run = [missing_sorted[0]]
            for m in missing_sorted[1:]:
                if m == run[-1] + 1:
                    run.append(m)
                else:
                    runs.append(run)
                    run = [m]
            runs.append(run)

            for run in runs:
                start = run[0]
                end = run[-1]
                do_sequential = False
                if self.last_sequential is not None:
                    if start == self.last_sequential + 1:
                        do_sequential = True
                    elif 0 <= start - self.last_sequential <= 3:
                        do_sequential = True
                if do_sequential:
                    desired_pos = max(start, (self.last_sequential + 1) if self.last_sequential is not None else start)
                    ok = True
                    if desired_pos != int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)):
                        ok = self.cap.set(cv2.CAP_PROP_POS_FRAMES, float(desired_pos))
                    for target in range(desired_pos, end + 1):
                        ret, frame = self.cap.read()
                        if not ret or frame is None:
                            ok = False
                            break
                        pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES) - 1)
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        self._cache_put(pos, rgb)
                        result[pos] = rgb
                        self.last_sequential = pos
                    if not ok:
                        for target in run:
                            v = self._read_frame_at(target)
                            if v is not None:
                                self._cache_put(target, v)
                                result[target] = v
                else:
                    for target in run:
                        v = self._read_frame_at(target)
                        if v is not None:
                            self._cache_put(target, v)
                            result[target] = v

            self.frames_ready.emit(result)

#