@echo off
setlocal
cd /d "%~dp0"
if exist tools\vendor\w64devkit\bin\gcc.exe set "PATH=%CD%\tools\vendor\w64devkit\bin;%PATH%"
if exist tools\vendor\nasm-2.16.03\nasm.exe set "PATH=%CD%\tools\vendor\nasm-2.16.03;%PATH%"
if not exist build mkdir build
rem NASM 2.16 warns for valid RIP-relative references across COFF sections.
nasm -f win64 -Wall -w-reloc-rel-dword -w-reloc-abs-dword -l build\sfx.lst -o build\sfx.obj engine\sfx.asm
if errorlevel 1 exit /b 1
gcc -shared -nostdlib -s -Wl,--entry,0 -o build\sfx.dll build\sfx.obj engine\sfx.def
if errorlevel 1 exit /b 1
gcc -shared -O2 -ffp-contract=off -Wall -Wextra -o build\sfx_ref.dll ref\sfx_ref.c engine\sfx.def
if errorlevel 1 exit /b 1
gcc -c -O2 -ffp-contract=off -o build\sfx_ref.o ref\sfx_ref.c
if errorlevel 1 exit /b 1
gcc -shared -O0 -ffp-contract=off -o build\sfx_ref_o0.dll ref\sfx_ref.c engine\sfx.def
if errorlevel 1 exit /b 1
nasm -f win64 -Wall -o build\abi_probe.obj tests\abi_probe.asm
if errorlevel 1 exit /b 1
gcc -O2 -ffp-contract=off -Wall -Wextra -o build\verify.exe tests\test_engine.c build\abi_probe.obj
if errorlevel 1 exit /b 1
gcc -O2 -Wall -Wextra -o build\bench.exe bench\bench.c
if errorlevel 1 exit /b 1
echo Build successful.
