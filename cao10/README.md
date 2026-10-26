# Procedural Game Sound Effects Generator

Windows x64 desktop sound generator for CA010. All audio synthesis and WAV
construction run in hand-written NASM. Python/Tkinter supplies the controls,
waveform display, playback, and file dialog. Only Python's standard library is
required at runtime.

## Run

Install 64-bit Python 3.11 or newer with Tcl/Tk, then double-click `launch.bat`.
The provided program archive includes the compiled `build/sfx.dll`.
Choose a preset, adjust controls, press **Play**, and **Save WAV**.
Auto-play is off by default. Playback runs on a worker thread.

## Build from source

Use NASM 2.16+ and MinGW-w64 GCC on PATH, or run
`powershell -ExecutionPolicy Bypass -File tools/bootstrap.ps1` to download the
pinned portable toolchain into `tools/vendor`. Then run `build.bat`.
The script stops on compiler/linker errors and builds the Assembly DLL,
C reference at O2 and O0, correctness harness, and benchmark harness.
Generated sine tables are committed; `python tools/gen_sine_table.py` regenerates them.

## Reproduce the checks

From this directory:

```bat
build.bat
python tools/run_checks.py
python tests/test_gui_headless.py
```

`run_checks.py` expects the pinned toolchain in `tools/vendor` for the PE inspection
and compiler metadata. It writes raw native tests, headless binding tests,
benchmarks, DLL inspection, hashes and environment information into `results`.
The off-screen GUI test needs a normal Python installation with working Tcl/Tk;
it uses hidden real widgets, a 480-column Canvas, and mocked audio playback.
It writes `results/gui-headless.json`. Neither test plays audio.

The native tests compare 20 fixed cases (five per waveform, including all seven
presets) and 10,000 seeded random parameter sets against a separate C reference.
They also check invalid input, guard bytes, repeatability, pitch slide, waveform
periods, full-scale quantization, WAV headers, and Win64 nonvolatile registers.
Binding tests cover 1,000 Randomize operations and 100 concurrent calls.

Benchmarks use a C QueryPerformanceCounter harness with 100 warm-ups and 1,000
measurements per waveform and implementation. Each measured sound has 44,100
samples with slide and vibrato enabled. Allocation, GUI drawing and WAV export
are excluded. Medians and p95 values are retained in `results/benchmark.json`.

## Evaluation limits

Current results are from one Windows laptop. Optimized C is faster than this
Assembly implementation; all measured Assembly medians are below the 5 ms
target. Background applications and AC connection were not controlled during
the benchmark. A later battery snapshot is retained separately and does not
establish the conditions throughout timing.

Actual speakers, Audacity/Windows Media Player compatibility, a visible-window
review by another group member, group listening, a ten-minute soak session, and
second-laptop benchmarks still need completion. Headless GUI latency is useful
integration evidence, but does not certify visible-window rendering latency.
No claims are made that presets are recognisable without a listening test.

The engine has no heap use, no imported DLLs and no writable sections. The
linker emits a read-only `.idata` containing only a null import descriptor;
`.pdata` and `.xdata` provide Windows unwind information. The generator uses a
152-byte stack frame plus call return addresses, below the 256-byte budget.
The three exported functions are documented in `ref/sfx.h` and the specification.
Input/output buffers for `sfx_write_wav` must not overlap.

The parameter format is 44 bytes. Audio is mono signed 16-bit PCM at 44.1 kHz,
up to 220,500 samples. Identical parameters and seed give identical bytes.
JSON parameter storage, a sine oscillator and Linux support are optional and
are not implemented in this version.
