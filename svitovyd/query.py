"""svitovyd.query — query a svitovyd map file.

Modes:
  find   — filter file blocks by filename and/or child-line content
  trace  — BFS backwards through the call graph from an identifier
  deps   — BFS forwards (what a file depends on)
  idiff  — ORPHAN_DRIFT + GHOST ALERT between two map snapshots
  sym    — asymmetry and cohesion health report

Filter token syntax for find:
    term    filename contains term
    !term   exclude if filename contains term
    \\term  include block if any child line contains term
    \\!term exclude block if any child line contains term
    -term   show ONLY child lines containing term
    -!term  hide child lines containing term
"""

from __future__ import annotations

import os
import re


# ── parse ───────────────────────────────────────────────────────────────────────

def parse_map(map_path: str) -> tuple[dict, dict]:
    """Parse map file → (defines_map, links_map).

    defines_map : { rel_file → { name → lineno } }
    links_map   : { caller_rel → { target_rel → { name → kind } } }
    """
    with open(map_path, encoding='utf-8') as f:
        content = f.read()

    defines_map: dict = {}
    links_map:   dict = {}
    current_file = None

    for line in content.splitlines():
        if line.startswith('#') or not line.strip():
            continue
        if not line.startswith(' '):
            current_file = line.strip()
            defines_map.setdefault(current_file, {})
            links_map.setdefault(current_file, {})
        elif current_file and 'defines :' in line:
            items_str = line.split('defines :', 1)[1].strip()
            for item in items_str.split(', '):
                m = re.match(r'(\w[\w-]*)\(ln:(\d+)\)', item.strip())
                if m:
                    defines_map[current_file][m.group(1)] = int(m.group(2))
        elif current_file and 'links  →' in line:
            m = re.match(r'\s+links\s+→\s+(\S+)\s+\((.+)\)', line)
            if m:
                target   = m.group(1)
                refs_str = m.group(2)
                refs: dict = {}
                for item in refs_str.split(', '):
                    if ':' in item:
                        kind, name = item.split(':', 1)
                        refs[name.strip()] = kind.strip()
                links_map[current_file].setdefault(target, {}).update(refs)

    return defines_map, links_map


# ── find ────────────────────────────────────────────────────────────────────────

def find_map(map_path: str, query: str) -> tuple[list, str]:
    """Search map file with filter syntax.

    Returns (hits, rendered_string).
    """
    with open(map_path, encoding='utf-8') as f:
        content = f.read()

    tokens:          list[str] = query.split()
    pos_file:        list[str] = []
    neg_file:        list[str] = []
    pos_child:       list[str] = []
    neg_block:       list[str] = []
    show_lines:      list[str] = []
    hide_lines:      list[str] = []
    must_show_lines: list[str] = []   # +term — filter children AND hide file if none match

    for t in tokens:
        if t.startswith('\\!') and len(t) > 2:
            neg_block.append(t[2:].lower())
        elif t.startswith('\\') and len(t) > 1:
            pos_child.append(t[1:].lower())
        elif t.startswith('-!') and len(t) > 2:
            hide_lines.append(t[2:].lower())
        elif t.startswith('-') and len(t) > 1:
            show_lines.append(t[1:].lower())
        elif t.startswith('+') and len(t) > 1:
            must_show_lines.append(t[1:].lower())
        elif t.startswith('!') and len(t) > 1:
            neg_file.append(t[1:].lower())
        else:
            pos_file.append(t.lower())

    if not any([pos_file, neg_file, pos_child, neg_block, show_lines, hide_lines, must_show_lines]):
        return [], content

    blocks = re.split(r'\n(?=\S)', content)

    def process_block(block: str) -> str | None:
        lines       = block.split('\n')
        fname       = lines[0].lower()
        child_lines = [l for l in lines[1:] if l.strip()]

        if pos_file and not all(t in fname for t in pos_file):
            return None
        if any(t in fname for t in neg_file):
            return None
        if pos_child:
            if not any(all(t in line.lower() for t in pos_child) for line in child_lines):
                return None
        if neg_block:
            children_text = '\n'.join(child_lines).lower()
            if any(t in children_text for t in neg_block):
                return None
        if show_lines:
            child_lines = [l for l in child_lines
                           if any(t in l.lower() for t in show_lines)]
        if must_show_lines:
            child_lines = [l for l in child_lines
                           if any(t in l.lower() for t in must_show_lines)]
            if not child_lines:
                return None
        if hide_lines:
            child_lines = [l for l in child_lines
                           if not any(t in l.lower() for t in hide_lines)]

        return lines[0] + ('\n' + '\n'.join(child_lines) if child_lines else '')

    hits = [r for b in blocks
            if not b.startswith('#')
            for r in [process_block(b)] if r is not None]

    return hits, '\n'.join(hits)


# ── trace (backwards) ────────────────────────────────────────────────────────────

def trace_map(map_path: str, identifier: str, max_depth: int = 8) -> str | None:
    """BFS backwards through the call graph from a defined identifier."""
    defines_map, links_map = parse_map(map_path)

    start_file = start_ln = None
    for frel, defs in defines_map.items():
        if identifier in defs:
            start_file = frel
            start_ln   = defs[identifier]
            break

    if not start_file:
        return None

    incoming: dict = {}
    for caller, targets in links_map.items():
        for target, refs in targets.items():
            for name, kind in refs.items():
                incoming.setdefault(target, []).append((caller, name, kind))

    lines_out = [
        f'trace: {identifier}',
        f'{start_file}  [defines {identifier}(ln:{start_ln})]',
    ]
    visited = {start_file}
    queue   = [(start_file, 1)]

    while queue:
        current, depth = queue.pop(0)
        if depth > max_depth:
            break
        indent  = '  ' * depth
        for caller, name, kind in sorted(incoming.get(current, []), key=lambda x: x[0]):
            lines_out.append(f'{indent}← {kind}:{name}  {caller}')
            if caller not in visited:
                visited.add(caller)
                queue.append((caller, depth + 1))

    return '\n'.join(lines_out)


# ── deps (forward) ───────────────────────────────────────────────────────────────

def deps_map(map_path: str, identifier: str, max_depth: int = 8) -> str | None:
    """BFS forward through the dependency graph from a defined identifier."""
    defines_map, links_map = parse_map(map_path)

    start_file = start_ln = None
    for frel, defs in defines_map.items():
        if identifier in defs:
            start_file = frel
            start_ln   = defs[identifier]
            break
    if not start_file:
        matches = [f for f in defines_map
                   if identifier.replace('\\', '/') in f.replace('\\', '/')]
        if matches:
            start_file = sorted(matches, key=len)[0]

    if not start_file:
        return None

    parent:   dict = {start_file: None}
    depth_of: dict = {start_file: 0}
    queue   = [start_file]
    order   = [start_file]

    while queue:
        current = queue.pop(0)
        d = depth_of[current]
        if d >= max_depth:
            continue
        for target, refs in links_map.get(current, {}).items():
            if target not in parent:
                name = next(iter(refs))
                kind = refs[name]
                parent[target]   = (current, name, kind)
                depth_of[target] = d + 1
                queue.append(target)
                order.append(target)

    start_label = f"{identifier}(ln:{start_ln})" if start_ln else identifier
    lines_out = [f"deps: {start_label}", f"{start_file}"]

    for frel in order[1:]:
        entry = parent[frel]
        if entry is None:
            continue
        _, name, kind = entry
        indent = "  " * depth_of[frel]
        lines_out.append(f"{indent}→ {kind}:{name}  {frel}")

    return '\n'.join(lines_out)


# ── keywords ─────────────────────────────────────────────────────────────────────

def _split_identifier(name: str) -> list[str]:
    """Split camelCase / PascalCase / snake_case / kebab-case into lowercase subwords.

    Examples:
        RuleIndex   → ['rule', 'index']
        rule_index  → ['rule', 'index']
        HTTPRequest → ['http', 'request']
    """
    parts = re.split(r'[_\-]+', name)
    result = []
    for part in parts:
        if not part:
            continue
        s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', part)
        s = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', s)
        result.extend(w.lower() for w in s.split('_') if len(w) >= 2)
    seen: dict = {}
    for w in result:
        seen.setdefault(w, None)
    return list(seen)


def _build_line_to_file(map_path: str) -> dict:
    """Return {line_number: file_path} for every line in map.txt.

    File ownership: nearest non-indented, non-comment line above.
    """
    with open(map_path, encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    result = {}
    current_file = None
    for i, line in enumerate(lines, 1):
        stripped = line.rstrip('\n')
        if stripped and not stripped[0].isspace() and not stripped.startswith('#'):
            current_file = stripped.strip()
        if current_file:
            result[i] = current_file
    return result


def keyword_to_files(map_path: str, word: str) -> list:
    """Return list of files where *word* appears, in order of first occurrence."""
    import csv as _csv

    kw_path = os.path.join(os.path.dirname(os.path.abspath(map_path)), 'keyword.txt')
    if not os.path.exists(kw_path):
        return []

    line_nums = []
    _csv.field_size_limit(10_000_000)
    with open(kw_path, encoding='utf-8', newline='') as f:
        reader = _csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) >= 3 and row[0] == word:
                line_nums = [int(x) for x in row[2].split(';') if x]
                break

    if not line_nums:
        return []

    line_to_file = _build_line_to_file(map_path)
    seen: set = set()
    files = []
    for ln in line_nums:
        f = line_to_file.get(ln)
        if f and f not in seen:
            seen.add(f)
            files.append(f)
    return files


def keyword_index(map_path: str) -> tuple[str, int]:
    """Scan map.txt, extract all identifier tokens, save to keyword.txt (CSV).

    Returns (keyword_path, word_count).
    CSV columns: word, count, lines  (semicolon-separated line numbers in map.txt)
    """
    import csv
    from collections import defaultdict

    with open(map_path, encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    token_re = re.compile(r'[a-zA-Z_][a-zA-Z0-9_]{1,}')
    word_lines: dict = defaultdict(set)
    for lineno, line in enumerate(lines, 1):
        for m in token_re.finditer(line):
            word_lines[m.group()].add(lineno)

    kw_path = os.path.join(os.path.dirname(os.path.abspath(map_path)), 'keyword.txt')
    sorted_words = sorted(word_lines, key=str.lower)
    with open(kw_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['word', 'count', 'lines'])
        for word in sorted_words:
            lns = sorted(word_lines[word])
            w.writerow([word, len(lns), ';'.join(str(l) for l in lns)])

    return kw_path, len(sorted_words)


def keyword_extract(
    map_path: str,
    source: str,
    fuzzy: bool = False,
    like: bool = False,
    show_counts: bool = False,
    csv_out: bool = False,
    sort_alpha: bool = False,
    show_origin: bool = False,
    sort_count: bool = False,
) -> str:
    """Extract real codebase identifiers from source text (or file path).

    Looks up words in keyword.txt (built by keyword_index).
    fuzzy=True → subword match: splits both query and keyword, matches if ALL
                 query subwords (≥5 chars) appear in the keyword's subwords.
    like=True  → substring match: each query token matches any keyword that
                 contains it as a case-insensitive substring (%token%).
    default    → exact identifier match.
    """
    import csv as _csv

    kw_path = os.path.join(os.path.dirname(os.path.abspath(map_path)), 'keyword.txt')
    if not os.path.exists(kw_path):
        return f"keyword.txt not found: {kw_path}\nRun: svitovyd keywords index"

    # load keyword vocab
    _csv.field_size_limit(10_000_000)
    kw_freq: dict = {}
    with open(kw_path, encoding='utf-8', newline='') as f:
        reader = _csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) >= 2:
                try:
                    kw_freq[row[0]] = int(row[1])
                except ValueError:
                    pass

    # resolve source: file or inline text
    if os.path.exists(source):
        with open(source, encoding='utf-8', errors='replace') as f:
            text = f.read()
    else:
        text = source

    token_re = re.compile(r'[a-zA-Z_][a-zA-Z0-9_]{1,}')
    seen: dict = {}  # keyword → order of first match

    if fuzzy:
        kw_parts = {kw: frozenset(_split_identifier(kw)) for kw in kw_freq}
        for i, m in enumerate(token_re.finditer(text)):
            query_parts = frozenset(
                w for w in _split_identifier(m.group()) if len(w) >= 5
            )
            if not query_parts:
                continue
            for kw, kp in kw_parts.items():
                if query_parts <= kp and kw not in seen:
                    seen[kw] = i
    elif like:
        for i, m in enumerate(token_re.finditer(text)):
            token = m.group().lower()
            for j, kw in enumerate(kw_freq):
                if token in kw.lower() and kw not in seen:
                    seen[kw] = i * 100000 + j
    else:
        kw_set = set(kw_freq)
        for i, m in enumerate(token_re.finditer(text)):
            w = m.group()
            if w in kw_set and w not in seen:
                seen[w] = i

    if not seen:
        return '(no matching keywords found)'

    if sort_alpha:
        result = sorted(seen, key=lambda w: w.lower())
    elif sort_count or show_counts:
        result = sorted(seen, key=lambda w: (-kw_freq[w], w.lower()))
    else:
        result = sorted(seen, key=lambda w: (seen[w], w.lower()))

    if not show_origin:
        items = [f"{w}({kw_freq[w]})" if show_counts else w for w in result]
        return ', '.join(items) if csv_out else '\n'.join(items)

    line_to_file = _build_line_to_file(map_path)
    import csv as _csv2
    _csv2.field_size_limit(10_000_000)
    kw_path = os.path.join(os.path.dirname(os.path.abspath(map_path)), 'keyword.txt')
    kw_lines: dict = {}
    with open(kw_path, encoding='utf-8', newline='') as f:
        reader = _csv2.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) >= 3 and row[0] in seen:
                kw_lines[row[0]] = [int(x) for x in row[2].split(';') if x]

    lines_out = []
    for w in result:
        label = f"{w}({kw_freq[w]})" if show_counts else w
        files: list = []
        seen_files: set = set()
        for ln in kw_lines.get(w, []):
            f = line_to_file.get(ln)
            if f and f not in seen_files:
                seen_files.add(f)
                files.append(f)
        if files:
            lines_out.append(f"{label} -> {', '.join(files)}")
        else:
            lines_out.append(label)
    return '\n'.join(lines_out)


def keywords_map(map_path: str, k: int = 50, plain: bool = False) -> str:
    """Top-K identifiers ranked by reference count.

    plain=True  → one identifier per line (for piping)
    plain=False → ranked table with count and defining file
    """
    defines_map, links_map = parse_map(map_path)

    ref_count: dict[str, int] = {}
    for targets in links_map.values():
        for refs in targets.values():
            for name in refs:
                ref_count[name] = ref_count.get(name, 0) + 1

    all_defines = {name: frel for frel, defs in defines_map.items() for name in defs}
    ranked = sorted(all_defines, key=lambda n: (-ref_count.get(n, 0), n))[:k]

    if plain:
        return '\n'.join(ranked)

    lines = [f"top-{k} identifiers by reference count  (total defined: {len(all_defines)})", ""]
    for i, name in enumerate(ranked, 1):
        lines.append(f"  {i:>3}.  {ref_count.get(name, 0):>4}  {name:<40}  {all_defines[name]}")
    return '\n'.join(lines)


# ── symmetry ─────────────────────────────────────────────────────────────────────

def sym_report(map_path: str, k: int = 5) -> str:
    """Asymmetry and cohesion health report."""
    defines_map, links_map = parse_map(map_path)

    all_defines: dict = {}
    for frel, defs in defines_map.items():
        for name in defs:
            all_defines[name] = frel

    called_names: set = set()
    for targets in links_map.values():
        for refs in targets.values():
            called_names.update(refs.keys())

    orphans = {name: frel for name, frel in all_defines.items()
               if name not in called_names}

    name_calls: dict = {}
    for caller, targets in links_map.items():
        for target, refs in targets.items():
            for name in refs:
                name_calls.setdefault(name, []).append((caller, target))

    out_degree = {name: len({c for c, _ in calls})
                  for name, calls in name_calls.items()}
    top_k = sorted(out_degree, key=lambda n: -out_degree[n])[:k]

    fractions = []
    for name in top_k:
        calls = name_calls[name]
        intra = sum(1 for c, t in calls
                    if os.path.dirname(c) == os.path.dirname(t))
        fractions.append(intra / len(calls))
    cohesion = sum(fractions) / len(fractions) if fractions else 0.0

    orphan_pct = (len(orphans) / len(all_defines) * 100) if all_defines else 0.0
    lines = [
        f"ASYMMETRY_SCORE = {orphan_pct:.1f}%  "
        f"({len(orphans)} orphans / {len(all_defines)} defines)",
        f"COHESION@{k}    = {cohesion:.2f}",
        f"top-{k} hotspots: {', '.join(top_k)}",
    ]
    if orphans:
        lines.append(f"\northan identifiers ({len(orphans)}):")
        for name in sorted(orphans)[:20]:
            lines.append(f"  {name:<40} ← {orphans[name]}")
        if len(orphans) > 20:
            lines.append(f"  … and {len(orphans) - 20} more")
    return '\n'.join(lines)


# ── idiff ─────────────────────────────────────────────────────────────────────────

def idiff_report(map_prev: str, map_curr: str) -> str:
    """Structural diff between two map snapshots."""
    dm_prev, lm_prev = parse_map(map_prev)
    dm_curr, lm_curr = parse_map(map_curr)

    def _orphans(dm, lm):
        all_defs = {n: f for f, defs in dm.items() for n in defs}
        called   = {n for targets in lm.values() for refs in targets.values() for n in refs}
        return {n: f for n, f in all_defs.items() if n not in called}

    orphans_prev = _orphans(dm_prev, lm_prev)
    orphans_curr = _orphans(dm_curr, lm_curr)
    delta        = len(orphans_curr) - len(orphans_prev)
    new_orphans  = {n: f for n, f in orphans_curr.items() if n not in orphans_prev}
    healed       = {n: f for n, f in orphans_prev.items() if n not in orphans_curr}

    prev_targets: set = set()
    for targets in lm_prev.values():
        prev_targets.update(targets.keys())
    deleted = prev_targets - set(dm_curr.keys())
    ghosts: dict = {}
    for f in deleted:
        called_names: set = set()
        for targets in lm_prev.values():
            if f in targets:
                called_names.update(targets[f].keys())
        if called_names:
            ghosts[f] = sorted(called_names)

    label = 'DEGRADATION' if delta > 0 else ('HEALING' if delta < 0 else 'NEUTRAL')
    lines = [
        f'ORPHAN_DRIFT = {delta:+d}  [{label}]',
        f'  before: {len(orphans_prev)} orphans',
        f'  after:  {len(orphans_curr)} orphans',
    ]
    if new_orphans:
        lines.append(f'\nnew orphans (+{len(new_orphans)}):')
        for name in sorted(new_orphans):
            lines.append(f'  + {name:<40} ← {new_orphans[name]}')
    if healed:
        lines.append(f'\nhealed orphans (-{len(healed)}):')
        for name in sorted(healed):
            lines.append(f'  - {name:<40} ← {healed[name]}')
    if ghosts:
        lines.append(f'\n! GHOST ALERT — {len(ghosts)} deleted file(s) had active callers:')
        for f in sorted(ghosts):
            lines.append(f'  ! {f}')
            lines.append(f'    called: {", ".join(ghosts[f])}')

    return '\n'.join(lines)
