"""Headless binding, presets, concurrency, WAV and waveform checks."""
import concurrent.futures
import ctypes as C
import io
import json
from pathlib import Path
import random
import struct
import subprocess
import sys
import time
import wave
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'gui'))
from sfx_binding import Engine,SfxParams,DEFAULTS
from presets import PRESETS,randomize,constrain,waveform_columns

def run():
    engine=Engine(); reference=Engine(ROOT/'build/sfx_ref.dll'); checks=0
    def check(condition,label):
        nonlocal checks
        checks+=1
        if not condition:raise AssertionError(label)
    check(C.sizeof(SfxParams)==44,'ABI size')
    for i,(name,_) in enumerate(SfxParams._fields_):check(getattr(SfxParams,name).offset==i*4,'ABI field offset')
    results=ROOT/'results';(results/'presets').mkdir(parents=True,exist_ok=True)
    preset_results=[]
    for name,p in PRESETS.items():
        samples,data,ms=engine.generate(p)
        check(samples==reference.generate(p)[0],'preset C comparison')
        with wave.open(io.BytesIO(data),'rb') as wav:
            check((wav.getframerate(),wav.getnchannels(),wav.getsampwidth(),wav.getnframes())==(44100,1,2,len(samples)),'WAV format')
            check(wav.readframes(len(samples))==struct.pack(f'<{len(samples)}h',*samples),'WAV content')
        (results/'presets'/f'{name}.wav').write_bytes(data)
        check(data==engine.generate(p)[1],'preset repeatability')
        preset_results.append(dict(preset=name,samples=len(samples),duration_s=len(samples)/44100,wav_bytes=len(data)))
    rng=random.Random(20261026)
    for i in range(1000):
        p=randomize(rng);s,data,ms=engine.generate(p)
        check(0<len(s)<=88200,'Randomize valid and short')
    # Concurrent calls exercise the same DLL and binding without global engine state.
    p=dict(PRESETS['Explosion'])
    expected=engine.generate(p)[1]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        outputs=list(pool.map(lambda _:engine.generate(p)[1],range(100)))
    check(all(x==expected for x in outputs),'reentrant generation')
    q=dict(p,seed=2);check(engine.generate(q)[1]!=expected,'seed changes noise')
    check(waveform_columns([-32767,32767,0,100],2)==[(-32767,32767),(0,100)],'waveform peaks')
    check(waveform_columns([],100)==[],'empty waveform')
    check(constrain(dict(DEFAULTS,attack=0,sustain=0,decay=0))['decay']>0,'zero duration constrained')
    check(constrain(dict(DEFAULTS,base_freq=20,min_freq=100))['min_freq']==20,'frequency constraint')
    try:engine.generate(dict(DEFAULTS,seed=0))
    except ValueError:check(True,'binding invalid parameters')
    else:check(False,'binding accepted seed zero')
    try:Engine(ROOT/'build/missing.dll')
    except OSError:check(True,'missing DLL exception')
    else:check(False,'missing DLL unexpectedly loaded')
    # Parse PE directories and sections without an external dependency.
    dll=(ROOT/'build/sfx.dll').read_bytes(); pe=struct.unpack_from('<I',dll,0x3c)[0]
    nsections=struct.unpack_from('<H',dll,pe+6)[0];opt_size=struct.unpack_from('<H',dll,pe+20)[0]
    optional=pe+24;exports_rva,export_size,imports_rva,imports_size=struct.unpack_from('<IIII',dll,optional+112)
    sections=[]
    for i in range(nsections):
        offset=optional+opt_size+40*i
        name=dll[offset:offset+8].split(b'\0')[0].decode()
        vsize,rva,rawsize,raw=struct.unpack_from('<IIII',dll,offset+8)
        flags=struct.unpack_from('<I',dll,offset+36)[0]
        sections.append(dict(name=name,rva=rva,raw=raw,size=max(vsize,rawsize),writable=bool(flags&0x80000000)))
    def raw(rva):
        for section in sections:
            if section['rva']<=rva<section['rva']+section['size']:return section['raw']+rva-section['rva']
        raise ValueError('Unmapped RVA')
    ed=raw(exports_rva);nf,nn,addr,names,ordinals=struct.unpack_from('<IIIII',dll,ed+20)
    exported=[]
    for i in range(nn):
        ptr=raw(struct.unpack_from('<I',dll,raw(names)+4*i)[0]);exported.append(dll[ptr:dll.index(0,ptr)].decode())
    check(sorted(exported)==['sfx_generate','sfx_sample_count','sfx_write_wav'] and nf==3,'exact exports')
    # GNU ld may emit a read-only .idata containing just the null descriptor.
    imports=[]
    if imports_rva:
        offset=raw(imports_rva)
        while any(dll[offset:offset+20]):
            name_rva=struct.unpack_from('<I',dll,offset+12)[0]
            pos=raw(name_rva);imports.append(dll[pos:dll.index(0,pos)].decode());offset+=20
    check(not imports,'no imported DLLs')
    check(not any(s['writable'] for s in sections),'no writable sections')
    check(len(dll)<20480,'DLL size')
    data=dict(status='PASS',checks=checks,randomize_runs=1000,concurrent_runs=100,dll_bytes=len(dll),
              exports=exported,imports=imports,import_directory_bytes=imports_size,sections=sections,presets=preset_results,
              gui_visual_and_playback='Not assessed by headless tests')
    (results/'headless.json').write_text(json.dumps(data,indent=2))
    print(json.dumps(data,indent=2))

if __name__=='__main__':run()
