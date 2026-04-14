"""svitovyd MCP server — tools: map_index, map_find, map_trace, map_deps, map_sym, map_idiff.

Stdio (local):
  svitovyd-mcp

HTTP/SSE (LAN):
  svitovyd-mcp --http --port 8766 --host 0.0.0.0
  pip install svitovyd[http]

Connect from Claude Code / opencode / nanocoder / 1bcoder:
  /mcp connect svitovyd http://localhost:8766/sse
"""
from __future__ import annotations

import argparse
import os
import sys

from mcp.server.fastmcp import FastMCP

from .indexer import build_map
from .query import find_map, trace_map, deps_map, sym_report, idiff_report

mcp = FastMCP("svitovyd")

_DEFAULT_MAP = ".svitovyd/map.txt"
_MAP_FILE: str = _DEFAULT_MAP   # overridable via --map-file at startup


# ── tools ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def map_index(
    path: str = ".",
    depth: int = 2,
    map_file: str = "",
) -> str:
    """Scan a directory and build (or update) the project map.

    path      directory to scan (default: current directory)
    depth     2 = definitions + links (default);  3 = also vars/params
    map_file  output path (default: <path>/.svitovyd/map.txt)
    """
    try:
        root = os.path.abspath(path)
        if not os.path.isdir(root):
            return f"ERROR: not a directory: {root}"

        depth = max(2, min(depth, 3))
        out_path = map_file or _MAP_FILE or os.path.join(root, ".svitovyd", "map.txt")
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

        map_text = build_map(root, depth, map_path=out_path)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(map_text)

        lines = map_text.count("\n") + 1
        files = sum(1 for l in map_text.splitlines() if l and not l.startswith(" ") and not l.startswith("#"))
        return f"Map built: {files} files, {lines} lines → {out_path}"
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def map_find(
    query: str,
    map_file: str = "",
) -> str:
    """Filter map blocks by filename and/or content.

    Token syntax:
      term    filename contains term
      !term   exclude if filename contains term
      \\term  include block if any child line contains term
      \\!term exclude block if any child line contains term
      -term   show ONLY child lines containing term
      -!term  hide child lines containing term

    Examples:
      query="auth"
      query="auth \\UserService !test"
      query="controller -defines"
    """
    try:
        mp = _resolve_map(map_file)
        hits, result = find_map(mp, query)
        if not query.strip():
            return result
        if hits:
            return result + f"\n\n[{len(hits)} match(es)]"
        return f"[no matches for: {query}]"
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def map_trace(
    identifier: str,
    depth: int = 8,
    map_file: str = "",
) -> str:
    """BFS backwards through the call graph — who calls this identifier?

    identifier  function/class name defined in the codebase
    depth       max BFS depth (default: 8)

    Shows the reverse dependency chain:
      start_file  [defines identifier]
        ← call:name  caller_file
          ← import:name  caller_of_caller
    """
    try:
        mp = _resolve_map(map_file)
        result = trace_map(mp, identifier, max_depth=depth)
        if result is None:
            return (f"'{identifier}' not found in any defines.\n"
                    f"Hint: try  map_find query=\"\\{identifier}\"  to search by content.")
        return result
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def map_deps(
    identifier: str,
    depth: int = 8,
    map_file: str = "",
) -> str:
    """BFS forward through the dependency graph — what does this identifier depend on?

    identifier  function/class name OR file path substring
    depth       max BFS depth (default: 8)

    Shows forward dependency chain:
      start_file
        → call:name  dependency_file
          → import:name  transitive_dependency
    """
    try:
        mp = _resolve_map(map_file)
        result = deps_map(mp, identifier, max_depth=depth)
        if result is None:
            return (f"'{identifier}' not found in defines or file paths.\n"
                    f"Hint: try  map_find query=\"{identifier}\"")
        return result
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def map_sym(
    k: int = 5,
    map_file: str = "",
) -> str:
    """Asymmetry and cohesion health report.

    ASYMMETRY_SCORE = % of defined identifiers never referenced by any other file (orphans).
    COHESION@K      = fraction of top-K hotspot calls that stay within the same module.

    High ASYMMETRY → many dead/untested symbols.
    Low  COHESION  → high coupling across modules.
    """
    try:
        mp = _resolve_map(map_file)
        return sym_report(mp, k=k)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def map_idiff(
    prev_map_file: str,
    map_file: str = "",
) -> str:
    """Structural diff between two map snapshots.

    Reports:
      ORPHAN_DRIFT  delta in orphan count since last snapshot
      GHOST ALERT   files deleted that other files still referenced

    Workflow:
      cp .svitovyd/map.txt .svitovyd/map.prev.txt
      svitovyd index .
      map_idiff prev_map_file=".svitovyd/map.prev.txt"
    """
    try:
        mp = _resolve_map(map_file)
        if not os.path.exists(prev_map_file):
            return f"ERROR: prev map not found: {prev_map_file}"
        return idiff_report(prev_map_file, mp)
    except Exception as e:
        return f"ERROR: {e}"


# ── helpers ────────────────────────────────────────────────────────────────────

def _resolve_map(map_file: str) -> str:
    path = map_file or _MAP_FILE
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Map file not found: {path}\n"
            f"Run: svitovyd index .  (or  map_index path='.')"
        )
    return path


# ── entry point ────────────────────────────────────────────────────────────────

def main():
    global _MAP_FILE

    parser = argparse.ArgumentParser(prog="svitovyd-mcp")
    parser.add_argument("--http", action="store_true",
                        help="HTTP/SSE transport instead of stdio")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--map-file", default=None,
                        help="Default map file for all tools (default: .svitovyd/map.txt)")
    args = parser.parse_args()

    if args.map_file:
        _MAP_FILE = args.map_file

    print(f"[svitovyd] map file: {_MAP_FILE}", file=sys.stderr, flush=True)

    if args.http:
        try:
            import uvicorn  # noqa: F401
        except ImportError:
            print("HTTP transport requires uvicorn: pip install svitovyd[http]",
                  file=sys.stderr)
            sys.exit(1)
        print(f"[svitovyd] MCP server — http://{args.host}:{args.port}/sse",
              file=sys.stderr, flush=True)
        print(f"Connect:  /mcp connect svitovyd http://<host>:{args.port}/sse",
              file=sys.stderr, flush=True)
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
