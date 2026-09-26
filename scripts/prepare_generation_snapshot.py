#!/usr/bin/env python3
"""Make a new local anonymous Git work copy for the unchanged full generator gate."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    destination = args.output_dir.resolve()
    source = ROOT.resolve()
    if destination.exists():
        parser.error('output directory already exists; choose a new work-copy path')
    if destination.is_relative_to(source):
        parser.error('output directory must be outside the source archive')
    if shutil.which('git') is None:
        parser.error('Git is required for the optional full-generation work copy')
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns(
        '.git', '__pycache__', '*.pyc', '.pytest_cache', '*.egg-info', '.venv', 'outputs'))
    git = ['git', '-C', str(destination)]
    git_env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    git_env.update(GIT_AUTHOR_NAME='Anonymous Review', GIT_AUTHOR_EMAIL='review@example.invalid', GIT_COMMITTER_NAME='Anonymous Review', GIT_COMMITTER_EMAIL='review@example.invalid', GIT_AUTHOR_DATE='2026-01-01T00:00:00+0000', GIT_COMMITTER_DATE='2026-01-01T00:00:00+0000')
    commands = [
        ['init', '--initial-branch=stage2-repair-candidate'],
        ['config', '--local', 'user.name', 'Anonymous Review'],
        ['config', '--local', 'user.email', 'review@example.invalid'],
        ['config', '--local', 'commit.gpgsign', 'false'],
        ['config', '--local', 'core.hooksPath', '/dev/null'],
        ['add', '.'],
        ['commit', '-m', 'Anonymous release snapshot'],
    ]
    for command in commands:
        subprocess.run(git + command, check=True, capture_output=True, text=True, env=git_env)
    revision = subprocess.check_output(git + ['rev-parse', 'HEAD'], text=True, env=git_env).strip()
    status = subprocess.check_output(git + ['status', '--porcelain=v1', '--untracked-files=all'], text=True, env=git_env).strip()
    remotes = subprocess.check_output(git + ['remote'], text=True, env=git_env).strip()
    if status or remotes:
        raise RuntimeError('Expected a clean local snapshot without remotes')
    print(json.dumps({'status': 'PASS', 'purpose': 'local full-generation work copy',
                      'code_commit': revision, 'working_tree_clean': True,
                      'original_git_history_copied': False, 'remotes': [],
                      'note': 'Keep generated outputs outside this work copy. No generation was started.'}, indent=2))

if __name__ == '__main__':
    main()
