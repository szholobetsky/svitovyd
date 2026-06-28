"""Internationalisation strings for svitovyd Gradio UI.

Usage:
    from . import i18n
    t = i18n.get("uk")
    label = t["find_btn"]
"""
from __future__ import annotations

LANGS: list[str] = ["en", "uk"]

STRINGS: dict[str, dict[str, str]] = {

    # ── English ───────────────────────────────────────────────────────────────
    "en": {
        # app
        "app_title":     "SVITOVYD | {project_name}",
        "app_header":    "## SVITOVYD | project map :: {project_name}",
        "map_file_label": "Map file",

        # tabs
        "tab_find":      "Find",
        "tab_trace":     "Trace",
        "tab_deps":      "Deps",
        "tab_sym":       "Sym",
        "tab_keywords":  "Keywords",
        "tab_idiff":     "Idiff",
        "tab_settings":  "Settings",
        "tab_download":  "Download",

        # find
        "find_desc":        "Filter map blocks. Syntax: `term` `!term` `\\term` `\\!term` `-term` `-!term`",
        "find_query_label": "Query",
        "find_query_ph":    "auth !test",
        "find_btn":         "Find",
        "find_out_label":   "Result",

        # trace
        "trace_desc":       "BFS backwards — who calls this identifier?",
        "trace_id_label":   "Identifier",
        "trace_id_ph":      "insertEmail",
        "trace_depth_label":"Max depth",
        "trace_btn":        "Trace",
        "trace_out_label":  "Result",

        # deps
        "deps_desc":        "BFS forward — what does this identifier depend on?",
        "deps_id_label":    "Identifier or file substring",
        "deps_id_ph":       "DatabaseManager",
        "deps_depth_label": "Max depth",
        "deps_btn":         "Deps",
        "deps_out_label":   "Result",

        # sym
        "sym_desc":       "Asymmetry and cohesion health report.",
        "sym_k_label":    "Top-K hotspots",
        "sym_btn":        "Run",
        "sym_out_label":  "Result",

        # keywords
        "kw_desc":        (
            "Enter a task description to extract matching identifiers (fuzzy). "
            "Leave empty to see top-K identifiers ranked by reference count."
        ),
        "kw_task_label":  "Task description (optional)",
        "kw_task_ph":     "add author field to Book class",
        "kw_k_label":     "Top K (used when task is empty)",
        "kw_btn":         "Extract",
        "kw_out_label":   "Result",

        # idiff
        "idiff_desc":       "Structural diff between two map snapshots.",
        "idiff_prev_label": "Previous map file",
        "idiff_prev_ph":    ".svitovyd/map.prev.txt",
        "idiff_btn":        "Diff",
        "idiff_out_label":  "Result",

        # settings
        "settings_theme_header":   "### Theme",
        "settings_theme_label":    "Theme",
        "settings_theme_save_btn": "Save",
        "settings_lang_header":    "### Language",
        "settings_lang_label":     "Language",
        "settings_lang_save_btn":  "Save",
        "settings_restart_hint":   "Saved — restart to apply.",
        "settings_reload_delay_label": "Reload delay (s)",
        "settings_restart_btn":    "Restart application",
        "settings_restarting":     "Restarting...",

        # download
        "dl_desc": (
            "Download files from the remote server to your local machine.\n\n"
            "**map.txt** — copy to `.1bcoder/map.txt` to use with 1bcoder `/map` commands.\n\n"
            "**keyword.txt** — full vocabulary (all tokens + counts) built by "
            "`svitovyd keywords index`. Required for `keyword extract`. "
            "Check *Filter to top K* to download a smaller plain list instead."
        ),
        "dl_map_btn":      "Prepare map.txt",
        "dl_map_label":    "map.txt",
        "dl_kw_filter":    "Filter to top K only",
        "dl_kw_k_label":   "Top K (used when filter is on)",
        "dl_kw_btn":       "Prepare keyword.txt",
        "dl_kw_label":     "keyword.txt",

        # output strings
        "out_enter_query":    "Enter a query.",
        "out_enter_id":       "Enter an identifier.",
        "out_enter_id_or_file": "Enter an identifier or file substring.",
    },

    # ── Ukrainian ─────────────────────────────────────────────────────────────
    "uk": {
        # app
        "app_title":     "SVITOVYD | {project_name}",
        "app_header":    "## SVITOVYD | project map :: {project_name}",
        "map_file_label": "Файл карти",

        # tabs
        "tab_find":      "Пошук",
        "tab_trace":     "Трасування",
        "tab_deps":      "Залежності",
        "tab_sym":       "Симетрія",
        "tab_keywords":  "Ключові слова",
        "tab_idiff":     "Idiff",
        "tab_settings":  "Налаштування",
        "tab_download":  "Завантаження",

        # find
        "find_desc":        "Фільтрація блоків карти. Синтаксис: `term` `!term` `\\term` `\\!term` `-term` `-!term`",
        "find_query_label": "Запит",
        "find_query_ph":    "auth !test",
        "find_btn":         "Знайти",
        "find_out_label":   "Результат",

        # trace
        "trace_desc":        "BFS назад — хто викликає цей ідентифікатор?",
        "trace_id_label":    "Ідентифікатор",
        "trace_id_ph":       "insertEmail",
        "trace_depth_label": "Максимальна глибина",
        "trace_btn":         "Трасувати",
        "trace_out_label":   "Результат",

        # deps
        "deps_desc":        "BFS вперед — від чого залежить цей ідентифікатор?",
        "deps_id_label":    "Ідентифікатор або частина імені файлу",
        "deps_id_ph":       "DatabaseManager",
        "deps_depth_label": "Максимальна глибина",
        "deps_btn":         "Залежності",
        "deps_out_label":   "Результат",

        # sym
        "sym_desc":      "Звіт про асиметрію та зв'язність.",
        "sym_k_label":   "Top-K точок нагрівання",
        "sym_btn":       "Запустити",
        "sym_out_label": "Результат",

        # keywords
        "kw_desc": (
            "Введи опис задачі для вилучення відповідних ідентифікаторів (нечіткий пошук). "
            "Залиш порожнім, щоб побачити top-K ідентифікаторів за кількістю посилань."
        ),
        "kw_task_label": "Опис задачі (необов'язково)",
        "kw_task_ph":    "додати поле author до класу Book",
        "kw_k_label":    "Top K (коли опис порожній)",
        "kw_btn":        "Вилучити",
        "kw_out_label":  "Результат",

        # idiff
        "idiff_desc":       "Структурний діф між двома знімками карти.",
        "idiff_prev_label": "Попередній файл карти",
        "idiff_prev_ph":    ".svitovyd/map.prev.txt",
        "idiff_btn":        "Діф",
        "idiff_out_label":  "Результат",

        # settings
        "settings_theme_header":   "### Тема",
        "settings_theme_label":    "Тема",
        "settings_theme_save_btn": "Зберегти",
        "settings_lang_header":    "### Мова",
        "settings_lang_label":     "Мова",
        "settings_lang_save_btn":  "Зберегти",
        "settings_restart_hint":   "Збережено — перезапусти для застосування.",
        "settings_reload_delay_label": "Затримка перезапуску (с)",
        "settings_restart_btn":    "Перезапустити застосунок",
        "settings_restarting":     "Перезапуск...",

        # download
        "dl_desc": (
            "Завантажити файли з сервера на локальну машину.\n\n"
            "**map.txt** — скопіюй до `.1bcoder/map.txt` для використання з командою 1bcoder `/map`.\n\n"
            "**keyword.txt** — повний словник (всі токени + лічильники), побудований командою "
            "`svitovyd keywords index`. Потрібен для `keyword extract`. "
            "Встанови *Фільтр до top K*, щоб завантажити скорочений список."
        ),
        "dl_map_btn":    "Підготувати map.txt",
        "dl_map_label":  "map.txt",
        "dl_kw_filter":  "Фільтр до top K",
        "dl_kw_k_label": "Top K (коли фільтр увімкнено)",
        "dl_kw_btn":     "Підготувати keyword.txt",
        "dl_kw_label":   "keyword.txt",

        # output strings
        "out_enter_query":      "Введіть запит.",
        "out_enter_id":         "Введіть ідентифікатор.",
        "out_enter_id_or_file": "Введіть ідентифікатор або частину імені файлу.",
    },
}


def get(lang: str) -> dict[str, str]:
    base = STRINGS["en"]
    if lang == "en" or lang not in STRINGS:
        return base
    return {**base, **STRINGS[lang]}
