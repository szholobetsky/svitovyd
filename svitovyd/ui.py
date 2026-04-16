"""Gradio web UI for svitovyd.

Start:
  svitovyd ui                  # default port 7860
  svitovyd ui --port 7861
  svitovyd ui --map .svitovyd/map.txt

Tabs:
  Find     — filter map blocks by filename / content
  Trace    — BFS backwards: who calls this identifier?
  Deps     — BFS forward: what does this depend on?
  Sym      — asymmetry and cohesion health report
  Keywords — top-K identifiers ranked by reference count
  Idiff    — structural diff between two map snapshots
  Download — download map.txt and keywords.txt to local machine
"""
from __future__ import annotations

import os
import tempfile

DEFAULT_MAP = os.path.join('.svitovyd', 'map.txt')


def _require_map(map_path: str) -> str | None:
    if not os.path.exists(map_path):
        return f"Map file not found: {map_path}\nRun: svitovyd index ."
    return None


def _run_find(map_path, query):
    err = _require_map(map_path)
    if err:
        return err
    if not query.strip():
        return "Enter a query."
    from .query import find_map
    hits, result = find_map(map_path, query)
    if not hits:
        return f"No matches for: {query}"
    return f"{result}\n\n{len(hits)} match(es)"


def _run_trace(map_path, identifier, depth):
    err = _require_map(map_path)
    if err:
        return err
    if not identifier.strip():
        return "Enter an identifier."
    from .query import trace_map
    result = trace_map(map_path, identifier.strip(), max_depth=int(depth))
    if result is None:
        return f"'{identifier}' not found in any defines.\nTry: find \\{identifier}"
    return result


def _run_deps(map_path, identifier, depth):
    err = _require_map(map_path)
    if err:
        return err
    if not identifier.strip():
        return "Enter an identifier or file substring."
    from .query import deps_map
    result = deps_map(map_path, identifier.strip(), max_depth=int(depth))
    if result is None:
        return f"'{identifier}' not found."
    return result


def _run_sym(map_path, k):
    err = _require_map(map_path)
    if err:
        return err
    from .query import sym_report
    return sym_report(map_path, k=int(k))


def _run_keywords(map_path, k, task_text):
    err = _require_map(map_path)
    if err:
        return err
    if task_text.strip():
        from .query import keyword_extract
        result = keyword_extract(map_path, task_text.strip(), fuzzy=True)
        if result == '(no matching keywords found)':
            return result
        return f"Extracted identifiers (fuzzy):\n\n{result}"
    from .query import keywords_map
    return keywords_map(map_path, k=int(k))


def _run_idiff(map_path, prev_path):
    err = _require_map(map_path)
    if err:
        return err
    if not prev_path.strip() or not os.path.exists(prev_path.strip()):
        return f"Previous map file not found: {prev_path}"
    from .query import idiff_report
    return idiff_report(prev_path.strip(), map_path)


def _download_map(map_path):
    """Return map.txt path for browser download, or a temp error file."""
    if not os.path.exists(map_path):
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='_error.txt',
                                          delete=False, encoding='utf-8')
        tmp.write(f"Map file not found: {map_path}\nRun: svitovyd index .")
        tmp.close()
        return tmp.name
    return map_path


def _download_keywords(map_path, filter_top_k, k):
    """Download keyword.txt — full vocabulary or filtered to top-K."""
    err = _require_map(map_path)
    if err:
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='_error.txt',
                                          delete=False, encoding='utf-8')
        tmp.write(err)
        tmp.close()
        return tmp.name

    kw_path = os.path.join(os.path.dirname(os.path.abspath(map_path)), 'keyword.txt')

    if not filter_top_k:
        # return the full keyword.txt built by `keywords index`
        if not os.path.exists(kw_path):
            tmp = tempfile.NamedTemporaryFile(mode='w', suffix='_error.txt',
                                              delete=False, encoding='utf-8')
            tmp.write(f"keyword.txt not found: {kw_path}\n"
                      f"Run: svitovyd keywords index")
            tmp.close()
            return tmp.name
        return kw_path

    # filtered: top-K plain list by reference count
    from .query import keywords_map
    content = keywords_map(map_path, k=int(k), plain=True)
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='_keywords.txt',
                                      delete=False, encoding='utf-8')
    tmp.write(content)
    tmp.close()
    return tmp.name


def build_app(map_path: str = DEFAULT_MAP):
    try:
        import gradio as gr
    except ImportError:
        raise ImportError("Gradio not installed. Run: pip install \"svitovyd[ui]\"")

    project_root = os.path.abspath(os.path.join(map_path, '..', '..'))
    project_name = os.path.basename(project_root)

    with gr.Blocks(title=f"svitovyd — {project_name}", theme=gr.themes.Monochrome()) as app:
        gr.Markdown(f"## svitovyd — project map :: {project_name}")

        map_box = gr.Textbox(value=map_path, label="Map file", scale=4)

        with gr.Tabs():

            # ── Find ──────────────────────────────────────────────────────
            with gr.Tab("Find"):
                gr.Markdown(
                    "Filter map blocks. Syntax: `term` `!term` `\\term` `\\!term` `-term` `-!term`"
                )
                find_query = gr.Textbox(label="Query", placeholder="auth !test")
                find_btn   = gr.Button("Find", variant="primary")
                find_out   = gr.Code(language=None, label="Result")
                find_btn.click(_run_find, inputs=[map_box, find_query], outputs=find_out)
                find_query.submit(_run_find, inputs=[map_box, find_query], outputs=find_out)

            # ── Trace ─────────────────────────────────────────────────────
            with gr.Tab("Trace"):
                gr.Markdown("BFS backwards — who calls this identifier?")
                trace_id    = gr.Textbox(label="Identifier", placeholder="insertEmail")
                trace_depth = gr.Slider(1, 16, value=8, step=1, label="Max depth")
                trace_btn   = gr.Button("Trace", variant="primary")
                trace_out   = gr.Code(language=None, label="Result")
                trace_btn.click(_run_trace,
                                inputs=[map_box, trace_id, trace_depth], outputs=trace_out)

            # ── Deps ──────────────────────────────────────────────────────
            with gr.Tab("Deps"):
                gr.Markdown("BFS forward — what does this identifier depend on?")
                deps_id    = gr.Textbox(label="Identifier or file substring",
                                        placeholder="DatabaseManager")
                deps_depth = gr.Slider(1, 16, value=8, step=1, label="Max depth")
                deps_btn   = gr.Button("Deps", variant="primary")
                deps_out   = gr.Code(language=None, label="Result")
                deps_btn.click(_run_deps,
                               inputs=[map_box, deps_id, deps_depth], outputs=deps_out)

            # ── Sym ───────────────────────────────────────────────────────
            with gr.Tab("Sym"):
                gr.Markdown("Asymmetry and cohesion health report.")
                sym_k   = gr.Slider(1, 20, value=5, step=1, label="Top-K hotspots")
                sym_btn = gr.Button("Run", variant="primary")
                sym_out = gr.Code(language=None, label="Result")
                sym_btn.click(_run_sym, inputs=[map_box, sym_k], outputs=sym_out)

            # ── Keywords ──────────────────────────────────────────────────
            with gr.Tab("Keywords"):
                gr.Markdown(
                    "Enter a task description to extract matching identifiers (fuzzy). "
                    "Leave empty to see top-K identifiers ranked by reference count."
                )
                kw_task = gr.Textbox(label="Task description (optional)",
                                     placeholder="add author field to Book class")
                kw_k    = gr.Slider(10, 200, value=50, step=10,
                                    label="Top K (used when task is empty)")
                kw_btn  = gr.Button("Extract", variant="primary")
                kw_out  = gr.Code(language=None, label="Result")
                kw_btn.click(_run_keywords, inputs=[map_box, kw_k, kw_task], outputs=kw_out)
                kw_task.submit(_run_keywords, inputs=[map_box, kw_k, kw_task], outputs=kw_out)

            # ── Idiff ─────────────────────────────────────────────────────
            with gr.Tab("Idiff"):
                gr.Markdown("Structural diff between two map snapshots.")
                idiff_prev = gr.Textbox(label="Previous map file",
                                        placeholder=".svitovyd/map.prev.txt")
                idiff_btn  = gr.Button("Diff", variant="primary")
                idiff_out  = gr.Code(language=None, label="Result")
                idiff_btn.click(_run_idiff,
                                inputs=[map_box, idiff_prev], outputs=idiff_out)

            # ── Download ──────────────────────────────────────────────────
            with gr.Tab("Download"):
                gr.Markdown(
                    "Download files from the remote server to your local machine.\n\n"
                    "**map.txt** — copy to `.1bcoder/map.txt` to use with 1bcoder `/map` commands.\n\n"
                    "**keyword.txt** — full vocabulary (all tokens + counts) built by "
                    "`svitovyd keywords index`. Required for `keyword extract`. "
                    "Check *Filter to top K* to download a smaller plain list instead."
                )
                with gr.Row():
                    dl_map_btn = gr.Button("Prepare map.txt", variant="primary")

                dl_map_file = gr.File(label="map.txt", interactive=False)

                gr.Markdown("---")

                with gr.Row():
                    dl_kw_filter = gr.Checkbox(label="Filter to top K only", value=False)
                    dl_kw_k      = gr.Slider(10, 500, value=100, step=10,
                                             label="Top K (used when filter is on)")
                    dl_kw_btn    = gr.Button("Prepare keyword.txt", variant="primary")

                dl_kw_file = gr.File(label="keyword.txt", interactive=False)

                dl_map_btn.click(_download_map,
                                 inputs=[map_box],
                                 outputs=dl_map_file)
                dl_kw_btn.click(_download_keywords,
                                inputs=[map_box, dl_kw_filter, dl_kw_k],
                                outputs=dl_kw_file)

    return app


def main(port: int = 7860, host: str = "0.0.0.0", map_path: str = DEFAULT_MAP):
    app = build_app(map_path=map_path)
    print(f"svitovyd UI — open: http://localhost:{port}")
    app.launch(server_name=host, server_port=port)
