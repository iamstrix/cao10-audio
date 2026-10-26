#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "../ref/sfx.h"
typedef uint32_t (*Count)(const SfxParams*);
typedef uint32_t (*Gen)(const SfxParams*,int16_t*,uint32_t);
typedef uint32_t (*Wav)(const int16_t*,uint32_t,void*,uint32_t);
extern uint32_t abi_probe(void*,uintptr_t,uintptr_t,uintptr_t,uintptr_t);
static Count count;
static Gen gen,ref;
static Wav wav;
static int checks=0,max_delta=0;
static int16_t a[220500],b[220500];
static unsigned char guarded[441044+128];
static void check(int ok,const char *name) {checks++;if(!ok){fprintf(stderr,"FAIL: %s at check %d\n",name,checks);exit(1);}}
static uint32_t rng=0x51f15eed;
static uint32_t next(void){rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;return rng;}
static float uniform(float lo,float hi){return lo+(hi-lo)*(float)(next()&0xffffff)/16777216.f;}
static SfxParams base(void){SfxParams p={0,440,0,20,0,6,.01f,.1f,.3f,.5f,1};return p;}
static void compare(SfxParams *p){
 uint32_t n=gen(p,a,220500),m=ref(p,b,220500);
 check(n && n==m,"reference count");
 int delta=0;for(uint32_t i=0;i<n;i++){int d=abs((int)a[i]-b[i]);if(d>delta)delta=d;}
 if(delta>max_delta)max_delta=delta;
 check(delta<=1,"reference samples");
}
static void invalid(SfxParams *p){
 memset(guarded,0xcd,sizeof guarded);
 check(count(p)==0,"invalid count");
 check(gen(p,(int16_t*)(guarded+64),220500)==0,"invalid generation");
 for(unsigned i=0;i<sizeof guarded;i++)if(guarded[i]!=0xcd)check(0,"invalid wrote buffer");
 check(abi_probe((void*)gen,(uintptr_t)p,(uintptr_t)a,220500,0)==0,"invalid ABI");
 check(abi_probe((void*)count,(uintptr_t)p,0,0,0)==0,"invalid count ABI");
}
int main(void){
 HMODULE dll=LoadLibraryA("build/sfx.dll"),r=LoadLibraryA("build/sfx_ref.dll");
 check(dll && r,"load libraries");
 count=(Count)(void*)GetProcAddress(dll,"sfx_sample_count");gen=(Gen)(void*)GetProcAddress(dll,"sfx_generate");
 wav=(Wav)(void*)GetProcAddress(dll,"sfx_write_wav");ref=(Gen)(void*)GetProcAddress(r,"sfx_generate");
 check(count && gen && wav && ref,"exports");
 SfxParams p=base();
 /* Twenty fixed cases, five per waveform, including preset parameter shapes. */
 for(unsigned w=0;w<4;w++)for(unsigned k=0;k<5;k++){
   p=base();p.waveform=w;p.base_freq=300+350*k;p.slide=(float)k-2;
   p.vib_depth=.025f*k;p.attack=.005f*k;p.seed=1+k;
   if(w==0 && k<4){
     p=base();p.attack=0;
     if(k==0){p.base_freq=988;p.slide=2;p.sustain=.05f;p.decay=.25f;}
     if(k==1){p.base_freq=300;p.slide=2;p.sustain=.05f;p.decay=.2f;}
     if(k==2){p.base_freq=400;p.slide=1.5f;p.vib_depth=.1f;p.vib_rate=12;p.sustain=.2f;p.decay=.3f;}
     if(k==3){p.base_freq=1500;p.sustain=.03f;p.decay=.05f;p.volume=.4f;}
   }
   if(w==1 && k==0){p=base();p.waveform=1;p.base_freq=1200;p.slide=-3.5f;p.min_freq=100;p.attack=0;p.sustain=.05f;p.decay=.15f;p.volume=.4f;}
   if(w==3 && k<2){p=base();p.waveform=3;p.attack=0;p.volume=.6f;
     if(k==0){p.base_freq=2000;p.slide=-1.5f;p.min_freq=50;p.sustain=.1f;p.decay=.8f;}
     if(k==1){p.base_freq=3000;p.slide=-3;p.min_freq=100;p.sustain=.02f;p.decay=.15f;}
   }
   compare(&p);
 }
 for(unsigned i=0;i<10000;i++){
   p=base();p.waveform=next()%4;p.base_freq=uniform(20,4000);p.min_freq=uniform(20,fminf(1000,p.base_freq));
   p.slide=uniform(-4,4);p.vib_depth=uniform(0,.5f);p.vib_rate=uniform(0,30);
   p.attack=uniform(0,.5f);p.sustain=uniform(0,.5f);p.decay=uniform(0,.8f);p.volume=uniform(0,1);p.seed=next()|1;
   compare(&p);
   if(p.slide>=0)check(count(&p)==gen(&p,a,220500),"planned equals actual");
 }
 p=base();compare(&p);uint32_t n=count(&p);memcpy(b,a,n*2);
 for(unsigned i=0;i<1000;i++){check(gen(&p,a,220500)==n,"repeat count");check(!memcmp(a,b,n*2),"determinism");}
 static const float lows[9]={20,-4,20,0,0,0,0,0,0};
 static const float highs[9]={4000,4,1000,.5f,30,2,2,3,1};
 for(unsigned field=0;field<9;field++){
   float values[]={lows[field]-1,highs[field]+1,NAN,INFINITY,-INFINITY};
   for(unsigned j=0;j<5;j++){p=base();memcpy((unsigned char*)&p+4+field*4,&values[j],4);invalid(&p);}
 }
 invalid(NULL);p=base();p.waveform=4;invalid(&p);p=base();p.seed=0;invalid(&p);
 p=base();p.attack=p.sustain=p.decay=0;invalid(&p);
 p=base();p.attack=2;p.sustain=2;p.decay=3;invalid(&p);
 p=base();p.min_freq=500;invalid(&p);
 p=base();p.attack=2;p.sustain=2;p.decay=1.f+1.f/44100.f;invalid(&p);
 p=base();n=count(&p);
 for(int shift=-1;shift<=1;shift++){
   memset(guarded,0xcd,sizeof guarded);
   uint32_t m=gen(&p,(int16_t*)(guarded+64),n+shift);
   check(shift<0?m==0:m==n,"capacity count");
   for(unsigned i=0;i<64;i++)check(guarded[i]==0xcd,"prefix guard");
   for(unsigned i=64+(shift<0?0:n*2);i<sizeof guarded;i++)check(guarded[i]==0xcd,"suffix guard");
 }
 check(gen(&p,NULL,220500)==0,"NULL samples");
 check(abi_probe((void*)count,(uintptr_t)&p,0,0,0)==0,"count ABI success");
 check(abi_probe((void*)count,0,0,0,0)==0,"count ABI error");
 check(abi_probe((void*)gen,(uintptr_t)&p,(uintptr_t)a,220500,0)==0,"generate ABI success");
 check(abi_probe((void*)gen,(uintptr_t)&p,0,220500,0)==0,"generate ABI null");
 check(abi_probe((void*)gen,(uintptr_t)&p,(uintptr_t)a,0,0)==0,"generate ABI capacity");
 p=base();p.base_freq=441;p.attack=p.decay=0;p.sustain=1;p.volume=1;n=gen(&p,a,220500);
 unsigned cycles=0;int min=32767,max=-32768;
 for(unsigned i=0;i<n;i++){if(i && a[i-1]<0 && a[i]>0)cycles++;if(a[i]<min)min=a[i];if(a[i]>max)max=a[i];}
 check(cycles==440 || cycles==441,"441 Hz cycle count");check(min==-32767 && max==32767,"full scale");
 unsigned last=0,periods=0;
 for(unsigned i=1;i<n;i++)if(a[i-1]<0 && a[i]>0){if(periods)check(i-last>=99 && i-last<=101,"441 Hz periods");last=i;periods++;}
 p=base();p.attack=0;p.sustain=1;p.decay=0;p.waveform=1;p.slide=1;n=gen(&p,a,220500);
 last=0;unsigned prev=0;for(unsigned i=1;i<n;i++)if(a[i]<a[i-1]){prev=last;last=i;}
 check(fabs(44100.0/(last-prev)-880)<8.8,"up slide frequency");
 p=base();p.base_freq=1000;p.slide=-4;p.min_freq=100;p.attack=0;p.sustain=1;p.decay=0;
 n=gen(&p,a,220500);check(fabs(n-36625.0)<367,"down slide cutoff");
 p=base();p.min_freq=p.base_freq;p.slide=-4;check(gen(&p,a,220500)==1,"first sample cutoff");
 p=base();p.base_freq=4000;p.slide=4;p.attack=2;p.sustain=2;p.decay=1;compare(&p);check(count(&p)==220500,"maximum duration");
 unsigned sizes[]={1,44100,220500};
 for(unsigned j=0;j<3;j++){
   n=sizes[j];memset(guarded,0xcd,sizeof guarded);uint32_t bytes=44+n*2;
   check(wav(a,n,guarded+64,bytes-1)==0,"WAV short capacity");
   for(unsigned i=0;i<sizeof guarded;i++)if(guarded[i]!=0xcd)check(0,"WAV short wrote");
   check(wav(a,n,guarded+64,bytes)==bytes,"WAV count");
   unsigned char expected[44]={'R','I','F','F',0,0,0,0,'W','A','V','E','f','m','t',' ',16,0,0,0,1,0,1,0,0x44,0xac,0,0,0x88,0x58,1,0,2,0,16,0,'d','a','t','a',0,0,0,0};
   uint32_t v=36+n*2;memcpy(expected+4,&v,4);v=n*2;memcpy(expected+40,&v,4);
   check(!memcmp(expected,guarded+64,44),"WAV complete header");check(!memcmp(a,guarded+108,n*2),"WAV payload");
   for(unsigned i=0;i<64;i++)check(guarded[i]==0xcd && guarded[64+bytes+i]==0xcd,"WAV guards");
 }
 check(wav(NULL,1,guarded,sizeof guarded)==0,"WAV null input");
 check(wav(a,1,NULL,sizeof guarded)==0,"WAV null output");
 check(wav(a,0,guarded,sizeof guarded)==0,"WAV zero");
 check(wav(a,220501,guarded,sizeof guarded)==0,"WAV excess count");
 check(abi_probe((void*)wav,(uintptr_t)a,1,(uintptr_t)guarded,sizeof guarded)==0,"WAV ABI success");
 check(abi_probe((void*)wav,0,1,(uintptr_t)guarded,sizeof guarded)==0,"WAV ABI null input");
 check(abi_probe((void*)wav,(uintptr_t)a,1,0,sizeof guarded)==0,"WAV ABI null output");
 check(abi_probe((void*)wav,(uintptr_t)a,0,(uintptr_t)guarded,sizeof guarded)==0,"WAV ABI zero");
 check(abi_probe((void*)wav,(uintptr_t)a,220501,(uintptr_t)guarded,sizeof guarded)==0,"WAV ABI excess");
 check(abi_probe((void*)wav,(uintptr_t)a,1,(uintptr_t)guarded,0)==0,"WAV ABI short");
 printf("{\"checks\":%d,\"fixed_cases\":20,\"random_cases\":10000,\"determinism_runs\":1000,\"maximum_sample_delta\":%d,\"status\":\"PASS\"}\n",checks,max_delta);
 return 0;
}
