"""Captura de audio de Windows (WASAPI + loopback) y análisis en tiempo real.

Arquitectura (todo separado del renderizado):
  * PortAudio llama a un callback en su propio hilo -> escribe muestras mono en un RingBuffer.
  * Un hilo de análisis (~100 Hz) calcula RMS, graves/medios/agudos (FFT), picos, con
    normalización adaptativa y suavizado temporal, y publica un 'Features' inmutable.
  * El hilo de render solo llama a snapshot(); jamás toca PortAudio.
  * Abrir, cambiar, refrescar y reconectar dispositivos se hace en hilos de trabajo, de modo
    que un error de audio nunca bloquea ni cierra la aplicación.
"""
from __future__ import annotations

import collections
import math
import threading
import time
from dataclasses import dataclass, field

import numpy as np

try:  # PyAudioWPatch = PyAudio + WASAPI loopback para Windows
    import pyaudiowpatch as pyaudio
    _PA_ERROR = None
except Exception as exc:  # pragma: no cover - depende del sistema
    pyaudio = None
    _PA_ERROR = exc

try:  # alternativa para Python >= 3.14 (donde PyAudioWPatch aún no tiene ruedas)
    import soundcard as _sc
    _SC_ERROR = None
except Exception as exc:  # pragma: no cover
    _sc = None
    _SC_ERROR = exc

BACKEND_ERROR = None
if pyaudio is None and _sc is None:
    BACKEND_ERROR = "No hay librería de captura: pip install PyAudioWPatch (o soundcard en Python 3.14)"

VIRTUAL_HINTS = ("cable", "voicemeeter", "vb-audio", "virtual")


@dataclass(frozen=True)
class AudioDevice:
    key: str            # identificador estable (tipo + nombre real)
    name: str           # nombre real de Windows
    kind: str           # 'default_loopback' | 'loopback' | 'input' | 'demo'
    index: int          # índice PortAudio (-1 si se resuelve al abrir)
    virtual: bool = False

    @property
    def label(self) -> str:
        if self.kind == "demo":
            return "[DEMO] Señal sintética (sin audio real)"
        if self.kind == "default_loopback":
            return "[SALIDA] Predeterminada de Windows (loopback)"
        tag = {"loopback": "SALIDA", "input": "ENTRADA"}[self.kind]
        if self.virtual:
            tag += "/VIRTUAL"
        return f"[{tag}] {self.name}"


@dataclass
class Features:
    vol: float = 0.0
    bass: float = 0.0
    mid: float = 0.0
    treb: float = 0.0
    peak_count: int = 0       # contador de picos detectados (se incrementa en cada transitorio)
    peak_strength: float = 0.0
    level_db: float = -120.0
    signal: bool = False


class RingBuffer:
    def __init__(self, size: int):
        self.buf = np.zeros(size, np.float32)
        self.size = size
        self.w = 0
        self.lock = threading.Lock()
        self.last_write = 0.0

    def write(self, x: np.ndarray):
        n = len(x)
        if n == 0:
            return
        with self.lock:
            if n >= self.size:
                x = x[-self.size:]
                n = self.size
            i = self.w % self.size
            first = min(n, self.size - i)
            self.buf[i:i + first] = x[:first]
            if n > first:
                self.buf[:n - first] = x[first:]
            self.w += n
            self.last_write = time.perf_counter()

    def latest(self, n: int) -> np.ndarray:
        with self.lock:
            w = self.w
            if w < n:
                out = np.zeros(n, np.float32)
                if w:
                    out[-w:] = self.buf[:w]
                return out
            idx = np.arange(w - n, w) % self.size
            return self.buf[idx].copy()


class Analyzer:
    N = 2048
    BANDS = ((30.0, 220.0), (220.0, 2200.0), (2200.0, 14000.0))

    def __init__(self):
        self.win = np.hanning(self.N).astype(np.float32)
        self.ref = [2e-3, 1e-3, 5e-4]
        self.sm = [0.0, 0.0, 0.0, 0.0]          # graves, medios, agudos, volumen
        self.prev_lm = None
        self.flux_hist = collections.deque(maxlen=70)
        self.last_peak = 0.0
        self.peak_count = 0
        self.peak_strength = 0.0
        self.sens = 1.0
        self._fs = None
        self.idx = []
        self.kflux = None

    def _setup(self, fs):
        freqs = np.fft.rfftfreq(self.N, 1.0 / fs)
        self.idx = [np.flatnonzero((freqs >= lo) & (freqs < hi)) for lo, hi in self.BANDS]
        self.kflux = np.flatnonzero((freqs > 40) & (freqs < 5000))
        self._fs = fs
        self.prev_lm = None
        self.flux_hist.clear()

    @staticmethod
    def _smooth(cur, target, dt, att, rel):
        tau = att if target > cur else rel
        return cur + (target - cur) * (1.0 - math.exp(-dt / tau))

    def process(self, x: np.ndarray, fs: int, dt: float, now: float) -> Features:
        if fs != self._fs:
            self._setup(fs)
        spec = np.abs(np.fft.rfft(x * self.win)) * (4.0 / self.N)
        rms = float(np.sqrt(np.mean(x[-1024:] ** 2)))
        silent = rms < 1.2e-4
        vals = [float(np.sqrt(np.mean(spec[ix] ** 2))) if ix.size else 0.0 for ix in self.idx]
        decay = 0.5 ** (dt / 10.0)           # el techo de normalización se adapta (semivida 10 s)
        tg = []
        for i, v in enumerate(vals):
            self.ref[i] = max(self.ref[i] * decay, v, 2e-4)
            t = 0.0 if silent else (v / self.ref[i]) ** 0.85
            tg.append(min(1.3, t * self.sens))
        self.ref_vol = max(getattr(self, "ref_vol", 5e-3) * decay, rms, 1e-3)
        tv = 0.0 if silent else min(1.3, (rms / self.ref_vol) ** 0.8 * self.sens)
        s = self.sm
        s[0] = self._smooth(s[0], tg[0], dt, 0.030, 0.22)
        s[1] = self._smooth(s[1], tg[1], dt, 0.040, 0.20)
        s[2] = self._smooth(s[2], tg[2], dt, 0.020, 0.14)
        s[3] = self._smooth(s[3], tv, dt, 0.050, 0.30)

        # detección de transitorios por flujo espectral adaptativo
        lm = np.log1p(spec[self.kflux] * 200.0)
        flux = 0.0 if self.prev_lm is None else float(np.sum(np.maximum(lm - self.prev_lm, 0.0)))
        self.prev_lm = lm
        hist = self.flux_hist
        if len(hist) >= 24 and not silent:
            arr = np.fromiter(hist, float)
            thr = arr.mean() + 1.7 * arr.std() + 0.25
            if flux > thr and now - self.last_peak > 0.17 and tv > 0.10:
                self.last_peak = now
                self.peak_count += 1
                self.peak_strength = float(np.clip((flux - thr) / (thr + 1e-3) * 0.9 + 0.45, 0.35, 1.0))
        hist.append(flux)
        db = 20.0 * math.log10(rms + 1e-7)
        return Features(vol=s[3], bass=s[0], mid=s[1], treb=s[2], peak_count=self.peak_count,
                        peak_strength=self.peak_strength, level_db=db, signal=not silent)


class DemoSynth:
    """Generador de música sintética (bombo, hi-hat, bajo, acordes) para probar sin audio real."""

    def __init__(self, fs=44100):
        self.fs = fs
        self.i = 0
        self.rng = np.random.default_rng(5)

    def block(self, n):
        fs = self.fs
        t = (self.i + np.arange(n)) / fs
        self.i += n
        beat = 60.0 / 124.0
        tb = t % beat
        kick = np.sin(2 * np.pi * (46 * tb + 3.6 * (1 - np.exp(-25 * tb)))) * np.exp(-tb * 9) * 0.9
        th = (t + beat / 2) % beat
        hat = self.rng.standard_normal(n) * np.exp(-th * 70) * 0.25
        te = t % (beat / 2)
        snare_t = (t + beat) % (2 * beat)
        snare = self.rng.standard_normal(n) * np.exp(-snare_t * 18) * 0.30 * (snare_t < 0.3)
        bar = (t // (beat * 4)).astype(int) % 4
        f0 = np.array([55.0, 55.0, 65.4, 49.0])[bar]
        bass = (np.sin(2 * np.pi * f0 * t) + 0.4 * np.sin(4 * np.pi * f0 * t)) * 0.30 * (0.6 + 0.4 * np.sin(2 * np.pi * t / beat * 2) ** 2)
        chord = np.array([[220.0, 261.6, 329.6], [220.0, 261.6, 329.6], [261.6, 329.6, 392.0], [196.0, 246.9, 293.7]])[bar]
        pad = sum(np.sin(2 * np.pi * chord[:, k] * t) for k in range(3)) * 0.07
        step = ((t // (beat / 2)).astype(int)) % 8
        arp = np.sin(2 * np.pi * (chord[:, 0] * 2 * (1 + (step % 4) * 0.25)) * t) * 0.10 * np.exp(-te * 9)
        return np.clip(kick + hat + snare + bass + pad + arp, -1, 1).astype(np.float32) * 0.8


def _friendly_error(exc: Exception, label: str) -> str:
    t = str(exc)
    if "-9996" in t or "Invalid device" in t:
        return "El dispositivo ya no está disponible (¿desconectado?). Pulsa «Actualizar» y elige otro."
    if "-9997" in t or "Invalid sample rate" in t:
        return "El dispositivo no admite la configuración de audio solicitada."
    if "-9985" in t or "Device unavailable" in t:
        return "Dispositivo ocupado: otra aplicación lo usa en modo exclusivo."
    if "-9999" in t or "Unanticipated host error" in t:
        return ("Windows rechazó el acceso al dispositivo. Si es un micrófono, activa el acceso en "
                "Configuración > Privacidad y seguridad > Micrófono (aplicaciones de escritorio).")
    return f"No se pudo abrir «{label}»: {t}"


class AudioEngine:
    def __init__(self):
        self._lock = threading.RLock()
        self._ring = RingBuffer(1 << 16)
        self._an = Analyzer()
        self._feat = Features()
        self._flock = threading.Lock()
        self._pa = None
        self._stream = None
        self._demo_thread = None
        self._demo_stop = threading.Event()
        self._devices: list[AudioDevice] = []
        self._selected: AudioDevice | None = None
        self._want_running = False
        self._streaming = False
        self._busy = False
        self._sc_thread = None
        self._sc_stop = threading.Event()
        self._sc_err = None
        self._rate = 48000
        self._last_try = 0.0
        self.status = "Audio detenido."
        self.is_error = False
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="audio-analysis", daemon=True)
        self._thread.start()

    # ------------------------------------------------------------ API pública
    @property
    def devices(self):
        return list(self._devices)

    @property
    def selected(self):
        return self._selected

    @property
    def running(self):
        return self._want_running

    def snapshot(self) -> Features:
        with self._flock:
            return self._feat

    def set_sensitivity(self, v: float):
        self._an.sens = float(v)

    def refresh_devices(self, wait=False, preferred_key=None):
        """Re-enumera los dispositivos (reinicia PortAudio) y reabre la fuente activa."""
        self._run(lambda: self._do_refresh(preferred_key), wait)

    def select(self, dev: AudioDevice):
        self._selected = dev
        self._want_running = True
        self._run(self._open_selected)

    def start(self):
        self._want_running = True
        self._run(self._open_selected)

    def stop(self):
        self._want_running = False
        self._run(self._do_stop)

    def close(self):
        self._stop.set()
        self._want_running = False
        try:
            with self._lock:
                self._close_stream()
                if self._pa is not None:
                    self._pa.terminate()
                    self._pa = None
        except Exception:
            pass

    # ------------------------------------------------------------ internos
    def _run(self, fn, wait=False):
        def work():
            with self._lock:
                self._busy = True
                try:
                    fn()
                except Exception as exc:  # nunca debe cerrar la aplicación
                    self.status = f"Error de audio: {exc}"
                    self.is_error = True
                    self._streaming = False
                finally:
                    self._busy = False
        if wait:
            work()
        else:
            threading.Thread(target=work, name="audio-op", daemon=True).start()

    def _ensure_pa(self):
        if pyaudio is None:
            raise RuntimeError("PyAudioWPatch no está instalado (pip install PyAudioWPatch).")
        if self._pa is None:
            self._pa = pyaudio.PyAudio()
        return self._pa

    def _enumerate(self) -> list[AudioDevice]:
        devs: list[AudioDevice] = []
        if pyaudio is None and _sc is not None:
            devs = self._enumerate_sc()
        elif pyaudio is not None:
            pa = self._ensure_pa()
            wasapi = None
            try:
                wasapi = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            except Exception:
                wasapi = None
            try:
                pa.get_default_wasapi_loopback()
                devs.append(AudioDevice("default_loopback", "default", "default_loopback", -1))
            except Exception:
                pass
            loops, ins = [], []
            for i in range(pa.get_device_count()):
                try:
                    info = pa.get_device_info_by_index(i)
                except Exception:
                    continue
                if wasapi is not None and info.get("hostApi") != wasapi["index"]:
                    continue
                if int(info.get("maxInputChannels", 0)) < 1:
                    continue
                name = str(info.get("name", f"Dispositivo {i}"))
                virt = any(h in name.lower() for h in VIRTUAL_HINTS)
                if info.get("isLoopbackDevice", False):
                    loops.append(AudioDevice(f"loopback:{name}", name, "loopback", i, virt))
                else:
                    ins.append(AudioDevice(f"input:{name}", name, "input", i, virt))
            devs += loops + ins
        devs.append(AudioDevice("demo", "demo", "demo", -2))
        return devs

    def _enumerate_sc(self) -> list[AudioDevice]:
        devs: list[AudioDevice] = []
        try:
            _sc.default_speaker()
            devs.append(AudioDevice("default_loopback", "default", "default_loopback", -1))
        except Exception:
            pass
        loops, ins = [], []
        for m in _sc.all_microphones(include_loopback=True):
            name = str(m.name)
            virt = any(h in name.lower() for h in VIRTUAL_HINTS)
            if getattr(m, "isloopback", False):
                loops.append(AudioDevice(f"loopback:{name}", name, "loopback", -1, virt))
            else:
                ins.append(AudioDevice(f"input:{name}", name, "input", -1, virt))
        return devs + loops + ins

    def _open_sc(self, dev):
        if dev.kind == "default_loopback":
            mic = _sc.get_microphone(str(_sc.default_speaker().name), include_loopback=True)
        else:
            want_loop = dev.kind == "loopback"
            mic = next((m for m in _sc.all_microphones(include_loopback=True)
                        if str(m.name) == dev.name and bool(getattr(m, "isloopback", False)) == want_loop), None)
        if mic is None:
            raise RuntimeError("Invalid device: no se encontró el dispositivo")
        stop = threading.Event()
        self._sc_stop = stop
        self._sc_err = None
        self._rate = 48000
        ring = self._ring

        def run():
            try:
                with mic.recorder(samplerate=48000, blocksize=1024) as rec:
                    while not stop.is_set():
                        d = np.asarray(rec.record(numframes=1024), np.float32)
                        if d.ndim > 1:
                            d = d.mean(axis=1)
                        ring.write(d)
            except Exception as exc:
                if not stop.is_set():
                    self._sc_err = exc

        self._sc_thread = threading.Thread(target=run, name="audio-capture", daemon=True)
        self._sc_thread.start()
        self._streaming = True
        self.status = f"Capturando: {dev.label}"
        self.is_error = False

    def _do_refresh(self, preferred_key=None):
        prev = self._selected
        self.status = "Actualizando dispositivos…"
        self.is_error = False
        self._close_stream()
        if self._pa is not None:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None
        try:
            self._devices = self._enumerate()
        except Exception as exc:
            self._devices = [AudioDevice("demo", "demo", "demo", -2)]
            self.status = f"No se pudieron listar los dispositivos: {exc}"
            self.is_error = True
        key = preferred_key or (prev.key if prev else None)
        found = next((d for d in self._devices if d.key == key), None)
        if found is None:
            found = self._devices[0]
        self._selected = found
        if self._want_running:
            self._open_selected()
        elif not self.is_error:
            self.status = f"{len(self._devices)} dispositivos encontrados."

    def _do_stop(self):
        self._close_stream()
        self._streaming = False
        self.status = "Audio detenido."
        self.is_error = False

    def _close_stream(self):
        self._streaming = False
        self._demo_stop.set()
        self._sc_stop.set()
        self._sc_thread = None
        st, self._stream = self._stream, None
        if st is not None:
            try:
                st.stop_stream()
            except Exception:
                pass
            try:
                st.close()
            except Exception:
                pass

    def _open_selected(self):
        dev = self._selected
        self._close_stream()
        if dev is None:
            if not self._devices:
                self._devices = self._enumerate()
            dev = self._selected = self._devices[0]
        if dev.kind == "demo":
            self._start_demo()
            return
        self.status = f"Conectando con «{dev.name}»…"
        self.is_error = False
        try:
            if pyaudio is None:
                if _sc is None:
                    raise RuntimeError(BACKEND_ERROR or "sin librería de audio")
                self._open_sc(dev)
                return
            pa = self._ensure_pa()
            idx = dev.index
            if dev.kind == "default_loopback":
                info = pa.get_default_wasapi_loopback()
            else:
                info = pa.get_device_info_by_index(idx)
            ch0 = max(1, int(info.get("maxInputChannels", 2)))
            rate0 = int(info.get("defaultSampleRate", 48000))
            attempts = [(ch0, rate0), (min(ch0, 2), rate0), (2, 48000), (2, 44100), (1, 48000), (1, 44100)]
            last = None
            for ch, rate in dict.fromkeys(attempts):
                try:
                    self._stream = pa.open(
                        format=pyaudio.paFloat32, channels=ch, rate=rate, input=True,
                        input_device_index=int(info["index"]), frames_per_buffer=1024,
                        stream_callback=self._make_callback(ch))
                    self._rate = rate
                    break
                except Exception as exc:
                    last = exc
                    self._stream = None
            if self._stream is None:
                raise last if last else RuntimeError("sin configuración válida")
            self._streaming = True
            self.status = f"Capturando: {dev.label}"
            self.is_error = False
        except Exception as exc:
            self._streaming = False
            self.status = _friendly_error(exc, dev.name)
            self.is_error = True

    def _make_callback(self, ch):
        ring = self._ring

        def cb(in_data, frame_count, time_info, status):
            try:
                x = np.frombuffer(in_data, dtype=np.float32)
                if ch > 1:
                    x = x[:(len(x) // ch) * ch].reshape(-1, ch).mean(axis=1)
                ring.write(x)
            except Exception:
                pass
            return (None, pyaudio.paContinue)
        return cb

    def _start_demo(self):
        self._demo_stop = threading.Event()
        stop = self._demo_stop
        self._rate = 44100
        synth = DemoSynth(44100)

        def run():
            n = 1024
            nxt = time.perf_counter()
            while not stop.is_set():
                self._ring.write(synth.block(n))
                nxt += n / 44100.0
                d = nxt - time.perf_counter()
                if d > 0:
                    time.sleep(d)
        threading.Thread(target=run, name="audio-demo", daemon=True).start()
        self._streaming = True
        self.status = "Capturando: señal de demostración sintética."
        self.is_error = False

    def _stream_alive(self):
        if self._sc_thread is not None:
            return self._sc_thread.is_alive() and self._sc_err is None
        st = self._stream
        if st is None:
            return False
        try:
            return bool(st.is_active())
        except Exception:
            return False

    def _watchdog(self, now):
        """Si el dispositivo se desconecta o el stream muere, reintenta cada pocos segundos."""
        if not self._want_running or self._busy or self._selected is None:
            return
        if self._selected.kind == "demo":
            return
        if not self._stream_alive() and now - self._last_try > 3.0:
            self._last_try = now
            if self._streaming or not self.is_error:
                self.status = "Dispositivo desconectado o en error. Reintentando…"
                self.is_error = True
            self._streaming = False
            self._run(self._do_refresh)

    def _loop(self):
        last = time.perf_counter()
        next_watch = last + 2.0
        zeros = np.zeros(Analyzer.N, np.float32)
        while not self._stop.is_set():
            now = time.perf_counter()
            dt = min(0.1, max(1e-3, now - last))
            last = now
            try:
                if self._streaming and now - self._ring.last_write < 0.15:
                    x = self._ring.latest(Analyzer.N)
                else:
                    x = zeros
                f = self._an.process(x, self._rate, dt, now)
                with self._flock:
                    self._feat = f
                if now >= next_watch:
                    next_watch = now + 1.0
                    self._watchdog(now)
            except Exception:
                pass
            time.sleep(0.008)
