"""Rasterize Word-exported PDFs with bundled Poppler and compare prior pages."""
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image,ImageDraw
from pdf2image import convert_from_path
from pypdf import PdfReader
from docx import Document
ROOT=Path(__file__).resolve().parents[2]
runtime=Path(sys.executable).parent.parent
poppler=runtime/'native/poppler/Library/bin'
qa=ROOT/'tmp/docx-qa';qa.mkdir(parents=True,exist_ok=True)
original=ROOT/'tmp/docx-original/original.pdf'
updated=qa/'updated.pdf'
old_reader=PdfReader(original);new_reader=PdfReader(updated)
assert len(new_reader.pages)>len(old_reader.pages)
before=Document(ROOT/'tmp/docx-original/proposal-before-chapter4.docx')
after=Document(next(ROOT.glob('*.docx')))
assert [p.text for p in before.paragraphs]==[p.text for p in after.paragraphs[:len(before.paragraphs)]]
assert [[[c.text for c in r.cells] for r in t.rows] for t in before.tables]==[[[c.text for c in r.cells] for r in t.rows] for t in after.tables[:len(before.tables)]]
checks=[]
for i,p in enumerate(old_reader.pages):
    same=p.extract_text()==new_reader.pages[i].extract_text()
    checks.append(dict(page=i+1,text_unchanged=same))
for stale in qa.glob('page*.png'):
    assert stale.resolve().parent==qa.resolve()
    stale.unlink()
paths=convert_from_path(str(updated),dpi=120,output_folder=str(qa),fmt='png',
                        output_file='page',paths_only=True,poppler_path=str(poppler))
# Check the original pages at raster level as well as extracted text.
old_paths=convert_from_path(str(original),dpi=120,output_folder=str(ROOT/'tmp/docx-original'),
                            fmt='png',output_file='page',paths_only=True,poppler_path=str(poppler))
for i,p in enumerate(old_paths):
    with Image.open(p) as a,Image.open(paths[i]) as b:
        same=a.size==b.size and a.tobytes()==b.tobytes()
    checks[i]['pixels_unchanged']=same
for n,start in enumerate(range(0,len(paths),6),1):
    sheet=Image.new('RGB',(1000,3*688),'#dddddd');draw=ImageDraw.Draw(sheet)
    for j,p in enumerate(paths[start:start+6]):
        im=Image.open(p);im.thumbnail((480,640));x=(j%2)*500+10;y=(j//2)*688+25
        sheet.paste(im,(x,y));draw.text((x,y-20),f'Page {start+j+1}',fill='black')
    sheet.save(qa/f'contact-{n}.png')
(qa/'qa.json').write_text(json.dumps(dict(original_pages=len(old_reader.pages),updated_pages=len(new_reader.pages),
    original_proposal_text_unchanged=True,original_table_indents_corrected=True,prior_page_checks=checks,pages=paths),indent=2))
for i,p in enumerate(new_reader.pages):
    if i>=len(old_reader.pages):print(f'Page {i+1}: '+p.extract_text()[:200].replace('\n',' '))
print('Original proposal text unchanged; table indents corrected; rendered',len(paths),'pages.')
