"""Caller-owned buffers and typed Windows x64 DLL interface."""
import ctypes as C
from pathlib import Path
import time

class SfxParams(C.Structure):
    _fields_ = [('waveform', C.c_uint32)] + [(name,C.c_float) for name in (
        'base_freq','slide','min_freq','vib_depth','vib_rate','attack','sustain','decay','volume')] + [('seed',C.c_uint32)]

DEFAULTS = dict(waveform=0,base_freq=440,slide=0,min_freq=20,vib_depth=0,vib_rate=6,
                attack=.01,sustain=.1,decay=.3,volume=.5,seed=1)

class Engine:
    def __init__(self, path=None):
        if C.sizeof(C.c_void_p)!=8:
            raise RuntimeError('64-bit Python is required.')
        self.dll=C.CDLL(str(path or Path(__file__).resolve().parents[1]/'build/sfx.dll'))
        self.dll.sfx_sample_count.argtypes=[C.POINTER(SfxParams)]
        self.dll.sfx_generate.argtypes=[C.POINTER(SfxParams),C.POINTER(C.c_int16),C.c_uint32]
        self.dll.sfx_write_wav.argtypes=[C.POINTER(C.c_int16),C.c_uint32,C.c_void_p,C.c_uint32]
        for n in ('sfx_sample_count','sfx_generate','sfx_write_wav'):
            getattr(self.dll,n).restype=C.c_uint32
    def generate(self, values):
        p=SfxParams(**values)
        total=self.dll.sfx_sample_count(C.byref(p))
        if not total: raise ValueError('Invalid sound parameters.')
        samples=(C.c_int16*total)()
        start=time.perf_counter_ns()
        n=self.dll.sfx_generate(C.byref(p),samples,total)
        elapsed=(time.perf_counter_ns()-start)/1e6
        if not n: raise RuntimeError('Sound generation failed.')
        wav=C.create_string_buffer(44+2*n)
        size=self.dll.sfx_write_wav(samples,n,wav,len(wav))
        if not size: raise RuntimeError('WAV construction failed.')
        return list(samples[:n]),wav.raw[:size],elapsed
