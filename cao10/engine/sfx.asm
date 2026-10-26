bits 64
default rel
global sfx_sample_count, sfx_generate, sfx_write_wav
struc SfxParams
 .waveform: resd 1
 .base_freq: resd 1
 .slide: resd 1
 .min_freq: resd 1
 .vib_depth: resd 1
 .vib_rate: resd 1
 .attack: resd 1
 .sustain: resd 1
 .decay: resd 1
 .volume: resd 1
 .seed: resd 1
endstruc
section .rdata align=16
one: dd 1.0
half: dd 0.5
two: dd 2.0
four: dd 4.0
rate: dd 44100.0
ln2: dd 0.69314718
maxfreq: dd 20000.0
scale: dd 32767.0
noisescale: dd 0x30000000 ; 2^-31
table_size: dd 256.0
align 16
absmask: dd 0x7fffffff,0xffffffff,0xffffffff,0xffffffff
low: dd 20.0,-4.0,20.0,0.0,0.0,0.0,0.0,0.0,0.0
high: dd 4000.0,4.0,1000.0,0.5,30.0,2.0,2.0,3.0,1.0
sine:
%include "engine/sine_table.inc"
header: db 'RIFF'
 dd 0
 db 'WAVEfmt '
 dd 16
 dw 1,1
 dd 44100,88200
 dw 2,16
 db 'data'
 dd 0
section .text
; Input RCX=params. Output EAX=planned samples, zero on invalid input.
; Clobbers RAX,RDX,R8,R9,R10,XMM0,XMM1. No stack or nonvolatile use.
sfx_sample_count:
 xor eax,eax
 test rcx,rcx
 jz .bad
 cmp dword [rcx+SfxParams.waveform],3
 ja .bad
 cmp dword [rcx+SfxParams.seed],0
 je .bad
 lea r9,[low]
 lea r10,[high]
 xor r8d,r8d
.validate:
 movss xmm0,[rcx+r8*4+4]
 comiss xmm0,[r9+r8*4]
 jp .bad
 jb .bad
 comiss xmm0,[r10+r8*4]
 ja .bad
 inc r8d
 cmp r8d,9
 jb .validate
 movss xmm0,[rcx+SfxParams.min_freq]
 comiss xmm0,[rcx+SfxParams.base_freq]
 ja .bad
 movss xmm0,[rcx+SfxParams.attack]
 mulss xmm0,[rate]
 cvttss2si eax,xmm0
 movss xmm0,[rcx+SfxParams.sustain]
 mulss xmm0,[rate]
 cvttss2si edx,xmm0
 add eax,edx
 movss xmm0,[rcx+SfxParams.decay]
 mulss xmm0,[rate]
 cvttss2si edx,xmm0
 add eax,edx
 test eax,eax
 jz .bad
 cmp eax,220500
 ja .bad
 ret
.bad:
 xor eax,eax
 ret
; Generate RCX=params, RDX=int16 output, R8D=capacity. EAX=count or zero.
; Clobbers volatile registers only. 152-byte frame including 32-byte shadow.
; Loop map: RCX=params,RDX=out,R8D=n,R9D=PRNG,R10/R11=scratch.
; XMM0=temporary/sample,XMM1=gain,XMM2=temporary,XMM3=phase,
; XMM4=frequency,XMM5=vibrato phase. Persistent scalars in stack slots.
%define P 32
%define OUT 40
%define CAP 48
%define TOTAL 52
%define A 56
%define AS 60
%define D 64
%define STEP 68
%define MULT 72
%define NOISE 76
sfx_generate:
generate_begin:
 sub rsp,152
generate_prologue_end:
 mov [rsp+P],rcx
 mov [rsp+OUT],rdx
 mov [rsp+CAP],r8d
 call sfx_sample_count
 test eax,eax
 jz .error
 cmp [rsp+CAP],eax
 jb .error
 cmp qword [rsp+OUT],0
 je .error
 mov [rsp+TOTAL],eax
 mov rcx,[rsp+P]
 mov rdx,[rsp+OUT]
 movss xmm0,[rcx+SfxParams.attack]
 mulss xmm0,[rate]
 cvttss2si eax,xmm0
 mov [rsp+A],eax
 movss xmm0,[rcx+SfxParams.sustain]
 mulss xmm0,[rate]
 cvttss2si r10d,xmm0
 add eax,r10d
 mov [rsp+AS],eax
 movss xmm0,[rcx+SfxParams.decay]
 mulss xmm0,[rate]
 cvttss2si eax,xmm0
 mov [rsp+D],eax
 movss xmm0,[rcx+SfxParams.vib_rate]
 divss xmm0,[rate]
 movss [rsp+STEP],xmm0
 movss xmm0,[rcx+SfxParams.slide]
 divss xmm0,[rate]
 mulss xmm0,[ln2]
 movss xmm1,xmm0
 mulss xmm1,[half]
 mulss xmm1,xmm0
 addss xmm0,[one]
 addss xmm0,xmm1
 movss [rsp+MULT],xmm0
 mov r9d,[rcx+SfxParams.seed]
 call noise_next
 movss [rsp+NOISE],xmm0
 xorps xmm3,xmm3
 xorps xmm5,xmm5
 movss xmm4,[rcx+SfxParams.base_freq]
 xor r8d,r8d
.loop:
 mulss xmm4,[rsp+MULT]
 minss xmm4,[maxfreq]
 test r8d,r8d
 jz .vibrato
 comiss xmm4,[rcx+SfxParams.min_freq]
 jb .done
.vibrato:
 movss xmm0,xmm5
 mulss xmm0,[table_size]
 cvttss2si r10d,xmm0
 and r10d,255
 lea r11,[sine]
 movss xmm0,[r11+r10*4]
 mulss xmm0,[rcx+SfxParams.vib_depth]
 addss xmm0,[one]
 addss xmm5,[rsp+STEP]
 comiss xmm5,[one]
 jb .phase
 subss xmm5,[one]
.phase:
 mulss xmm0,xmm4
 divss xmm0,[rate]
 addss xmm3,xmm0
 comiss xmm3,[one]
 jb .wave
 subss xmm3,[one]
 call noise_next
 movss [rsp+NOISE],xmm0
.wave:
 mov eax,[rcx+SfxParams.waveform]
 test eax,eax
 jz .square
 cmp eax,1
 je .saw
 cmp eax,2
 je .triangle
 movss xmm0,[rsp+NOISE]
 jmp .gain
.square:
 movss xmm0,[one]
 comiss xmm3,[half]
 jb .gain
 xorps xmm0,xmm0
 subss xmm0,[one]
 jmp .gain
.saw:
 movss xmm0,xmm3
 mulss xmm0,[two]
 subss xmm0,[one]
 jmp .gain
.triangle:
 movss xmm2,xmm3
 subss xmm2,[half]
 andps xmm2,[absmask]
 mulss xmm2,[four]
 movss xmm0,[one]
 subss xmm0,xmm2
.gain:
 cmp r8d,[rsp+A]
 jb .attack
 movss xmm1,[one]
 cmp r8d,[rsp+AS]
 jb .quantize
 mov eax,r8d
 sub eax,[rsp+AS]
 cvtsi2ss xmm2,eax
 cvtsi2ss xmm1,dword [rsp+D]
 divss xmm2,xmm1
 movss xmm1,[one]
 subss xmm1,xmm2
 jmp .quantize
.attack:
 cvtsi2ss xmm1,r8d
 cvtsi2ss xmm2,dword [rsp+A]
 divss xmm1,xmm2
.quantize:
 mulss xmm0,xmm1
 mulss xmm0,[rcx+SfxParams.volume]
 mulss xmm0,[scale]
 cvtss2si eax,xmm0
 movd xmm0,eax
 packssdw xmm0,xmm0
 movd eax,xmm0
 mov [rdx+r8*2],ax
 inc r8d
 cmp r8d,[rsp+TOTAL]
 jb .loop
.done:
 mov eax,r8d
 add rsp,152
 ret
.error:
 xor eax,eax
 add rsp,152
 ret
generate_end:
; Internal leaf: R9D=state in/out, XMM0=noise out; R10D scratch.
noise_next:
 mov r10d,r9d
 shl r10d,13
 xor r9d,r10d
 mov r10d,r9d
 shr r10d,17
 xor r9d,r10d
 mov r10d,r9d
 shl r10d,5
 xor r9d,r10d
 cvtsi2ss xmm0,r9d
 mulss xmm0,[noisescale]
 ret
; RCX=samples, EDX=count,R8=output,R9D=byte capacity. EAX=bytes or zero.
; Clobbers RAX,RDX,R9,R10,R11 only. No stack or nonvolatile use.
sfx_write_wav:
 xor eax,eax
 test rcx,rcx
 jz .bad
 test r8,r8
 jz .bad
 test edx,edx
 jz .bad
 cmp edx,220500
 ja .bad
 lea r10d,[rdx*2+44]
 cmp r9d,r10d
 jb .bad
 lea r11,[header]
 xor r9d,r9d
.header:
 mov al,[r11+r9]
 mov [r8+r9],al
 inc r9d
 cmp r9d,44
 jb .header
 add edx,edx
 mov [r8+40],edx
 lea eax,[rdx+36]
 mov [r8+4],eax
 xor r9d,r9d
.copy:
 mov al,[rcx+r9]
 mov [r8+r9+44],al
 inc r9d
 cmp r9d,edx
 jb .copy
 mov eax,r10d
 ret
.bad:
 xor eax,eax
 ret

; Windows unwind metadata for the only non-leaf public routine. Read-only.
section .xdata rdata align=4
generate_unwind:
 db 1,generate_prologue_end-generate_begin,2,0
 db generate_prologue_end-generate_begin,1 ; UWOP_ALLOC_LARGE, 16-bit size / 8
 dw 152/8
section .pdata rdata align=4
 dd generate_begin wrt ..imagebase
 dd generate_end wrt ..imagebase
 dd generate_unwind wrt ..imagebase
