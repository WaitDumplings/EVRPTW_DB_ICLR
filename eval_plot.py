#!/usr/bin/env python3
"""Evaluate a checkpoint on one instance and write verified routes plus SVG.

Example: python eval_plot.py --ckpt model.pt --inst_path instance.json
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from evaluate import main

if __name__ == '__main__':
    raise SystemExit(main())
