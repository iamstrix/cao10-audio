"""Exercise real Tk widgets off screen. No audio output or visible window."""
import json
from pathlib import Path
import statistics
import sys
import threading
import time
from unittest.mock import patch
import tkinter as tk
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'gui'))
import app as ui
from presets import PRESETS,RANGES
root=tk.Tk();root.withdraw()
app=ui.App(root)
checks=0
def check(ok,label):
    global checks
    checks+=1
    if not ok:raise AssertionError(label)
def settle():
    deadline=time.monotonic()+5
    while app.pending is not None:
        root.update()
        if time.monotonic()>deadline:raise TimeoutError('GUI callback did not complete')
        time.sleep(.001)
    root.update_idletasks()
try:
    check(app.engine is not None,'engine loads')
    # An unmapped canvas reports one pixel. Use a fixed off-screen drawing area
    # so this test exercises 480 real Canvas columns while keeping the window hidden.
    app.canvas.winfo_width=lambda:480
    app.canvas.winfo_height=lambda:320
    for name,p in PRESETS.items():
        app.load(p,name);settle();check(app.wav==app.engine.generate(p)[1],'preset GUI binding')
        check(len(app.canvas.find_all())==481,'waveform canvas')
    for key,(lo,hi) in RANGES.items():
        for value in (lo,hi):
            app.vars[key].set(value);app.schedule();settle();check(app.wav is not None,'control limits')
    app.seed.set('0');app.schedule();settle();check(app.wav is None and 'Seed' in app.status.get(),'seed error displayed')
    app.load(PRESETS['Coin'],'Coin');settle()
    saved=ROOT/'results/gui-save.wav'
    with patch.object(ui.filedialog,'asksaveasfilename',return_value=str(saved)):
        app.save()
    check(saved.read_bytes()==app.wav,'Save writes current WAV')
    app.zoom.set(True);app.draw();check(len(app.canvas.find_all())==481,'waveform zoom')
    app.zoom.set(False)
    entered=threading.Event();release=threading.Event()
    def playback(data,flags):entered.set();release.wait(2)
    with patch.object(ui.winsound,'PlaySound',side_effect=playback):
        app.play();check(entered.wait(1),'playback worker started')
        ticks=[];root.after(0,lambda:ticks.append(1));root.update()
        check(ticks==[1] and app.playing,'UI responsive during mocked playback')
        release.set()
        deadline=time.monotonic()+2
        while app.playing and time.monotonic()<deadline:time.sleep(.001)
        check(not app.playing,'playback worker completed')
    # 100 maximum-length event-to-canvas cycles, including the 50 ms debounce.
    p=dict(PRESETS['Coin'],attack=2,sustain=2,decay=1,slide=0)
    app.load(p,'Maximum');settle()
    elapsed=[]
    for i in range(100):
        app.vars['volume'].set(.2+i/200)
        start=time.perf_counter();app.schedule();settle()
        elapsed.append((time.perf_counter()-start)*1000)
        check(len(app.samples)==220500,'maximum-length regeneration')
    p95=sorted(elapsed)[94]
    # Missing DLL keeps the application alive and explains recovery.
    other=tk.Toplevel(root);other.withdraw()
    with patch.object(ui,'Engine',side_effect=OSError('DLL unavailable')):
        missing=ui.App(other)
    check('unavailable' in missing.status.get(),'missing engine error')
    other.destroy()
    results=dict(status='PASS',checks=checks,canvas_columns=480,latency_runs=100,
                 maximum_sound_samples=220500,median_event_to_canvas_ms=statistics.median(elapsed),
                 p95_event_to_canvas_ms=p95,headless_latency_below_100ms=p95<100,
                 actual_audio_playback='Not assessed; playback API mocked',
                 visible_window_layout='Not assessed; window withdrawn',python=sys.version)
    (ROOT/'results/gui-headless.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results,indent=2))
finally:root.destroy()
