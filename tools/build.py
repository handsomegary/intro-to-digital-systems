"""Build the English combined question-and-solution book using XeLaTeX."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', default='xelatex', help='XeLaTeX executable')
    parser.add_argument('--chapter', choices=['midterm-112', 'final-112'])
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    if args.chapter and args.publish:
        parser.error('--publish is only for the complete book')
    engine = shutil.which(args.engine)
    if not engine:
        parser.error('XeLaTeX was not found; install it or use --engine')
    label = args.chapter or 'book'
    build = ROOT / '.build' / label
    build.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'main.tex'
    if args.chapter:
        source = build / 'preview.tex'
        source.write_text(
            r'\documentclass[11pt,a4paper,oneside]{book}' + '\n'
            r'\input{shared/preamble}\begin{document}' + '\n'
            + r'\input{exams/' + args.chapter + '}\n'
            + r'\end{document}' + '\n', encoding='utf-8')
    for number in (1, 2):
        command = [engine, '--disable-installer', '-interaction=nonstopmode',
                   '-halt-on-error', '-file-line-error',
                   f'-output-directory={build}', str(source)]
        # --disable-installer is specific to MiKTeX.
        version = subprocess.run([engine, '--version'], capture_output=True,
                                 text=True, encoding='utf-8', errors='replace')
        if 'miktex' not in version.stdout.lower():
            command.remove('--disable-installer')
        result = subprocess.run(command, cwd=ROOT, capture_output=True,
                                text=True, encoding='utf-8', errors='replace')
        (build / f'pass-{number}.txt').write_text(result.stdout + result.stderr,
                                               encoding='utf-8')
        if result.returncode:
            print(result.stdout[-10000:])
            raise SystemExit(f'Compilation failed; inspect {build}')
    log = (build / f'{source.stem}.log').read_text(encoding='utf-8', errors='replace')
    warnings = re.findall(r'^.*(?:Overfull \\[hv]box|Missing character:|'
                          r'LaTeX Warning:.*(?:undefined|multiply defined)|'
                          r'Label\(s\) may have changed).*$'
                          , log, flags=re.MULTILINE)
    output = build / f'{source.stem}.pdf'
    report = {'document': label, 'pages': None, 'warnings': warnings,
              'pdf': output.relative_to(ROOT).as_posix()}
    page_match = re.search(r'Output written on .*?\((\d+) page', log, re.DOTALL)
    if page_match:
        report['pages'] = int(page_match.group(1))
    (build / 'build-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    if not output.is_file() or warnings:
        raise SystemExit(f'Build needs review: {warnings}; see {build}')
    if args.publish:
        shutil.copyfile(output, ROOT / 'exam-solutions.pdf')
    print(f'PASS: {label}; {report["pages"]} pages; no layout/reference warnings')


if __name__ == '__main__':
    main()
