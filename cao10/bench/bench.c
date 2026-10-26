#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include "../ref/sfx.h"
typedef uint32_t (*Gen)(const SfxParams*,int16_t*,uint32_t);
static int16_t samples[44100];
static int cmp(const void*a,const void*b){double x=*(const double*)a,y=*(const double*)b;return (x>y)-(x<y);}
int main(void){
 const char *paths[]={"build/sfx.dll","build/sfx_ref.dll","build/sfx_ref_o0.dll"};
 const char *names[]={"Assembly","C O2","C O0"};LARGE_INTEGER frequency;
 QueryPerformanceFrequency(&frequency);printf("[\n");
 for(int impl=0;impl<3;impl++){
  HMODULE dll=LoadLibraryA(paths[impl]);if(!dll)return 1;
  Gen gen=(Gen)(void*)GetProcAddress(dll,"sfx_generate");if(!gen)return 1;
  for(int w=0;w<4;w++){
   SfxParams p={(uint32_t)w,440,1,20,.1f,6,0,1,0,.5f,1};
   for(int i=0;i<100;i++)if(gen(&p,samples,44100)!=44100)return 2;
   double elapsed[1000];
   for(int i=0;i<1000;i++){LARGE_INTEGER a,b;QueryPerformanceCounter(&a);uint32_t n=gen(&p,samples,44100);QueryPerformanceCounter(&b);if(n!=44100)return 2;elapsed[i]=(b.QuadPart-a.QuadPart)*1000.0/frequency.QuadPart;}
   qsort(elapsed,1000,sizeof(double),cmp);
   printf("{\"implementation\":\"%s\",\"waveform\":%d,\"median_ms\":%.6f,\"p95_ms\":%.6f}%s\n",names[impl],w,(elapsed[499]+elapsed[500])/2,elapsed[949],impl==2&&w==3?"":",");
  }
  FreeLibrary(dll);
 }
 printf("]\n");return 0;
}
