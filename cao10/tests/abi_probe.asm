bits 64
default rel
global abi_probe
section .text
; uint32 abi_probe(function,a,b,c,d). Calls function and verifies all Win64
; nonvolatile GP/SIMD registers. Preserves our caller's original registers.
; 248 local bytes plus 64 saved GP bytes, test stub only (not engine).
abi_probe:
 mov rax,[rsp+40]
 push rbx
 push rbp
 push rsi
 push rdi
 push r12
 push r13
 push r14
 push r15
 sub rsp,248
 mov [rsp+32],rcx
 mov [rsp+40],rdx
 mov [rsp+48],r8
 mov [rsp+56],r9
 mov [rsp+224],rax
%assign i 6
%rep 10
 movups [rsp+64+(i-6)*16],xmm%+i
 pcmpeqd xmm%+i,xmm%+i
%assign i i+1
%endrep
 mov rbx,0x123456789abcdef0
 mov rbp,rbx
 mov rsi,rbx
 mov rdi,rbx
 mov r12,rbx
 mov r13,rbx
 mov r14,rbx
 mov r15,rbx
 mov rcx,[rsp+40]
 mov rdx,[rsp+48]
 mov r8,[rsp+56]
 mov r9,[rsp+224]
 call [rsp+32]
 xor eax,eax
 mov r10,0x123456789abcdef0
%macro check 1
 cmp %1,r10
 je %%ok
 or eax,1
%%ok:
%endmacro
 check rbx
 check rbp
 check rsi
 check rdi
 check r12
 check r13
 check r14
 check r15
 pcmpeqd xmm0,xmm0
%assign i 6
%rep 10
 pcmpeqb xmm%+i,xmm0
 pmovmskb r11d,xmm%+i
 cmp r11d,65535
 je .ok%+i
 or eax,2
.ok%+i:
 movups xmm%+i,[rsp+64+(i-6)*16]
%assign i i+1
%endrep
 add rsp,248
 pop r15
 pop r14
 pop r13
 pop r12
 pop rdi
 pop rsi
 pop rbp
 pop rbx
 ret
