"""Run from any directory; all subprocess calls use argument arrays."""
import pathlib, subprocess, sys
D=pathlib.Path(__file__).resolve().parent
for script in ['run.py','supplement.py','summarize.py']:
    subprocess.run(['nice','-n','10',sys.executable,str(D/script)],check=True)
