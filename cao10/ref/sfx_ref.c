#include "sfx.h"
#include <stddef.h>
#include <xmmintrin.h>
#include "sine_table.h"
static const float lo[9]={20,-4,20,0,0,0,0,0,0};
static const float hi[9]={4000,4,1000,.5f,30,2,2,3,1};
uint32_t sfx_sample_count(const SfxParams *p) {
    if (!p || p->waveform>3 || !p->seed) return 0;
    /* Copy through bytes to avoid aliasing or assuming an array of struct fields. */
    for (unsigned i=0;i<9;i++) {
        union { uint32_t u; float f; } v;
        const unsigned char *b=(const unsigned char*)p+4+4*i;
        v.u=(uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24;
        if (!(v.f>=lo[i] && v.f<=hi[i])) return 0;
    }
    if(p->min_freq>p->base_freq) return 0;
    uint32_t n=(uint32_t)(p->attack*44100.f)+(uint32_t)(p->sustain*44100.f)+(uint32_t)(p->decay*44100.f);
    return n>=1 && n<=220500 ? n : 0;
}
static uint32_t next(uint32_t x) { x^=x<<13; x^=x>>17; x^=x<<5; return x; }
static float noise_float(uint32_t x) { return (float)(int32_t)x*0x1p-31f; }
uint32_t sfx_generate(const SfxParams *p,int16_t *out,uint32_t capacity) {
    uint32_t total=sfx_sample_count(p);
    if(!total || !out || capacity<total) return 0;
    uint32_t a=(uint32_t)(p->attack*44100.f), as=a+(uint32_t)(p->sustain*44100.f);
    uint32_t d=(uint32_t)(p->decay*44100.f), state=next(p->seed);
    float noise=noise_float(state), phase=0, vp=0, freq=p->base_freq;
    float step=p->vib_rate/44100.f, y=(p->slide/44100.f)*.69314718f;
    float mult=(1.f+y)+((.5f*y)*y);
    for(uint32_t n=0;n<total;n++) {
        freq=freq*mult; if(freq>20000.f) freq=20000.f;
        if(n && freq<p->min_freq) return n;
        union {uint32_t u;float f;} sine={sine_bits[((uint32_t)(vp*256.f))&255]};
        float vib=1.f+p->vib_depth*sine.f;
        vp=vp+step; if(vp>=1.f) vp=vp-1.f;
        phase=phase+(freq*vib)/44100.f;
        if(phase>=1.f) {phase=phase-1.f; state=next(state); noise=noise_float(state);}
        float s;
        if(p->waveform==0) s=phase<.5f?1.f:-1.f;
        else if(p->waveform==1) s=2.f*phase-1.f;
        else if(p->waveform==2) { float t=phase-.5f; if(t<0) t=-t; s=1.f-4.f*t; }
        else s=noise;
        float gain=n<a?(float)n/(float)a:n<as?1.f:1.f-(float)(n-as)/(float)d;
        int v=_mm_cvtss_si32(_mm_set_ss(((s*gain)*p->volume)*32767.f));
        if(v>32767) v=32767;
        if(v< -32768) v=-32768;
        out[n]=(int16_t)v;
    }
    return total;
}
uint32_t sfx_write_wav(const int16_t *samples,uint32_t n,void *output,uint32_t cap) {
    static const unsigned char header[44]={'R','I','F','F',0,0,0,0,'W','A','V','E','f','m','t',' ',16,0,0,0,1,0,1,0,0x44,0xac,0,0,0x88,0x58,1,0,2,0,16,0,'d','a','t','a',0,0,0,0};
    if(!samples || !output || !n || n>220500 || cap<44+2*n) return 0;
    unsigned char *out=output; uint32_t size=2*n, riff=36+size;
    for(unsigned i=0;i<44;i++) out[i]=header[i];
    for(unsigned i=0;i<4;i++) {out[4+i]=(unsigned char)(riff>>(8*i));out[40+i]=(unsigned char)(size>>(8*i));}
    for(unsigned i=0;i<size;i++) out[44+i]=((const unsigned char*)samples)[i];
    return 44+size;
}
