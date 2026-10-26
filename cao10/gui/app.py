"""Launch with 64-bit Python: python gui/app.py. Standard library only."""
from pathlib import Path
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import winsound
from sfx_binding import Engine, DEFAULTS
from presets import PRESETS,RANGES,constrain,randomize,waveform_columns

class App:
    def __init__(self,root):
        self.root=root; root.title('CA010 Procedural Game SFX Generator')
        root.geometry('980x760'); root.minsize(820,700)
        self.engine=None; self.wav=None; self.samples=[]; self.name='Custom'
        self.pending=None; self.loading=False; self.playing=False
        self.vars={k:tk.DoubleVar(value=v) for k,v in DEFAULTS.items() if k not in ('waveform','seed')}
        self.wave=tk.StringVar(value='Square'); self.seed=tk.StringVar(value='1')
        self.auto=tk.BooleanVar(value=False); self.zoom=tk.BooleanVar(value=False)
        main=ttk.Frame(root,padding=16); main.pack(fill='both',expand=True)
        ttk.Label(main,text='Procedural Game Sound Effects',font=('Segoe UI',18,'bold')).pack(anchor='w')
        bar=ttk.Frame(main); bar.pack(fill='x',pady=12)
        for name in PRESETS: ttk.Button(bar,text=name,command=lambda n=name:self.load(PRESETS[n],n)).pack(side='left',padx=2)
        ttk.Button(bar,text='Randomize',command=lambda:self.load(randomize(),'Random')).pack(side='left',padx=2)
        body=ttk.Frame(main); body.pack(fill='both',expand=True)
        controls=ttk.Frame(body); controls.pack(side='left',fill='y',padx=(0,20))
        ttk.Label(controls,text='Waveform').grid(row=0,column=0,sticky='w')
        combo=ttk.Combobox(controls,textvariable=self.wave,values=['Square','Sawtooth','Triangle','Noise'],state='readonly',width=15)
        combo.grid(row=0,column=1); combo.bind('<<ComboboxSelected>>',self.schedule)
        labels={'base_freq':'Starting pitch (Hz)','slide':'Pitch slide (octaves/s)','min_freq':'Minimum pitch (Hz)',
                'vib_depth':'Vibrato depth','vib_rate':'Vibrato rate (Hz)','attack':'Attack (s)',
                'sustain':'Sustain (s)','decay':'Decay (s)','volume':'Volume'}
        for row,(key,limits) in enumerate(RANGES.items(),1):
            ttk.Label(controls,text=labels[key]).grid(row=row*2-1,column=0,sticky='w',pady=(7,0))
            ttk.Label(controls,textvariable=self.vars[key],width=16).grid(row=row*2-1,column=1)
            ttk.Scale(controls,from_=limits[0],to=limits[1],variable=self.vars[key],command=self.schedule,length=300).grid(row=row*2,column=0,columnspan=2,sticky='ew')
        ttk.Label(controls,text='Noise seed').grid(row=19,column=0,sticky='w',pady=10)
        entry=ttk.Entry(controls,textvariable=self.seed,width=16); entry.grid(row=19,column=1)
        entry.bind('<KeyRelease>',self.schedule)
        right=ttk.Frame(body); right.pack(side='left',fill='both',expand=True)
        self.canvas=tk.Canvas(right,bg='#101820',highlightthickness=0,height=320)
        self.canvas.pack(fill='both',expand=True); self.canvas.bind('<Configure>',lambda e:self.draw())
        ttk.Checkbutton(right,text='Zoom to first 20 ms',variable=self.zoom,command=self.draw).pack(anchor='w',pady=8)
        actions=ttk.Frame(right); actions.pack(fill='x',pady=10)
        ttk.Button(actions,text='Play',command=self.play).pack(side='left',padx=4)
        ttk.Button(actions,text='Save WAV',command=self.save).pack(side='left',padx=4)
        ttk.Checkbutton(right,text='Auto-play on change',variable=self.auto).pack(anchor='w')
        self.status=tk.StringVar(value='Loading engine…')
        ttk.Label(main,textvariable=self.status,wraplength=880).pack(anchor='w',pady=(12,0))
        try: self.engine=Engine(); self.regenerate()
        except (OSError,RuntimeError) as exc: self.status.set(f'Engine unavailable: {exc}. Run build.bat and restart.')
    def schedule(self,*args):
        if self.loading:return
        if self.pending:self.root.after_cancel(self.pending)
        self.pending=self.root.after(50,self.regenerate)
    def load(self,p,name):
        self.loading=True
        for k,v in self.vars.items():v.set(p[k])
        self.wave.set(['Square','Sawtooth','Triangle','Noise'][p['waveform']]);self.seed.set(str(p['seed']))
        self.loading=False;self.name=name;self.schedule()
    def regenerate(self):
        self.pending=None
        if not self.engine:return
        try:
            seed=int(self.seed.get())
            if not 1<=seed<=0xffffffff:raise ValueError('Seed must be between 1 and 4294967295.')
            p=constrain(dict({k:v.get() for k,v in self.vars.items()},waveform=['Square','Sawtooth','Triangle','Noise'].index(self.wave.get()),seed=seed))
            self.loading=True
            for k,v in self.vars.items():v.set(round(p[k],6))
            self.loading=False
            self.samples,self.wav,ms=self.engine.generate(p)
            self.draw();self.status.set(f'{len(self.samples)/44100:.3f} s, {len(self.samples):,} samples, generated in {ms:.3f} ms')
            if self.auto.get():self.play()
        except (ValueError,RuntimeError,tk.TclError) as exc:
            self.loading=False;self.wav=None;self.samples=[];self.draw();self.status.set(str(exc))
    def draw(self):
        self.canvas.delete('all');w=max(1,self.canvas.winfo_width());h=max(1,self.canvas.winfo_height())
        self.canvas.create_line(0,h/2,w,h/2,fill='#425565')
        s=self.samples[:882] if self.zoom.get() else self.samples
        for x,(lo,hi) in enumerate(waveform_columns(s,w)):
            self.canvas.create_line(x,h/2-hi/32768*(h*.45),x,h/2-lo/32768*(h*.45)+1,fill='#58dbbc')
    def play(self):
        if not self.wav or self.playing:return
        wav=self.wav;self.playing=True
        def work():
            try:winsound.PlaySound(wav,winsound.SND_MEMORY)
            except RuntimeError:pass
            finally:self.playing=False
        threading.Thread(target=work,daemon=True).start()
    def save(self):
        if not self.wav:return
        path=filedialog.asksaveasfilename(defaultextension='.wav',filetypes=[('WAV audio','*.wav')],initialfile=f'{self.name}_{self.seed.get()}.wav')
        if path:
            try:Path(path).write_bytes(self.wav)
            except OSError as exc:messagebox.showerror('Save failed',str(exc))

if __name__=='__main__':App(tk.Tk());tk.mainloop()
