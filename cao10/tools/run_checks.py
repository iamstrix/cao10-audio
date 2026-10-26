"""Run reproducible native and Python checks; retain raw evidence for Chapter 4."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
results=ROOT/'results';results.mkdir(exist_ok=True)
def run(command,filename):
    completed=subprocess.run(command,check=True,capture_output=True,text=True)
    (results/filename).write_text(completed.stdout)
    if filename.endswith('.json'): print(completed.stdout,flush=True)
    else: print('Saved '+filename,flush=True)
    return completed.stdout
run([str(ROOT/'build/verify.exe')],'engine-tests.json')
run([sys.executable,'tests/test_headless.py'],'headless-console.json')
run([str(ROOT/'build/bench.exe')],'benchmark.json')
vendor=ROOT/'tools/vendor/w64devkit/bin'
run([str(vendor/'objdump.exe'),'-p','build/sfx.dll'],'dll-pe.txt')
run([str(vendor/'objdump.exe'),'-h','build/sfx.dll'],'dll-sections.txt')
run([str(vendor/'objdump.exe'),'-d','build/sfx.dll'],'dll-disassembly.txt')
cpu=subprocess.run(['powershell','-NoProfile','-Command','Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors | ConvertTo-Json'],capture_output=True,text=True)
power=subprocess.run(['powercfg','/getactivescheme'],capture_output=True,text=True)
cpu_info=cpu.stdout.strip()
cpu_snapshot=results/'cpu.json'
if not cpu_info and cpu_snapshot.exists():cpu_info=json.loads(cpu_snapshot.read_text(encoding='utf-8-sig'))
metadata=dict(timestamp=datetime.datetime.now().astimezone().isoformat(),platform=platform.platform(),
              python=sys.version,cpu=cpu_info,power_scheme=power.stdout.strip(),
              power_connection='Not controlled or verified',background_apps='Not controlled',
              machines_tested=1,c_reference_object_bytes=(ROOT/'build/sfx_ref.o').stat().st_size,
              compiler=subprocess.check_output([str(vendor/'gcc.exe'),'--version'],text=True).splitlines()[0],
              nasm=subprocess.check_output([str(ROOT/'tools/vendor/nasm-2.16.03/nasm.exe'),'-v'],text=True).strip(),
              sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in list((ROOT/'engine').glob('*'))+list((ROOT/'ref').glob('*'))+[ROOT/'build/sfx.dll']})
(results/'environment.json').write_text(json.dumps(metadata,indent=2))
