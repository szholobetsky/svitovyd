"""svitovyd CLI entry point.

Usage:
  svitovyd index [path] [depth] [--out FILE] [--stdout]
  svitovyd find  [tokens ...] [--map FILE]
  svitovyd trace <identifier>  [--map FILE]
  svitovyd deps  <identifier>  [--map FILE]
  svitovyd sym   [--k N]       [--map FILE]
  svitovyd idiff --prev FILE   [--map FILE]
"""
from __future__ import annotations

import argparse
import os
import sys

DEFAULT_MAP = os.path.join('.svitovyd', 'map.txt')


def _map_path_arg(p):
    p.add_argument('--map', metavar='FILE', default=DEFAULT_MAP,
                   help=f'Map file (default: {DEFAULT_MAP})')


def main():
    parser = argparse.ArgumentParser(
        prog='svitovyd',
        description='Project map builder and query tool.',
    )
    sub = parser.add_subparsers(dest='cmd')

    # index
    p_idx = sub.add_parser('index', help='Scan directory and build map file')
    p_idx.add_argument('path', nargs='?', default='.',
                       help='Directory to scan (default: current directory)')
    p_idx.add_argument('depth', nargs='?', type=int, default=None,
                       help='2=definitions+links (default), 3=also vars/params')
    p_idx.add_argument('-d', '--depth-flag', type=int, default=None,
                       dest='depth_flag', metavar='N',
                       help='Depth (alias for positional depth argument)')
    p_idx.add_argument('--out', metavar='FILE',
                       help=f'Output file (default: {DEFAULT_MAP})')
    p_idx.add_argument('--stdout', action='store_true',
                       help='Also print map to stdout')

    # find
    p_find = sub.add_parser('find', help='Filter map blocks by filename/content')
    p_find.add_argument('query', nargs=argparse.REMAINDER,
                        help='Filter tokens: term  !term  \\term  \\!term  -term  -!term')
    _map_path_arg(p_find)

    # trace
    p_trace = sub.add_parser('trace', help='BFS backwards: who calls this identifier?')
    p_trace.add_argument('identifier', help='Identifier name to trace')
    p_trace.add_argument('--depth', type=int, default=8)
    _map_path_arg(p_trace)

    # deps
    p_deps = sub.add_parser('deps', help='BFS forward: what does this identifier depend on?')
    p_deps.add_argument('identifier', help='Identifier name or file substring')
    p_deps.add_argument('--depth', type=int, default=8)
    _map_path_arg(p_deps)

    # sym
    p_sym = sub.add_parser('sym', help='Asymmetry and cohesion health report')
    p_sym.add_argument('--k', type=int, default=5, help='Top-K hotspots (default: 5)')
    _map_path_arg(p_sym)

    # keywords (+ sub-subcommands: index, extract)
    p_kw = sub.add_parser('keywords', help='Keyword vocabulary: index, extract, ranked list')
    # --map is global for all keywords sub-subcommands
    _map_path_arg(p_kw)
    p_kw.add_argument('--k', type=int, default=50, help='Top K for ranked list (default: 50)')
    p_kw.add_argument('--plain', action='store_true', help='One identifier per line (for piping)')
    kw_sub = p_kw.add_subparsers(dest='kw_cmd')

    # keywords index
    kw_sub.add_parser('index', help='Build .svitovyd/keyword.txt from map.txt')

    # keywords extract
    p_kw_ext = kw_sub.add_parser('extract', help='Extract real identifiers from text or file')
    p_kw_ext.add_argument('source', nargs='+', help='Inline text or path to a file')
    p_kw_ext.add_argument('-f', '--fuzzy', action='store_true',
                          help='Fuzzy subword match (splits camelCase/snake_case)')
    p_kw_ext.add_argument('-l', '--like', action='store_true',
                          help='Substring match: query token appears anywhere in keyword (%token%)')
    p_kw_ext.add_argument('-n', '--counts', action='store_true',
                          help='Show frequency count next to each identifier')
    p_kw_ext.add_argument('-c', '--csv', action='store_true',
                          help='Comma-separated output (default: one per line)')
    p_kw_ext.add_argument('-a', '--alpha', action='store_true',
                          help='Sort alphabetically (default: order of appearance)')
    p_kw_ext.add_argument('-s', '--sort-count', action='store_true',
                          help='Sort by codebase frequency descending')
    p_kw_ext.add_argument('-o', '--origin', action='store_true',
                          help='Show which files each keyword appears in')

    # idiff
    p_idiff = sub.add_parser('idiff', help='Structural diff between two map snapshots')
    p_idiff.add_argument('--prev', required=True, metavar='FILE',
                         help='Previous map snapshot')
    _map_path_arg(p_idiff)

    # ui
    p_ui = sub.add_parser('ui', help='Start Gradio web UI')
    p_ui.add_argument('--port', type=int, default=7860)
    p_ui.add_argument('--host', default='0.0.0.0')
    p_ui.add_argument('--map', metavar='FILE', default=DEFAULT_MAP,
                      help=f'Map file to open (default: {DEFAULT_MAP})')

    # about
    sub.add_parser('about', help='Show version and authorship')

    # serve (MCP)
    p_srv = sub.add_parser('serve', help='Start MCP server (stdio or HTTP/SSE)')
    p_srv.add_argument('--http', action='store_true')
    p_srv.add_argument('--host', default='0.0.0.0')
    p_srv.add_argument('--port', type=int, default=8766)
    p_srv.add_argument('--map-file', default=None,
                       help='Default map file for all MCP tools')

    args = parser.parse_args()

    if args.cmd == 'index':
        from .indexer import build_map

        root  = os.path.abspath(args.path)
        depth = max(2, min(args.depth_flag or args.depth or 2, 3))

        if not os.path.isdir(root):
            print(f"error: not a directory: {root}", file=sys.stderr)
            sys.exit(1)

        if args.out:
            out_path = args.out
        else:
            svitovyd_dir = os.path.join(root, '.svitovyd')
            os.makedirs(svitovyd_dir, exist_ok=True)
            out_path = os.path.join(svitovyd_dir, 'map.txt')

        print(f"[svitovyd] scanning {root} (depth {depth}) ...", file=sys.stderr)
        map_text = build_map(root, depth, map_path=out_path)

        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(map_text)

        lines = map_text.count('\n') + 1
        print(f"[svitovyd] {lines} lines → {out_path}", file=sys.stderr)

        if args.stdout:
            print(map_text)

    elif args.cmd == 'find':
        from .query import find_map
        _require_map(args.map)
        query = ' '.join(args.query)
        hits, result = find_map(args.map, query)
        if not query:
            print(result)
        elif hits:
            print(result)
            print(f'\n[svitovyd] {len(hits)} match(es)', file=sys.stderr)
        else:
            print(f'[svitovyd] no matches for: {query}', file=sys.stderr)
            sys.exit(1)

    elif args.cmd == 'trace':
        from .query import trace_map
        _require_map(args.map)
        result = trace_map(args.map, args.identifier, max_depth=args.depth)
        if result is None:
            print(f"[svitovyd] '{args.identifier}' not found in any defines", file=sys.stderr)
            print(f"hint: try:  svitovyd find \\{args.identifier}", file=sys.stderr)
            sys.exit(1)
        print(result)

    elif args.cmd == 'deps':
        from .query import deps_map
        _require_map(args.map)
        result = deps_map(args.map, args.identifier, max_depth=args.depth)
        if result is None:
            print(f"[svitovyd] '{args.identifier}' not found", file=sys.stderr)
            sys.exit(1)
        print(result)

    elif args.cmd == 'sym':
        from .query import sym_report
        _require_map(args.map)
        print(sym_report(args.map, k=args.k))

    elif args.cmd == 'keywords':
        if args.kw_cmd == 'index':
            from .query import keyword_index
            _require_map(args.map)
            kw_path, count = keyword_index(args.map)
            print(f"[svitovyd] {count} keywords → {kw_path}", file=sys.stderr)

        elif args.kw_cmd == 'extract':
            from .query import keyword_extract
            _require_map(args.map)
            source = ' '.join(args.source)
            print(keyword_extract(
                args.map, source,
                fuzzy=args.fuzzy,
                like=args.like,
                show_counts=args.counts,
                csv_out=args.csv,
                sort_alpha=args.alpha,
                show_origin=args.origin,
                sort_count=args.sort_count,
            ))

        else:
            from .query import keywords_map
            _require_map(args.map)
            print(keywords_map(args.map, k=args.k, plain=args.plain))

    elif args.cmd == 'idiff':
        from .query import idiff_report
        _require_map(args.map)
        if not os.path.exists(args.prev):
            print(f'error: prev map not found: {args.prev}', file=sys.stderr)
            sys.exit(1)
        print(idiff_report(args.prev, args.map))

    elif args.cmd == 'serve':
        argv = ['svitovyd-mcp']
        if args.http:
            argv += ['--http', '--host', args.host, '--port', str(args.port)]
        if args.map_file:
            argv += ['--map-file', args.map_file]
        sys.argv = argv
        from .mcp_server import main as mcp_main
        mcp_main()

    elif args.cmd == 'ui':
        from .ui import main as ui_main
        ui_main(port=args.port, host=args.host, map_path=args.map)

    elif args.cmd == 'about':
        print("svitovyd — Project map builder and structural query tool")
        print()
        print("(c) 2026 Stanislav Zholobetskyi")
        print("Institute for Information Recording, National Academy of Sciences of Ukraine, Kyiv")
        print("PhD research: \u00abIntelligent Technology for Software Development and Maintenance Support\u00bb")

    else:
        parser.print_help()
        sys.exit(1)


def _require_map(map_path: str):
    if not os.path.exists(map_path):
        print(f'error: map file not found: {map_path}', file=sys.stderr)
        print('hint:  run  svitovyd index .  first', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
