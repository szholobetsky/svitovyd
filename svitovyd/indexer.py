"""svitovyd.indexer — scan a project directory and build a language-agnostic map.

Produces a text file listing:
  - defined identifiers (classes, functions, endpoints, tables, …)
  - cross-file references with relationship types (import / call / ref / expr)
  - optionally variables and function parameters (depth 3)
"""

from __future__ import annotations

import os
import re
import sys

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(it, **_):
        return it

# ── file filtering ─────────────────────────────────────────────────────────────

MAX_FILE_KB = 200

SCAN_EXTENSIONS = {
    '.py', '.js', '.ts', '.java', '.cs', '.go', '.rs', '.cpp', '.c', '.h',
    '.rb', '.php', '.kt', '.scala', '.swift', '.lua', '.r', '.m',
    '.html', '.htm', '.css', '.jsx', '.tsx', '.vue', '.svelte',
    '.sql', '.plsql', '.pls', '.pkb', '.pks',
    '.yaml', '.yml', '.toml', '.ini', '.env', '.conf', '.cfg', '.tf', '.hcl',
    '.xml', '.json',
    '.sh', '.bat', '.ps1',
}

SKIP_DIRS = {
    '.git', '.svn', '.hg', 'node_modules', '__pycache__', '.pytest_cache',
    '.venv', 'venv', 'env', '.env', 'dist', 'build', 'target', 'out',
    '.gradle', '.idea', '.vscode', '.1bcoder', '.simargl',
}

# ── definition patterns ────────────────────────────────────────────────────────

DEFINE_PATTERNS = [
    r'(?:def|function|func|fn|sub|procedure)\s+(\w+)',
    r'(?:class|interface|type|struct|enum|record)\s+(\w+)',
    r'CREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|VIEW|PROCEDURE|FUNCTION|PACKAGE(?:\s+BODY)?|TRIGGER)\s+(?:\w+\.)?(\w+)',
    r'resource\s+"[^"]+"\s+"(\w+)"',
    r'module\s+"(\w+)"',
    r'(?:id|name)\s*=\s*["\'](\w[\w-]+)["\']',
    r'@(?:app|router|Blueprint|api)\.\w+\s*\(\s*["\']([^"\']+)',
    r'^(\w[\w-]{3,})\s*[:=][^=]',
]

VAR_PATTERNS = [r'^(\w+)\s*=\s*[^=\n]']

STOP_WORDS = {
    'true', 'false', 'null', 'none', 'self', 'this', 'return', 'super',
    'import', 'from', 'class', 'function', 'interface', 'struct', 'enum',
    'public', 'private', 'protected', 'static', 'final', 'abstract',
    'void', 'bool', 'int', 'str', 'float', 'list', 'dict', 'tuple',
    'string', 'number', 'object', 'array', 'type', 'with', 'async', 'await',
    'pass', 'break', 'continue', 'raise', 'yield', 'lambda', 'global',
    'args', 'kwargs', 'cls',
    'for', 'not', 'and', 'try', 'del', 'def', 'elif', 'else', 'none',
}

_ASSIGN_RE = re.compile(r'(?<![=!<>])=(?!=)')
_WORD_RE   = re.compile(r'\b([A-Za-z_]\w*)\b')
_IMPORT_KW = re.compile(
    r'\b(import|from|include|require|uses|use|using|load|needs)\b', re.IGNORECASE
)


def classify_ref(name: str, text: str) -> str:
    escaped = re.escape(name)
    call = re.compile(escaped + r'\s*\(')
    ref  = re.compile(r'[\(\[,]\s*' + escaped + r'\s*[\)\],]')
    word = re.compile(r'\b' + escaped + r'\b')
    types: set[str] = set()
    for line in text.splitlines():
        if not word.search(line):
            continue
        if _IMPORT_KW.search(line):
            types.add('import')
        elif call.search(line):
            types.add('call')
        elif ref.search(line):
            types.add('ref')
        else:
            types.add('expr')
    return ','.join(t for t in ('import', 'call', 'ref', 'expr') if t in types) or 'ref'


def collect_files(root: str) -> list[str]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')]
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in SCAN_EXTENSIONS:
                continue
            fpath = os.path.join(dirpath, fname)
            try:
                if os.path.getsize(fpath) > MAX_FILE_KB * 1024:
                    continue
            except OSError:
                continue
            files.append(fpath)
    return files


def extract_definitions(text: str, depth: int) -> tuple[dict, dict]:
    def lineno(m):
        return text[:m.start()].count('\n') + 1

    defs: dict[str, int] = {}
    for pat in DEFINE_PATTERNS:
        for m in re.finditer(pat, text, re.IGNORECASE | re.MULTILINE):
            name = m.group(1).strip()
            if len(name) >= 4 and name.lower() not in STOP_WORDS and name not in defs:
                defs[name] = lineno(m)

    vars_dict: dict[str, int] = {}
    if depth >= 3:
        for pat in VAR_PATTERNS:
            for m in re.finditer(pat, text, re.MULTILINE):
                name = m.group(1).strip()
                if len(name) >= 3 and name.lower() not in STOP_WORDS \
                        and name not in defs and name not in vars_dict:
                    vars_dict[name] = lineno(m)
        for m in re.finditer(r'def\s+\w+\s*\(([^)]*)\)', text, re.IGNORECASE):
            for param in m.group(1).split(','):
                name = re.sub(r'[:\*=\[].*', '', param).strip().lstrip('*')
                if len(name) >= 3 and name.lower() not in STOP_WORDS \
                        and name not in defs and name not in vars_dict:
                    vars_dict[name] = lineno(m)
        for lno, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith('#'):
                continue
            if not _ASSIGN_RE.search(line):
                continue
            for m in _WORD_RE.finditer(line):
                name = m.group(1)
                if len(name) >= 3 and name.lower() not in STOP_WORDS \
                        and name not in defs and name not in vars_dict:
                    vars_dict[name] = lno

    return defs, vars_dict


def _parse_existing_map(text: str) -> tuple[dict, dict]:
    cached_blocks: dict[str, list] = {}
    cached_defs:   dict[str, tuple] = {}
    current_rel   = None
    current_lines: list[str] = []
    current_defs:  dict[str, int] = {}
    current_vars:  dict[str, int] = {}

    def _flush():
        if current_rel:
            cached_blocks[current_rel] = current_lines[:]
            cached_defs[current_rel]   = (dict(current_defs), dict(current_vars))

    for line in text.splitlines():
        if line.startswith('#') or not line.strip():
            continue
        if not line.startswith(' ') and not line.startswith('\t'):
            _flush()
            current_rel   = line.strip()
            current_lines = []
            current_defs  = {}
            current_vars  = {}
        else:
            current_lines.append(line)
            s = line.strip()
            if s.startswith('defines :'):
                for item in s[len('defines :'):].strip().split(','):
                    m = re.match(r'(\w+)\(ln:(\d+)\)', item.strip())
                    if m:
                        current_defs[m.group(1)] = int(m.group(2))
            elif re.match(r'vars\s+:', s):
                for item in re.sub(r'^vars\s+:\s*', '', s).split(','):
                    m = re.match(r'(\w+)\(ln:(\d+)\)', item.strip())
                    if m:
                        current_vars[m.group(1)] = int(m.group(2))
    _flush()
    return cached_blocks, cached_defs


def build_map(root: str, depth: int = 2, map_path: str | None = None) -> str:
    """Scan root and return map as a string.

    If map_path points to an existing map file, unchanged files are reused from cache.
    """
    root  = os.path.abspath(root)
    files = collect_files(root)

    map_mtime     = 0.0
    cached_blocks: dict = {}
    cached_defs:   dict = {}
    if map_path and os.path.exists(map_path):
        map_mtime = os.path.getmtime(map_path)
        try:
            existing = open(map_path, encoding='utf-8', errors='ignore').read()
            cached_blocks, cached_defs = _parse_existing_map(existing)
        except OSError:
            pass

    file_defs:    dict = {}
    file_content: dict = {}
    skipped = 0

    for fpath in tqdm(files, desc="scanning", unit="file", file=sys.stderr):
        rel = os.path.relpath(fpath, root)
        try:
            fmtime = os.path.getmtime(fpath)
        except OSError:
            continue
        if map_mtime and fmtime <= map_mtime and rel in cached_defs:
            file_defs[rel] = cached_defs[rel]
            skipped += 1
            continue
        try:
            text = open(fpath, encoding='utf-8', errors='ignore').read()
        except OSError:
            continue
        defs, vars_dict    = extract_definitions(text, depth)
        file_defs[rel]     = (defs, vars_dict)
        file_content[rel]  = text

    if skipped:
        changed = len(file_content)
        print(f"[svitovyd] {skipped} unchanged (reused), {changed} changed (re-scanned)",
              file=sys.stderr)

    global_index: dict[str, str] = {}
    for rel, (defs, _) in file_defs.items():
        for name in defs:
            if name not in global_index:
                global_index[name] = rel
    for rel, (_, vars_dict) in file_defs.items():
        for name in vars_dict:
            if name not in global_index:
                global_index[name] = rel

    file_links: dict = {}
    for rel, text in tqdm(file_content.items(), desc="linking", unit="file", file=sys.stderr):
        by_target: dict = {}
        for name, target_rel in global_index.items():
            if target_rel == rel:
                continue
            if re.search(r'\b' + re.escape(name) + r'\b', text):
                kind = classify_ref(name, text)
                by_target.setdefault(target_rel, {})[name] = kind
        file_links[rel] = by_target

    out = [f"# svitovyd map — {root}  depth:{depth}"]
    for rel in sorted(file_defs):
        out.append(f"\n{rel}")
        if rel in file_content:
            defs, vars_dict = file_defs[rel]
            if defs:
                items = ', '.join(
                    f"{n}(ln:{ln})" for n, ln in sorted(defs.items(), key=lambda x: x[1])
                )
                out.append(f"  defines : {items}")
            for target in sorted(file_links.get(rel, {})):
                refs  = file_links[rel][target]
                items = ', '.join(f"{kind}:{n}" for n, kind in sorted(refs.items()))
                out.append(f"  links  → {target} ({items})")
            if vars_dict:
                items = ', '.join(
                    f"{n}(ln:{ln})" for n, ln in sorted(vars_dict.items(), key=lambda x: x[1])
                )
                out.append(f"  vars    : {items}")
        elif rel in cached_blocks:
            out.extend(cached_blocks[rel])

    return '\n'.join(out)
