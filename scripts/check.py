#!/usr/bin/env python3
"""Run the documented local checks from any working directory."""

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def check_docs():
    """Check local Markdown file links and balanced fenced code blocks."""
    paths = sorted(set(ROOT.glob('*.md')) | set(ROOT.glob('*/README.md'))
                   | set((ROOT / 'docs').rglob('*.md')))
    errors = []
    for path in paths:
        text = path.read_text(encoding='utf-8')
        fence = None
        for number, line in enumerate(text.splitlines(), 1):
            marker = re.match(r'^\s*(`{3,}|~{3,})', line)
            if marker:
                value = marker.group(1)
                if fence is None:
                    fence = value
                elif value[0] == fence[0] and len(value) >= len(fence):
                    fence = None
                continue
            if fence:
                continue
            for target in re.findall(r'!?\[[^\]]*\]\(([^\s)]+)\)', line):
                parsed = urlsplit(target.strip('<>'))
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                resolved = (path.parent / unquote(parsed.path)).resolve()
                if not resolved.exists():
                    errors.append(f'{path.relative_to(ROOT)}:{number}: missing {target}')
        if fence:
            errors.append(f'{path.relative_to(ROOT)}: unclosed code fence')
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f'Documentation checks passed ({len(paths)} Markdown files).', flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docs-only', action='store_true',
                        help='check documentation without application dependencies')
    args = parser.parse_args()
    if check_docs():
        return 1
    if args.docs_only:
        return 0
    required = ['cdn-proxy/tap-verifier.js', 'cdn-proxy/agent-api.js',
                'tap-agent/tests/test_signature.py', 'agent-registry/tests/test_key_lookup.py']
    missing = [path for path in required if not (ROOT / path).is_file()]
    if missing:
        print('Full checks require the verifier, routing, and registry fixes in this checkout.\n'
              + 'Missing: ' + ', '.join(missing), file=sys.stderr)
        return 1
    environment = {**os.environ, 'PYTHON': sys.executable}
    commands = [
        (['node', '--test'], ROOT / 'cdn-proxy'),
        ([sys.executable, '-m', 'unittest', 'discover', '-s', 'tap-agent/tests', '-v'], ROOT),
        ([sys.executable, '-m', 'unittest', 'discover', '-s', 'agent-registry/tests', '-v'], ROOT),
    ]
    for command, directory in commands:
        print(f'Running {" ".join(command)} in {directory.relative_to(ROOT) or "."}', flush=True)
        try:
            result = subprocess.run(command, cwd=directory, env=environment, check=False)
        except FileNotFoundError as error:
            print(f'Missing executable: {error.filename}. See docs/quickstart.md.', file=sys.stderr)
            return 1
        if result.returncode:
            return result.returncode
    print('All local checks passed.', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
