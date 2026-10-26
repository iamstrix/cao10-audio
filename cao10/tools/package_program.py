"""Ship runnable binaries, source, and evidence; omit downloaded compilers."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[1]
out=ROOT.parent/'output';out.mkdir(exist_ok=True)
with ZipFile(out/'cao10-program.zip','w',ZIP_DEFLATED) as archive:
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(ROOT)
        if 'vendor' in relative.parts or '__pycache__' in relative.parts:continue
        if path.suffix=='.pyc' or path.name=='.gitignore':continue
        archive.write(path,Path('cao10')/relative)
print(out/'cao10-program.zip')
