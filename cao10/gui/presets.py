import random
from sfx_binding import DEFAULTS

RANGES = dict(base_freq=(20,4000),slide=(-4,4),min_freq=(20,1000),vib_depth=(0,.5),
              vib_rate=(0,30),attack=(0,2),sustain=(0,2),decay=(0,3),volume=(0,1))
PRESETS={}
for name,wave,base,slide,minimum,depth,vr,sustain,decay,vol in [
    ('Coin',0,988,2,20,0,6,.05,.25,.5),('Laser',1,1200,-3.5,100,0,6,.05,.15,.4),
    ('Explosion',3,2000,-1.5,50,0,6,.1,.8,.6),('Jump',0,300,2,20,0,6,.05,.2,.5),
    ('Hit',3,3000,-3,100,0,6,.02,.15,.6),('Power-Up',0,400,1.5,20,.1,12,.2,.3,.5),
    ('Blip',0,1500,0,20,0,6,.03,.05,.4)]:
    PRESETS[name]=dict(DEFAULTS,waveform=wave,base_freq=base,slide=slide,min_freq=minimum,
                       vib_depth=depth,vib_rate=vr,attack=0,sustain=sustain,decay=decay,volume=vol)

def constrain(values):
    p=dict(values)
    p['min_freq']=min(p['min_freq'],p['base_freq'])
    total=sum(p[x] for x in ('attack','sustain','decay'))
    if total>5:
        for x in ('attack','sustain','decay'): p[x]*=5/total
    if sum(int(p[x]*44100) for x in ('attack','sustain','decay'))==0:
        p['decay']=.001
    return p

def randomize(rng=None):
    rng=rng or random
    p=dict(DEFAULTS,**{k:rng.uniform(*v) for k,v in RANGES.items()})
    p.update(waveform=rng.randrange(4),seed=rng.randint(1,0xffffffff))
    total=p['attack']+p['sustain']+p['decay']
    if total>2:
        for x in ('attack','sustain','decay'): p[x]*=2/total
    return constrain(p)

def waveform_columns(samples,width):
    """Peak-preserving min/max binning, also usable without a Tk display."""
    if not samples or width<1: return []
    n=len(samples)
    return [(min(samples[i*n//width:max(i*n//width+1,(i+1)*n//width)]),
             max(samples[i*n//width:max(i*n//width+1,(i+1)*n//width)])) for i in range(width)]
