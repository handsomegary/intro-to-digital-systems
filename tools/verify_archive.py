"""Check English content, portable TeX inputs, and the generated-PDF-only policy."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
PDF = 'exam-solutions.pdf'
CJK = re.compile('[' + chr(0x3400) + '-' + chr(0x4dbf) + chr(0x4e00) + '-'
                 + chr(0x9fff) + chr(0xf900) + '-' + chr(0xfaff) + ']')
PRIVATE_PATH = re.compile(r'[A-Za-z]:[\\/]|/U[s]ers/|/h[o]me/')
TEXT = {'.tex', '.md', '.py', '.json', '.yml', '.yaml', '.txt'}


def pdf_allowlist(names):
    found = {name for name in names if Path(name).suffix.lower() == '.pdf'}
    assert found <= {PDF}, f'Original or unexpected PDF paths: {sorted(found - {PDF})}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', action='store_true')
    args = parser.parse_args()
    public_paths = []
    for path in ROOT.rglob('*'):
        relative = path.relative_to(ROOT)
        if any(part in {'.git', '.build', '__pycache__'} for part in relative.parts):
            continue
        assert not CJK.search(relative.as_posix()), str(relative)
        if not path.is_file():
            continue
        public_paths.append(relative.as_posix())
        assert path.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.docx', '.zip'}, relative
        if path.suffix not in TEXT:
            continue
        content = path.read_text(encoding='utf-8')
        assert not CJK.search(content), f'Non-English script in {relative}'
        assert not PRIVATE_PATH.search(content), f'Private absolute path in {relative}'
        if path.suffix == '.tex':
            for target in re.findall(r'\\(?:input|include)\{([^}]+)\}', content):
                dependency = ROOT / target
                if not dependency.suffix:
                    dependency = dependency.with_suffix('.tex')
                assert dependency.is_file(), f'Missing TeX input: {target}'
                assert dependency.resolve().is_relative_to(ROOT.resolve()), target
    pdf_allowlist(public_paths)
    coverage = json.loads((ROOT / 'source-coverage.json').read_text(encoding='utf-8'))
    assert len(coverage['sources']) == 5
    assert coverage['midterm']['question_numbers'] == list(range(1, 11))
    assert coverage['midterm']['printed_total_percent'] == 140
    assert coverage['final']['question_numbers'] == [1]
    assert coverage['final']['printed_total_percent'] == 100
    assert coverage['software_only_questions_omitted'] == []
    master = (ROOT / 'main.tex').read_text(encoding='utf-8')
    for name in ('midterm-112', 'final-112'):
        assert r'\input{exams/' + name + '}' in master
    if (ROOT / '.git').exists() and shutil.which('git'):
        def git(*arguments):
            return subprocess.check_output(['git', *arguments], cwd=ROOT,
                                           text=True, encoding='utf-8')
        pdf_allowlist(git('ls-files', '-z').split('\0'))
        if git('rev-list', '--all').strip():
            pdf_allowlist(name.strip('\r\n') for name in
                          git('log', '--all', '--format=', '--name-only', '-z').split('\0'))
    print('PASS: English archive, five sources accounted for, original PDFs excluded')
    if args.pdf:
        from pypdf import PdfReader
        reader = PdfReader(ROOT / PDF)
        content = '\n'.join(page.extract_text() or '' for page in reader.pages)
        assert not CJK.search(content + str(reader.metadata))
        assert not PRIVATE_PATH.search(content + str(reader.metadata))
        assert reader.metadata.title == 'Introduction to Digital Systems: Questions and Worked Solutions'
        assert 'Midterm' in content and 'Final' in content
        print(f'PASS: rebuilt English PDF, {len(reader.pages)} pages')


if __name__ == '__main__':
    main()
