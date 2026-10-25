"""Run all independent digital-logic and minimizer checks."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def main():
    for name in ('verify_midterm.py', 'verify_final.py'):
        subprocess.run([sys.executable, str(ROOT / 'tools' / name)], cwd=ROOT, check=True)
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                   cwd=ROOT, check=True)
    print('PASS: all exam and minimizer checks')


if __name__ == '__main__':
    main()
