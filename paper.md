---
title: "svitovyd: A Language-Agnostic Project Map Builder and Structural Query Tool for AI-Assisted Development"
authors:
  - name: Stanislav Zholobetskyi
    orcid: 0009-0008-6058-7233
    affiliation: 1
affiliations:
  - name: Institute for Information Recording, Kyiv, Ukraine
    index: 1
date: 2026-04-14
bibliography: paper.bib
---

# Summary

`svitovyd` is a command-line tool and MCP (Model Context Protocol) server that scans a source code repository and produces a compact, human- and machine-readable structural map: defined identifiers (classes, functions, API endpoints, database tables), their locations, and cross-file relationships with typed edges (`import`, `call`, `ref`, `expr`). The map can be queried interactively — filtering by filename or content, tracing reverse call chains, resolving forward dependencies, reporting structural health metrics, and computing structural diffs between snapshots. The same functionality is exposed as an MCP server so that any connected AI coding agent can call it programmatically.

# Statement of need

AI coding assistants operating over large codebases face a fundamental tension: effective assistance requires structural understanding of the project, but loading entire file trees into context is infeasible within the token limits of any model. The common workaround — providing the model with a flat directory listing — gives it names but no relationships, no definitions, no call graph.

Existing solutions are either too heavyweight or too narrow. Universal Ctags [@ctags] and similar symbol indexers produce flat symbol tables without relationship information. Tree-sitter [@treesitter] provides precise AST parsing but requires language-specific grammars and does not produce a graph-level view suitable for context injection. Source graph tools such as Sourcetrail are interactive IDEs, not lightweight services queryable from a shell or an agent. Language Server Protocol (LSP) servers are per-language, per-IDE, and not designed for programmatic batch querying from an AI agent.

`svitovyd` occupies a different point in this space: it is language-agnostic (pattern-based extraction covering 35 file types), produces a single compact text artifact that fits in an agent context, supports BFS graph traversal for tracing call and dependency chains, and exposes everything through MCP — so a connected agent can answer "who calls this function?" or "what does this class depend on?" without loading a single source file.

# Functionality

**Indexing** (`svitovyd index`, `map_index`): scans a directory tree and builds a `.svitovyd/map.txt` file containing file blocks with defined symbols and outgoing reference edges. Incremental updates use file modification times. Depth 2 indexes definitions and links; depth 3 additionally indexes variables and parameters.

**Query commands** (`map_find`, `map_trace`, `map_deps`, `map_sym`, `map_idiff`): `find` filters map blocks by filename and content with a token syntax including negation, content inclusion, and child-line filtering. `trace` performs BFS over the reverse dependency graph (who calls X?). `deps` performs BFS over the forward graph (what does X depend on?). `sym` computes asymmetry and cohesion health metrics. `idiff` computes a structural diff between two map snapshots, reporting orphan drift and ghost file references.

**MCP server**: runs as a stdio or HTTP/SSE server, exposing all six tools to any MCP-compatible agent (Claude Code, opencode, Cursor, 1bcoder, nanocoder). Agents gain structural query capability without filesystem access or language-specific tooling.

# Related software

Universal Ctags [@ctags] is the closest predecessor but produces flat symbol lists without relationship information and does not expose an MCP interface. Sourcetrail provides a full dependency graph but is a GUI application, no longer maintained, and not suitable for programmatic querying. `svitovyd` is the only tool in this space that combines language-agnostic extraction, BFS graph queries, structural diff, and MCP server in a single lightweight package.

# Acknowledgements

This work is conducted as part of a PhD research programme at the Institute for Information Recording, Kyiv, Ukraine.

# References
