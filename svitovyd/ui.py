"""Gradio web UI for svitovyd.

Start:
  svitovyd ui                  # default port 7860
  svitovyd ui --port 7861
  svitovyd ui --map .svitovyd/map.txt
  svitovyd ui --lang uk --theme Soft

Tabs:
  Find     — filter map blocks by filename / content
  Trace    — BFS backwards: who calls this identifier?
  Deps     — BFS forward: what does this depend on?
  Sym      — asymmetry and cohesion health report
  Keywords — top-K identifiers ranked by reference count
  Idiff    — structural diff between two map snapshots
  Settings — theme and language (saved to ~/.svitovyd/config.json, restart to apply)
  Download — download map.txt and keywords.txt to local machine
"""
from __future__ import annotations

import json as _json
import os
import tempfile
from pathlib import Path

from . import i18n

DEFAULT_MAP = os.path.join('.svitovyd', 'map.txt')

_T: dict = {}

_CONFIG_DIR  = Path.home() / ".svitovyd"
_CONFIG_FILE = _CONFIG_DIR / "config.json"

_THEMES = ["Monochrome", "Soft", "Glass", "Ocean", "Default",
           "GithubDark", "Dracula", "Solarized"]


def _dark_theme(primary_hue: str, bg: str, bg2: str, border: str,
                text: str, text_sub: str, input_bg: str, btn2_bg: str):
    """Build a dark Gradio theme by forcing both light and dark CSS vars to the same dark values."""
    import gradio as _gr
    from gradio.themes.utils import colors as _gc
    _base = getattr(_gc, primary_hue.lower(), _gc.blue)
    _primary = _gc.Color(
        c50=btn2_bg, c100=_base.c100, c200=_base.c200,
        c300=_base.c300, c400=_base.c400, c500=_base.c500,
        c600=_base.c600, c700=_base.c700, c800=_base.c800,
        c900=_base.c900, c950=_base.c950,
        name=f"dark-{primary_hue}",
    )
    return _gr.themes.Base(primary_hue=_primary, neutral_hue="slate").set(
        body_background_fill=bg,               body_background_fill_dark=bg,
        background_fill_primary=bg,            background_fill_primary_dark=bg,
        background_fill_secondary=bg2,         background_fill_secondary_dark=bg2,
        block_background_fill=bg2,             block_background_fill_dark=bg2,
        block_label_background_fill=bg2,       block_label_background_fill_dark=bg2,
        block_title_background_fill=bg2,
        panel_background_fill=bg2,             panel_background_fill_dark=bg2,
        block_border_color=border,             block_border_color_dark=border,
        block_label_border_color=border,       block_label_border_color_dark=border,
        border_color_primary=border,           border_color_primary_dark=border,
        body_text_color=text,                  body_text_color_dark=text,
        body_text_color_subdued=text_sub,      body_text_color_subdued_dark=text_sub,
        block_label_text_color=text_sub,       block_label_text_color_dark=text_sub,
        block_title_text_color=text,           block_title_text_color_dark=text,
        block_info_text_color=text_sub,        block_info_text_color_dark=text_sub,
        input_background_fill=bg,             input_background_fill_dark=bg,
        input_background_fill_hover=bg2,      input_background_fill_hover_dark=bg2,
        input_border_color=border,             input_border_color_dark=border,
        input_border_color_hover=text_sub,     input_border_color_hover_dark=text_sub,
        input_placeholder_color=text_sub,      input_placeholder_color_dark=text_sub,
        code_background_fill=bg,               code_background_fill_dark=bg,
        button_secondary_background_fill=btn2_bg,     button_secondary_background_fill_dark=btn2_bg,
        button_secondary_background_fill_hover=border, button_secondary_background_fill_hover_dark=border,
        button_secondary_text_color=text,      button_secondary_text_color_dark=text,
        button_secondary_border_color=border,  button_secondary_border_color_dark=border,
        button_cancel_background_fill=bg2,     button_cancel_background_fill_dark=bg2,
        table_even_background_fill=bg,         table_even_background_fill_dark=bg,
        table_odd_background_fill=bg2,         table_odd_background_fill_dark=bg2,
        table_border_color=border,             table_border_color_dark=border,
        table_text_color=text,                 table_text_color_dark=text,
        checkbox_background_color=bg2,         checkbox_background_color_dark=bg2,
        checkbox_border_color=border,          checkbox_border_color_dark=border,
        checkbox_label_background_fill=bg2,    checkbox_label_background_fill_dark=bg2,
        checkbox_label_text_color=text,        checkbox_label_text_color_dark=text,
        accordion_text_color=text,             accordion_text_color_dark=text,
        error_background_fill=bg2,             error_background_fill_dark=bg2,
        stat_background_fill=bg2,              stat_background_fill_dark=bg2,
    )


# ── config helpers ─────────────────────────────────────────────────────────────

def _load_config() -> dict:
    try:
        return _json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_config(patch: dict) -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = _load_config()
    cfg.update(patch)
    _CONFIG_FILE.write_text(_json.dumps(cfg, indent=2), encoding="utf-8")


# ── backend functions (no UI strings) ─────────────────────────────────────────

def _require_map(map_path: str) -> str | None:
    if not os.path.exists(map_path):
        return f"Map file not found: {map_path}\nRun: svitovyd index ."
    return None


def _run_find(map_path, query):
    err = _require_map(map_path)
    if err:
        return err
    if not query.strip():
        return _T.get("out_enter_query", "Enter a query.")
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
        return _T.get("out_enter_id", "Enter an identifier.")
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
        return _T.get("out_enter_id_or_file", "Enter an identifier or file substring.")
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
    if not os.path.exists(map_path):
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='_error.txt',
                                          delete=False, encoding='utf-8')
        tmp.write(f"Map file not found: {map_path}\nRun: svitovyd index .")
        tmp.close()
        return tmp.name
    return map_path


def _download_keywords(map_path, filter_top_k, k):
    err = _require_map(map_path)
    if err:
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='_error.txt',
                                          delete=False, encoding='utf-8')
        tmp.write(err)
        tmp.close()
        return tmp.name

    kw_path = os.path.join(os.path.dirname(os.path.abspath(map_path)), 'keyword.txt')

    if not filter_top_k:
        if not os.path.exists(kw_path):
            tmp = tempfile.NamedTemporaryFile(mode='w', suffix='_error.txt',
                                              delete=False, encoding='utf-8')
            tmp.write(f"keyword.txt not found: {kw_path}\n"
                      f"Run: svitovyd keywords index")
            tmp.close()
            return tmp.name
        return kw_path

    from .query import keywords_map
    content = keywords_map(map_path, k=int(k), plain=True)
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='_keywords.txt',
                                      delete=False, encoding='utf-8')
    tmp.write(content)
    tmp.close()
    return tmp.name


# ── UI ─────────────────────────────────────────────────────────────────────────

def build_app(map_path: str = DEFAULT_MAP, lang: str = "en", theme: str = "Monochrome"):
    global _T
    t = i18n.get(lang)
    _T.update(t)

    try:
        import gradio as gr
    except ImportError:
        raise ImportError("Gradio not installed. Run: pip install \"svitovyd[ui]\"")

    _theme_map = {
        "Monochrome": gr.themes.Monochrome(),
        "Soft":       gr.themes.Soft(),
        "Glass":      gr.themes.Glass(),
        "Ocean":      gr.themes.Ocean(),
        "Default":    gr.themes.Default(),
        "GithubDark": _dark_theme(
            primary_hue="blue",
            bg="#0d1117", bg2="#161b22", border="#30363d",
            text="#c9d1d9", text_sub="#8b949e",
            input_bg="#0d1117", btn2_bg="#21262d",
        ),
        "Dracula": _dark_theme(
            primary_hue="purple",
            bg="#282a36", bg2="#1e1f29", border="#44475a",
            text="#f8f8f2", text_sub="#6272a4",
            input_bg="#282a36", btn2_bg="#44475a",
        ),
        "Solarized": _dark_theme(
            primary_hue="cyan",
            bg="#002b36", bg2="#073642", border="#586e75",
            text="#839496", text_sub="#657b83",
            input_bg="#002b36", btn2_bg="#073642",
        ),
    }
    active_theme = _theme_map.get(theme, gr.themes.Monochrome())

    project_root = os.path.abspath(os.path.join(map_path, '..', '..'))
    project_name = os.path.basename(project_root)

    with gr.Blocks(
        title=t["app_title"].format(project_name=project_name),
        theme=active_theme,
    ) as app:
        gr.Markdown(t["app_header"].format(project_name=project_name))

        map_box = gr.Textbox(value=map_path, label=t["map_file_label"], scale=4)

        with gr.Tabs():

            # ── Find ──────────────────────────────────────────────────────────
            with gr.Tab(t["tab_find"]):
                gr.Markdown(t["find_desc"])
                find_query = gr.Textbox(label=t["find_query_label"],
                                        placeholder=t["find_query_ph"])
                find_btn   = gr.Button(t["find_btn"], variant="primary")
                find_out   = gr.Code(language=None, label=t["find_out_label"])
                find_btn.click(_run_find, inputs=[map_box, find_query], outputs=find_out)
                find_query.submit(_run_find, inputs=[map_box, find_query], outputs=find_out)

            # ── Trace ─────────────────────────────────────────────────────────
            with gr.Tab(t["tab_trace"]):
                gr.Markdown(t["trace_desc"])
                trace_id    = gr.Textbox(label=t["trace_id_label"],
                                         placeholder=t["trace_id_ph"])
                trace_depth = gr.Slider(1, 16, value=8, step=1, label=t["trace_depth_label"])
                trace_btn   = gr.Button(t["trace_btn"], variant="primary")
                trace_out   = gr.Code(language=None, label=t["trace_out_label"])
                trace_btn.click(_run_trace,
                                inputs=[map_box, trace_id, trace_depth], outputs=trace_out)

            # ── Deps ──────────────────────────────────────────────────────────
            with gr.Tab(t["tab_deps"]):
                gr.Markdown(t["deps_desc"])
                deps_id    = gr.Textbox(label=t["deps_id_label"],
                                        placeholder=t["deps_id_ph"])
                deps_depth = gr.Slider(1, 16, value=8, step=1, label=t["deps_depth_label"])
                deps_btn   = gr.Button(t["deps_btn"], variant="primary")
                deps_out   = gr.Code(language=None, label=t["deps_out_label"])
                deps_btn.click(_run_deps,
                               inputs=[map_box, deps_id, deps_depth], outputs=deps_out)

            # ── Sym ───────────────────────────────────────────────────────────
            with gr.Tab(t["tab_sym"]):
                gr.Markdown(t["sym_desc"])
                sym_k   = gr.Slider(1, 20, value=5, step=1, label=t["sym_k_label"])
                sym_btn = gr.Button(t["sym_btn"], variant="primary")
                sym_out = gr.Code(language=None, label=t["sym_out_label"])
                sym_btn.click(_run_sym, inputs=[map_box, sym_k], outputs=sym_out)

            # ── Keywords ──────────────────────────────────────────────────────
            with gr.Tab(t["tab_keywords"]):
                gr.Markdown(t["kw_desc"])
                kw_task = gr.Textbox(label=t["kw_task_label"],
                                     placeholder=t["kw_task_ph"])
                kw_k    = gr.Slider(10, 200, value=50, step=10, label=t["kw_k_label"])
                kw_btn  = gr.Button(t["kw_btn"], variant="primary")
                kw_out  = gr.Code(language=None, label=t["kw_out_label"])
                kw_btn.click(_run_keywords, inputs=[map_box, kw_k, kw_task], outputs=kw_out)
                kw_task.submit(_run_keywords, inputs=[map_box, kw_k, kw_task], outputs=kw_out)

            # ── Idiff ─────────────────────────────────────────────────────────
            with gr.Tab(t["tab_idiff"]):
                gr.Markdown(t["idiff_desc"])
                idiff_prev = gr.Textbox(label=t["idiff_prev_label"],
                                        placeholder=t["idiff_prev_ph"])
                idiff_btn  = gr.Button(t["idiff_btn"], variant="primary")
                idiff_out  = gr.Code(language=None, label=t["idiff_out_label"])
                idiff_btn.click(_run_idiff, inputs=[map_box, idiff_prev], outputs=idiff_out)

            # ── Settings ──────────────────────────────────────────────────────
            with gr.Tab(t["tab_settings"]):
                gr.Markdown(t["settings_theme_header"])
                with gr.Row():
                    s_theme     = gr.Dropdown(choices=_THEMES, value=theme,
                                              label=t["settings_theme_label"], scale=2)
                    s_theme_btn = gr.Button(t["settings_theme_save_btn"], scale=1)
                s_theme_hint = gr.Markdown("")

                gr.Markdown(t["settings_lang_header"])
                with gr.Row():
                    s_lang     = gr.Dropdown(choices=i18n.LANGS, value=lang,
                                             label=t["settings_lang_label"], scale=2)
                    s_lang_btn = gr.Button(t["settings_lang_save_btn"], scale=1)
                s_lang_hint = gr.Markdown("")

                def _do_save_theme(name):
                    _save_config({"theme": name})
                    return t["settings_restart_hint"]

                def _do_save_lang(name):
                    _save_config({"lang": name})
                    return t["settings_restart_hint"]

                s_theme_btn.click(_do_save_theme, inputs=[s_theme], outputs=[s_theme_hint])
                s_lang_btn.click(_do_save_lang, inputs=[s_lang], outputs=[s_lang_hint])

                gr.Markdown("---")
                _restart_delay = int(_load_config().get("restart_delay", 5))
                with gr.Row():
                    s_restart_delay = gr.Number(
                        value=_restart_delay, minimum=2, maximum=60, step=1,
                        label=t["settings_reload_delay_label"], precision=0, scale=3,
                    )
                    s_delay_save = gr.Button(t["settings_theme_save_btn"], scale=1)
                s_delay_hint = gr.Markdown("")

                def _do_save_restart_delay(d):
                    _save_config({"restart_delay": int(d)})
                    return t["settings_restart_hint"]

                s_delay_save.click(_do_save_restart_delay,
                                   inputs=[s_restart_delay], outputs=[s_delay_hint])

                s_restart_btn = gr.Button(t["settings_restart_btn"], variant="stop")
                s_restart_out = gr.Markdown("")

                def _do_restart_app(delay):
                    import sys, threading
                    import subprocess as _sp
                    def _relaunch():
                        _sp.Popen(sys.argv, cwd=os.getcwd())
                        os._exit(0)
                    threading.Timer(1.5, _relaunch).start()
                    return t["settings_restarting"]

                s_restart_btn.click(
                    _do_restart_app,
                    inputs=[s_restart_delay],
                    outputs=[s_restart_out],
                    js="""(delay) => {
  const ms = Math.max(2, parseInt(delay) || 5) * 1000;
  const overlay = document.createElement('div');
  overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;z-index:99999;background:#1e293b;padding:10px 16px;box-shadow:0 2px 8px rgba(0,0,0,.5)';
  const lbl = document.createElement('div');
  lbl.style.cssText = 'color:#e2e8f0;font-size:13px;margin-bottom:6px;font-family:monospace';
  const track = document.createElement('div');
  track.style.cssText = 'width:100%;height:8px;background:#334155;border-radius:4px;overflow:hidden';
  const fill = document.createElement('div');
  fill.style.cssText = 'height:100%;width:0%;background:#3b82f6;border-radius:4px';
  track.appendChild(fill);
  overlay.appendChild(lbl);
  overlay.appendChild(track);
  document.body.appendChild(overlay);
  const start = Date.now();
  const tick = setInterval(() => {
    const elapsed = Date.now() - start;
    const pct = Math.min(100, (elapsed / ms) * 100);
    const secs = Math.max(0, Math.ceil((ms - elapsed) / 1000));
    fill.style.width = pct + '%';
    lbl.textContent = 'Restarting SVITOVYD… reloading in ' + secs + ' s';
    if (elapsed >= ms) { clearInterval(tick); window.location.reload(); }
  }, 100);
}""",
                )

            # ── Download ──────────────────────────────────────────────────────
            with gr.Tab(t["tab_download"]):
                gr.Markdown(t["dl_desc"])
                with gr.Row():
                    dl_map_btn = gr.Button(t["dl_map_btn"], variant="primary")
                dl_map_file = gr.File(label=t["dl_map_label"], interactive=False)

                gr.Markdown("---")

                with gr.Row():
                    dl_kw_filter = gr.Checkbox(label=t["dl_kw_filter"], value=False)
                    dl_kw_k      = gr.Slider(10, 500, value=100, step=10,
                                             label=t["dl_kw_k_label"])
                    dl_kw_btn    = gr.Button(t["dl_kw_btn"], variant="primary")
                dl_kw_file = gr.File(label=t["dl_kw_label"], interactive=False)

                dl_map_btn.click(_download_map, inputs=[map_box], outputs=dl_map_file)
                dl_kw_btn.click(_download_keywords,
                                inputs=[map_box, dl_kw_filter, dl_kw_k],
                                outputs=dl_kw_file)

    return app


def main(port: int = 7860, host: str = "0.0.0.0",
         map_path: str = DEFAULT_MAP, lang: str = "en", theme: str = "Monochrome"):
    app = build_app(map_path=map_path, lang=lang, theme=theme)
    print(f"svitovyd UI — open: http://localhost:{port}")
    app.launch(server_name=host, server_port=port)
