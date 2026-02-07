import os, sys
import subprocess
import tempfile
import shutil
import traceback
import math, re
from PyQt5 import QtCore, QtWidgets
from utils import *

# -----------------------
# FFmpeg worker: ejecuta el recorte en background y emite progreso
# -----------------------

def get_real_start_for_copy(requested_start, keyframes, fps):
    """
    Calcula el timestamp real que FFmpeg usará con '-c copy',
    usando los keyframes disponibles en tu navegador de frames.

    Parameters:
        requested_start (float): tiempo deseado en segundos
        keyframes (list[int]): lista de números de frame que son keyframes
        fps (float): frames por segundo del video

    Returns:
        float: timestamp real (en segundos) del keyframe más cercano <= requested_start
    """
    if not keyframes:
        return requested_start  # fallback si no hay keyframes

    # Convertimos frames a tiempo en segundos
    keyframe_times = [kf / fps for kf in keyframes]

    # Filtramos keyframes antes o igual al tiempo solicitado
    candidates = [kf_time for kf_time in keyframe_times if kf_time <= requested_start]

    if not candidates:
        return keyframe_times[0]  # primer keyframe disponible

    return max(candidates)

class FFmpegWorker(QtCore.QObject):
    progress = QtCore.pyqtSignal(int)        # percent
    status = QtCore.pyqtSignal(str)          # status message
    finished = QtCore.pyqtSignal(str)       # output path
    error = QtCore.pyqtSignal(str)          # traceback or message

    def __init__(self):
        super().__init__()
        self._proc = None
        self._cancel_requested = False

    @QtCore.pyqtSlot(dict)
    def run_cut(self, params):
        """
        params: dict with keys:
            in_path, out_path, start_sec, end_sec, optimize_for_share (bool),
            add_black (bool), fps, width, height
        """
        try:
            in_path = params['in_path']
            out_path = params['out_path']
            start_sec = float(params['start_sec'])
            end_sec = float(params['end_sec'])
            optimize = bool(params.get('optimize_for_share', False))
            add_black = bool(params.get('add_black', False))
            fps = float(params.get('fps', 25.0))
            width = int(params.get('width', 0))
            height = int(params.get('height', 0))

            if end_sec <= start_sec:
                raise ValueError("El tiempo final debe ser mayor que el inicio.")

            total_expected = end_sec - start_sec
            if add_black:
                total_expected += 5.0

            self.status.emit("Iniciando recorte...")

            # Ensure output dir exists
            out_dir = os.path.dirname(out_path)
            os.makedirs(out_dir, exist_ok=True)

            tmpdir = tempfile.mkdtemp(prefix="video_cut_")
            try:
                requested_start = start_sec
                requested_end = end_sec

                if not optimize:
                    real_start = get_real_start_for_copy(
                        requested_start,
                        keyframes=params.get('keyframes', []),  # lista de frames I
                        fps=fps
                    )
                    if real_start < requested_start:
                        # desplazamiento real
                        shift = requested_start - real_start
                        start_sec = real_start
                        end_sec = requested_end
                    else:
                        shift = 0.0
                else:
                    shift = 0.0

                if shift > 0:
                    print(f"[ffmpeg] start ajustado: -{shift:.3f}s (keyframe)")
    
                # Step 1: cut portion to temp file
                cut_tmp = os.path.join(tmpdir, "cut.mp4")
                
                # If optimize is False, do stream copy; otherwise re-encode for sharing
                if optimize:
                    # re-encode to H.264/AAC with reasonable settings
                    ff_cmd_cut = [
                        "ffmpeg", "-y",
                        "-i", in_path,
                        "-ss", f"{start_sec:.3f}",
                        "-to", f"{end_sec:.3f}",
                        "-vf", f"scale='min({width},iw)':'min({height},ih)':force_original_aspect_ratio=decrease",
                        "-r", str(int(round(fps))),
                        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                        "-c:a", "aac", "-b:a", "128k",
                        cut_tmp
                    ]
                else:
                    # stream copy if possible (fast)
                    ff_cmd_cut = [
                        "ffmpeg", "-y",
                        "-i", in_path,
                        "-ss", f"{start_sec:.3f}",
                        "-to", f"{end_sec:.3f}",
                        "-c", "copy",
                        cut_tmp
                    ]

                # helper to run ffmpeg and parse progress (based on stderr time=)
                def run_and_track(cmd, expected_duration):
                    # start process
                    self._cancel_requested = False
                    # Hide console window on Windows
                    creationflags = 0
                    if sys.platform == "win32":
                        creationflags = subprocess.CREATE_NO_WINDOW

                    proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                            universal_newlines=True, bufsize=1, creationflags=creationflags)
                    self._proc = proc
                    last_percent = 0
                    time_re = re.compile(r'time=(\d{2}:\d{2}:\d{2}(?:\.\d+)?)')
                    while True:
                        if proc.stderr is None:
                            break
                        line = proc.stderr.readline()
                        if not line:
                            if proc.poll() is not None:
                                break
                            else:
                                continue
                        # parse time=
                        m = time_re.search(line)
                        if m:
                            timestr = m.group(1)
                            # parse hh:mm:ss(.ms)
                            parts = timestr.split(':')
                            hh = float(parts[0])
                            mm = float(parts[1])
                            ss = float(parts[2])
                            tsec = hh*3600 + mm*60 + ss
                            # clamp defensivo: ffmpeg puede reportar time > duración esperada
                            if expected_duration > 0 and tsec > expected_duration:
                                tsec = expected_duration
                            pct = min(100, int((tsec / expected_duration) * 100)) if expected_duration > 0 else 0
                            if pct != last_percent:
                                last_percent = pct
                                self.progress.emit(pct)
                        # optional: also parse "size=" or "frame=" if needed

                        if self._cancel_requested:
                            try:
                                proc.terminate()
                            except Exception:
                                pass
                            proc.wait(timeout=2)
                            raise Exception("Cancelado por el usuario.")

                    rc = proc.poll()
                    if rc not in (0, None):
                        # read remaining stderr
                        err = proc.stderr.read() if proc.stderr else ""
                        raise Exception(f"ffmpeg returned {rc}. stderr:\n{err}")

                    # final update to 100% for this stage
                    self.progress.emit(100)

                    return True

                # Run cut command
                # run_and_track(ff_cmd_cut, end_sec - start_sec)
                
                real_duration = end_sec - start_sec
                run_and_track(ff_cmd_cut, real_duration)

                final_output = cut_tmp

                # Step 2: if add_black -> generate 5s black video matching fps/size and concat
                if add_black:
                    black_tmp = os.path.join(tmpdir, "black.mp4")
                    # ensure width/height and fps known; fallback to 1280x720/fps if missing
                    w = width or 1280
                    h = height or 720
                    r = int(round(fps)) if fps and not math.isnan(fps) else 25
                    ff_cmd_black = [
                        "ffmpeg", "-y",
                        "-f", "lavfi",
                        "-i", f"color=size={w}x{h}:duration=5:rate={r}:color=black",
                        "-c:v", "libx264", "-t", "5",
                        "-pix_fmt", "yuv420p",
                        black_tmp
                    ]
                    # track this stage (expected duration is 5s)
                    run_and_track(ff_cmd_black, 5.0)

                    # create concat list
                    list_file = os.path.join(tmpdir, "concat.txt")
                    with open(list_file, "w", encoding="utf-8") as f:
                        f.write(f"file '{cut_tmp.replace('\\', '\\\\')}'\n")
                        f.write(f"file '{black_tmp.replace('\\', '\\\\')}'\n")

                    out_concat = os.path.join(tmpdir, "out_concat.mp4")
                    ff_cmd_concat = [
                        "ffmpeg", "-y",
                        "-f", "concat",
                        "-safe", "0",
                        "-i", list_file,
                        "-c", "copy",
                        out_concat
                    ]
                    # expected duration = (end-start) + 5
                    run_and_track(ff_cmd_concat, (end_sec - start_sec) + 5.0)
                    final_output = out_concat

                # Step 3: move final to out_path
                self.status.emit("Moviendo archivo a destino...")
                try:
                    os.rename(final_output, out_path)
                except OSError:
                    # Diferente unidad o dispositivo, realizar copia por fragmentos
                    try:
                        size = os.path.getsize(final_output)
                        with open(final_output, 'rb') as fsrc:
                            with open(out_path, 'wb') as fdst:
                                copied = 0
                                while True:
                                    buf = fsrc.read(1024*1024) # 1MB chunks
                                    if not buf: break
                                    fdst.write(buf)
                                    copied += len(buf)
                                    pct = int(copied * 100 / size) if size > 0 else 100
                                    self.progress.emit(pct)
                                    self.status.emit(f"Moviendo archivo... {pct}%")
                        os.remove(final_output)
                    except Exception as e:
                        raise Exception(f"Error al mover el archivo final: {e}")
                self.finished.emit(out_path)
            finally:
                try:
                    shutil.rmtree(tmpdir)
                except Exception:
                    pass

        except Exception as e:
            tb = traceback.format_exc()
            self.error.emit(tb)

    def cancel(self):
        self._cancel_requested = True
        try:
            if self._proc is not None:
                try:
                    self._proc.terminate()
                except Exception:
                    pass
        except Exception:
            pass

#