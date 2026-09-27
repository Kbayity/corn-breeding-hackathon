# phase2/step0_deliverables.py
"""Extract every deliverable and scoring statement from the track PDF; DELIVERABLES.md is then written by hand from the extracted text."""
import os
from pypdf import PdfReader
PROJECT = '/home/ronitk/Ronit-Personal/Work/BayerHackathonDataset'
pdf = os.path.join(PROJECT, 'Documentations from other events', 'PRECISION_AGRICULTURE_HACKATHON_2026_TRACK1.pdf')
pages = [p.extract_text() for p in PdfReader(pdf).pages]
text = '\n'.join(pages)
open(os.path.join(PROJECT, 'exploration', 'outputs', 'track1_pdf.txt'), 'w').write(text)
kw = ['deliverable', 'Deliverables', 'score', 'scoring', 'metric', 'accuracy', 'RMSE', 'correlation', 'judge', 'Judge',
      'submission', 'README', 'evaluation', 'Evaluation', 'file', 'CSV', 'csv', 'format', 'predict', 'rank']
hits = [l.strip() for l in text.splitlines() if any(k in l for k in kw)]
print('\n'.join(hits))

def selfcheck():
    assert len(pages) == 8
    assert 'Deliverables Required' in text and 'Judge-Mode' in text
selfcheck()
