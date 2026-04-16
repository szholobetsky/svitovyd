# svitovyd

Project map builder and structural query tool for codebases.

Scans any language codebase and produces a text map of:
- defined identifiers (classes, functions, endpoints, tables, …)
- cross-file references with relationship types (`import / call / ref / expr`)
- optionally variables and parameters (depth 3)

Query the map with `find`, `trace` (who calls?), `deps` (what depends on?), `sym` (health), `idiff` (structural diff).

Available as **CLI** and **MCP server** — works with Claude Code, opencode, nanocoder, 1bcoder, Cursor, and any MCP-compatible agent.

---

## Installation

```bash
# CLI only
pip install svitovyd

# CLI + MCP (stdio)
pip install "svitovyd[mcp]"

# CLI + MCP + HTTP/SSE transport (for remote/LAN connections)
pip install "svitovyd[http]"

# CLI + web UI (Gradio)
pip install "svitovyd[ui]"
```

---

## Quick start (CLI)

```bash
# Build map for current directory
svitovyd index .
svitovyd index . 3          # depth 3: also variables and parameters

# Search
svitovyd find auth
svitovyd find controller !test
svitovyd find "\UserService"          # blocks containing UserService
svitovyd find "\format_mismatch -format_mismatch"  # show only lines with term

# Trace call chain
svitovyd trace insertEmail            # who calls insertEmail?
svitovyd deps DatabaseManager         # what does DatabaseManager depend on?

# Health report
svitovyd sym --k 10

# Keyword vocabulary
svitovyd keywords index               # build .svitovyd/keyword.txt
svitovyd keywords extract "add author field to Book class" -f   # fuzzy extract
svitovyd keywords                     # top-50 identifiers by reference count

# Structural diff (after changes)
cp .svitovyd/map.txt .svitovyd/map.prev.txt
svitovyd index .
svitovyd idiff --prev .svitovyd/map.prev.txt
```

---

## Keywords

The keyword system bridges natural language task descriptions to real codebase identifiers. Two-step workflow:

**Step 1 — build the vocabulary index:**
```bash
svitovyd index .
svitovyd keywords index
# → .svitovyd/keyword.txt  (word, frequency, line numbers — CSV)
```

**Step 2 — extract identifiers from a task description:**
```bash
svitovyd keywords extract "add author field to Book class" -f
# → Book, author, addAuthor, BookRepository, …
```

Then use the extracted identifiers in `find` or `trace`:
```bash
svitovyd find "\Book"
svitovyd trace BookRepository
```

### Extract flags

| Flag | Meaning |
|---|---|
| `-f` | Fuzzy subword match — splits camelCase/snake_case, matches if all query subwords (≥5 chars) appear in the identifier |
| `-n` | Show frequency count next to each identifier: `Book(47)` |
| `-c` | Comma-separated output (default: one per line) |
| `-a` | Sort alphabetically (default: order of appearance in text) |

**Exact match** (no `-f`): query word must exactly match a keyword.txt entry — faster, no false positives.

**Fuzzy match** (`-f`): `"format mismatch"` matches `formatParameterMismatch`, `format_mismatch`, `FormatMismatch`. Use this for task descriptions written in natural language.

### Ranked list (no task text)

```bash
svitovyd keywords           # top 50 by reference count
svitovyd keywords --k 100   # top 100
svitovyd keywords --plain   # one per line, for piping
```

---

## Web UI

Browse the project map from a browser — useful when svitovyd runs on a remote machine or LAN server.

```bash
pip install "svitovyd[ui]"

svitovyd ui                        # opens at http://localhost:7860
svitovyd ui --port 7861            # custom port
svitovyd ui --map /path/to/map.txt # explicit map file
```

Binds to `0.0.0.0` by default, so it is immediately accessible from any machine on the same LAN:

```
http://192.168.1.42:7860
```

Tabs: **Find** · **Trace** · **Deps** · **Sym** · **Keywords** · **Idiff** · **Download**

The **Keywords** tab accepts an optional task description — enter text and it runs fuzzy identifier extraction; leave empty to get the ranked list. The **Download** tab lets you download `map.txt` and `keywords.txt` directly from the browser (useful when svitovyd runs on a remote server).

---

## MCP server

The MCP server exposes 6 tools to any connected agent:

| Tool | Description |
|---|---|
| `map_index` | Build or update the project map |
| `map_find` | Filter map blocks by filename/content |
| `map_trace` | BFS backwards — who calls this identifier? |
| `map_deps` | BFS forward — what does this depend on? |
| `map_sym` | Asymmetry and cohesion health report |
| `map_idiff` | Structural diff between two map snapshots |

### Start the server

**Stdio** (for local agents — Claude Code, 1bcoder):
```bash
svitovyd-mcp
```

**HTTP/SSE** (for remote agents — opencode, nanocoder, LAN):
```bash
svitovyd-mcp --http --port 8766
# or
svitovyd serve --http --port 8766
```

With a specific map file:
```bash
svitovyd-mcp --http --port 8766 --map-file /path/to/project/.svitovyd/map.txt
```

---

## Setup per agent

### Claude Code

Add to `.claude/settings.json` in your project or `~/.claude/settings.json` globally:

```json
{
  "mcpServers": {
    "svitovyd": {
      "command": "svitovyd-mcp",
      "args": []
    }
  }
}
```

With a specific map file:
```json
{
  "mcpServers": {
    "svitovyd": {
      "command": "svitovyd-mcp",
      "args": ["--map-file", "/path/to/project/.svitovyd/map.txt"]
    }
  }
}
```

### opencode

Start the HTTP server first:
```bash
svitovyd-mcp --http --port 8766
```

Add to your opencode config (`~/.config/opencode/config.json` or project-local):
```json
{
  "mcp": {
    "svitovyd": {
      "type": "sse",
      "url": "http://localhost:8766/sse"
    }
  }
}
```

Or connect interactively if opencode supports it:
```
/mcp connect svitovyd http://localhost:8766/sse
```

### nanocoder

Start the HTTP server:
```bash
svitovyd-mcp --http --port 8766
```

Add to nanocoder config:
```json
{
  "mcpServers": {
    "svitovyd": {
      "url": "http://localhost:8766/sse"
    }
  }
}
```

### 1bcoder

```
/mcp connect svitovyd http://localhost:8766/sse
```

Or add to `.1bcoder/mcp.yaml` for auto-connect:
```yaml
servers:
  - name: svitovyd
    url: http://localhost:8766/sse
```

### Cursor

Add to `.cursor/mcp.json` in your project:
```json
{
  "mcpServers": {
    "svitovyd": {
      "command": "svitovyd-mcp",
      "args": []
    }
  }
}
```

### Any MCP-compatible client (generic)

**Stdio transport** — command: `svitovyd-mcp`

**SSE transport** — start server then connect to: `http://localhost:8766/sse`

---

## MCP tools reference

### `map_index`
```
path      directory to scan (default: ".")
depth     2 = definitions + links (default)
          3 = also variables and parameters
map_file  output path (default: <path>/.svitovyd/map.txt)
```

### `map_find`
```
query     filter string — token syntax:
            term    filename contains term
            !term   exclude if filename contains term
            \term   include block if any child line contains term
            \!term  exclude block if any child line contains term
            -term   show ONLY child lines containing term
            -!term  hide child lines containing term
map_file  map file to query (default: .svitovyd/map.txt)
```

### `map_trace`
```
identifier  function/class name defined in the codebase
depth       max BFS depth (default: 8)
map_file    map file to query
```

### `map_deps`
```
identifier  function/class name OR file path substring
depth       max BFS depth (default: 8)
map_file    map file to query
```

### `map_sym`
```
k           top-K hotspots for cohesion score (default: 5)
map_file    map file to query
```

### `map_idiff`
```
prev_map_file   path to previous map snapshot (required)
map_file        current map file (default: .svitovyd/map.txt)
```

---

## Supported languages

`.py` `.js` `.ts` `.java` `.cs` `.go` `.rs` `.cpp` `.c` `.h`
`.rb` `.php` `.kt` `.scala` `.swift` `.lua`
`.html` `.css` `.jsx` `.tsx` `.vue` `.svelte`
`.sql` `.yaml` `.yml` `.toml` `.json` `.xml`
`.tf` `.hcl` `.sh` `.bat` `.ps1`

---

## Typical workflow with an AI agent

```
1. svitovyd index .                     # or: map_index path="."
2. svitovyd keywords index              # build keyword vocabulary
3. svitovyd keywords extract "task description" -f -c  # get real identifiers
4. map_find query="auth"                # explore by identifier / filename
5. map_trace identifier="login"         # understand call chain
6. map_deps identifier="DatabaseManager"# understand dependencies
7. map_sym                              # health check before refactoring
8. [make changes]
9. cp .svitovyd/map.txt .svitovyd/map.prev.txt
10. map_index path="."                  # rebuild
11. map_idiff prev_map_file=".svitovyd/map.prev.txt"  # verify impact
```

---

## Part of the SIMARGL toolkit

svitovyd is one of four tools that together form an **intellectual development support system**:

| Tool | Role |
|---|---|
| **[simargl](https://github.com/szholobetsky/simargl)** | Task-to-code retrieval — given a task description, finds which files and modules are likely affected, using semantic similarity over git history |
| **[svitovyd](https://github.com/szholobetsky/svitovyd)** | Project map — scans any codebase and produces a structural map of definitions and cross-file dependencies; exposes it as an MCP server |
| **[1bcoder](https://github.com/szholobetsky/1bcoder)** | AI coding assistant for small local models — surgical context management, agents, parallel inference, proc scripts |
| **[yasna](https://github.com/szholobetsky/yasna)** | Session memory — indexes conversations from all AI agents so you can find what was discussed, when, and where |

- **simargl** answers: *what code is related to this task?*
- **svitovyd** answers: *how is the code structured and what depends on what?*
- **1bcoder** answers: *how do I work with local models efficiently?*
- **yasna** answers: *where did I already discuss this?*

Together they cover the full development loop: understand the codebase, find relevant history, work with AI locally, remember what was decided.

The name comes from Slavic mythology. Svitovyd (Світовид) is the four-faced god who sees all directions simultaneously — past, future, war, and harvest. A fitting name for a tool that maps an entire codebase at once.

---

## About

(c) 2026 Stanislav Zholobetskyi  
Institute for Information Recording, National Academy of Sciences of Ukraine, Kyiv  
PhD research: «Intelligent Technology for Software Development and Maintenance Support»
