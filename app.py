"""FilePilot: a local, review-first file workspace."""
from __future__ import annotations
import html
import json
import os
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import pandas as pd
import streamlit as st
from filepilot_core import (CATEGORIES, FilePilotSupervisor, human_size, ollama_models,
                            recent_history, execute_plan, undo_latest, create_demo_folder)
from filepilot_features import revise_plan, insights, plan_csv

BASE = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("FILEPILOT_DATABASE", str(BASE / "data" / "filepilot.db")))
st.set_page_config(page_title="FilePilot · Your files, in order", page_icon="✦", layout="wide")
st.markdown(f"<style>{(BASE / 'assets' / 'style.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
DEFAULTS = {
    "page": "Overview", "analysis": None, "draft": {}, "revision": 0,
    "scan_id": "initial", "notice": None, "folder": str(BASE / "demo_folder"), "use_ai": False,
    "model": "qwen2.5:3b", "base_url": "http://localhost:11434", "max_files": 200,
    "max_file_mb": 100, "recursive": True, "exclusions": "*.tmp, *.part, ~$*",
    "goal": "Organise my files into useful categories with clear, readable names.",
    "layout": "Category", "preserve_names": False, "connection": None,
}
for key, value in DEFAULTS.items():
    # Retain preferences when their widgets are not on the current page.
    st.session_state[key] = st.session_state.get(key, value)

def esc(value):
    return html.escape(str(value))

def markup(value):
    st.markdown(value, unsafe_allow_html=True)

def navigate(page):
    st.session_state.page = page

def invalidate_review():
    st.session_state.revision += 1
    st.session_state.pop("approval", None)

def clear_scan():
    st.session_state.analysis = None
    st.session_state.draft = {}
    st.session_state.scan_id = uuid.uuid4().hex
    invalidate_review()

def flash(kind, message):
    st.session_state.notice = (kind, message)

def current_plan():
    return revise_plan(st.session_state.analysis, st.session_state.draft,
                       st.session_state.layout, st.session_state.preserve_names)

def heading(eyebrow, title, description):
    markup(f'<div class="page-heading"><div class="eyebrow">{esc(eyebrow)}</div>'
           f'<h1>{esc(title)}</h1><p>{esc(description)}</p></div>')

def empty_state(title, message, icon="⌁"):
    markup(f'<div class="empty-state"><div class="empty-icon">{icon}</div>'
           f'<h3>{esc(title)}</h3><p>{esc(message)}</p></div>')

def validate_ollama_address():
    address = urlparse(st.session_state.base_url)
    if address.scheme != "http" or address.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Use a local Ollama address, such as http://localhost:11434.")

def analyze():
    try:
        if st.session_state.use_ai:
            validate_ollama_address()
        with st.spinner("Reading your files and preparing a reviewable plan…"):
            result = FilePilotSupervisor().analyze(
                st.session_state.folder, st.session_state.goal,
                st.session_state.base_url, st.session_state.model,
                max_files=st.session_state.max_files, use_ai=st.session_state.use_ai,
                recursive=st.session_state.recursive, max_file_mb=st.session_state.max_file_mb,
                excluded_patterns=st.session_state.exclusions.split(","))
        clear_scan()
        st.session_state.analysis = result
        flash("success", f"Scan complete. {len(result.files)} files indexed; your files have not moved.")
    except Exception as exc:
        flash("error", f"Could not scan this folder: {exc}")

def fresh_demo(scan=False):
    demo = BASE / "practice" / uuid.uuid4().hex[:8]
    create_demo_folder(demo)
    st.session_state.folder = str(demo)
    clear_scan()
    navigate("Overview")
    if scan:
        analyze()
    else:
        flash("success", "Your fresh demo is ready. Select Scan folder to explore it.")

NAV = [("Overview", ":material/space_dashboard:"), ("Review plan", ":material/checklist:"),
       ("Duplicates", ":material/content_copy:"), ("Activity", ":material/history:"),
       ("Settings", ":material/tune:")]
with st.sidebar:
    markup('<div class="brand"><span class="brand-mark">✦</span><div>FilePilot<small>YOUR PERSONAL FILE WORKSPACE</small></div></div>')
    markup('<div class="nav-label">WORKSPACE</div>')
    for label, icon in NAV:
        st.button(label, icon=icon, key=f"nav_{label}", width="stretch",
                  type="primary" if st.session_state.page == label else "secondary",
                  on_click=navigate, args=(label,))
    markup('<div class="sidebar-separator"></div><div class="nav-label">CURRENT WORKSPACE</div>')
    active = st.session_state.analysis
    active_path = active.target if active else st.session_state.folder
    markup(f'<div class="workspace-card"><span class="workspace-icon">▣</span>'
           f'<strong>{esc(Path(active_path).name or "Select a folder")}</strong>'
           f'<small>{"Plan ready to review" if active else "Ready for a fresh start"}</small></div>')
    markup('<div class="sidebar-note"><span class="status-dot"></span> Local by design<p>Your files stay on this computer.<br>You approve every move.</p></div>')
    markup('<div class="sidebar-footer">FILEPILOT <span>2.0 / PREMIUM</span></div>')
markup(f'<div class="topbar"><span>Workspace <b>/</b> {esc(st.session_state.page)}</span>'
       '<span class="topbar-right"><span class="status-dot"></span> Local workspace <span class="avatar">FP</span></span></div>')
if st.session_state.notice:
    kind, message = st.session_state.notice
    getattr(st, kind)(message)
    st.session_state.notice = None

def overview():
    heading("A LITTLE ORDER. A LOT OF CLARITY.", "Make room for what matters.",
            "A calmer home for your files. Scan, review, and let FilePilot do the sorting.")
    left, right = st.columns([1.85, 1], gap="large")
    with left:
        with st.container(border=True, key="mission"):
            markup('<div class="section-kicker">YOUR NEXT CLEAN SLATE</div><h3>Where should we start?</h3>')
            st.text_input("Folder to organise", key="folder", placeholder=r"C:\Users\You\Downloads")
            row = st.columns([1.4, 1])
            row[0].button("Scan folder", icon=":material/document_search:", type="primary", width="stretch", on_click=analyze)
            row[1].button("Try demo", icon=":material/play_circle:", width="stretch", on_click=fresh_demo, args=(True,))
            st.caption("Preview first. Nothing moves until you approve the plan.")
    with right:
        markup('<div class="hero-art"><span class="art-label">LESS SEARCHING. MORE DOING.</span>'
               '<div class="orbit orbit-one"></div><div class="orbit orbit-two"></div>'
               '<div class="mini-file file-one"><span>≡</span><small>REPORT</small></div>'
               '<div class="mini-file file-two"><span>▧</span><small>RECEIPT</small></div>'
               '<div class="folder-art"><span>✦</span></div><span class="art-check">✓</span>'
               '<div class="art-caption">Everything in its right place.</div></div>')
    result = st.session_state.analysis
    info = insights(result) if result else None
    values = [
        ("Files indexed", str(len(result.files)) if result else "—", "In your latest scan", "▤"),
        ("Total size", human_size(result.total_size_bytes) if result else "—", "Within scan limits", "◫"),
        ("Exact duplicates", str(result.duplicate_count) if result else "—", human_size(info["duplicate_bytes"]) + " in extra copies" if info else "Identical content, spotted", "▱"),
        ("Need a closer look", str(info["needs_review"]) if info else "—", "Confidence below 70%", "◎")]
    for col, (label, value, detail, icon) in zip(st.columns(4), values):
        with col:
            markup(f'<div class="stat-card"><span class="stat-icon">{icon}</span><small>{label}</small>'
                   f'<strong>{esc(value)}</strong><span>{esc(detail)}</span></div>')
    a, b = st.columns([1.65, 1], gap="large")
    with a:
        with st.container(border=True, key="card_landscape"):
            st.subheader("Your file landscape")
            st.caption("A clear picture of what is in your latest scan.")
            if result and result.plan:
                colors = ["#24775f", "#77a68e", "#b0c9bc", "#a5b9d5", "#dab980", "#b5a6cc"]
                for i, (category, count) in enumerate(sorted(info["categories"].items(), key=lambda x: -x[1])):
                    markup(f'<div class="category-row"><span>{esc(category)}</span><div class="bar-track"><div style="width:{count/len(result.plan)*100}%;background:{colors[i % len(colors)]}"></div></div><b>{count}</b></div>')
                st.button("Review your plan", icon=":material/arrow_forward:", on_click=navigate, args=("Review plan",))
            else:
                empty_state("A fresh perspective awaits", "Scan a folder to see your categories, duplicates, and files that need attention.")
    with b:
        with st.container(border=True, key="card_workflow"):
            st.subheader("You're in control")
            for n, title, desc in [("01", "Scan & understand", "Read file details and detect exact copies."),
                                   ("02", "Make it yours", "Review categories, names, and destinations."),
                                   ("03", "Approve & organise", "Verified moves, with a path back through undo.")]:
                markup(f'<div class="workflow-step"><span>{n}</span><div><strong>{title}</strong><p>{desc}</p></div></div>')
    if result:
        if result.used_ai:
            st.success(result.ai_message)
        elif st.session_state.use_ai:
            st.info(result.ai_message)
        else:
            st.caption("This scan used offline rules. Enable local AI in Settings for content-aware name suggestions.")
        with st.expander("Scan activity & notices"):
            for message in result.agent_log:
                st.text(message)

def select_bulk(mode):
    for item in st.session_state.analysis.plan:
        include = mode == "all" or (mode == "confident" and item.confidence >= .7) or (mode == "unique" and not item.duplicate_of)
        st.session_state.draft.setdefault(item.id, {})["include"] = include
    invalidate_review()

def review():
    heading("THE FINAL SAY IS YOURS", "A plan you can make your own.",
            "Choose what moves, refine the details, and preview every destination.")
    result = st.session_state.analysis
    if not result or not result.plan:
        empty_state("No plan waiting for approval", "Start with a folder scan from Overview. Your plan will appear here.")
        st.button("Go to overview", on_click=navigate, args=("Overview",), type="primary")
        return
    st.caption(f"Scanned folder: {result.target}")
    with st.container(border=True, key="card_filters"):
        controls = st.columns([1.2, 1.2, 1])
        query = controls[0].text_input("Search files", placeholder="Search a name or path…")
        category = controls[1].selectbox("Filter category", ["All categories"] + sorted({p.category for p in current_plan()}))
        attention = controls[2].selectbox("Show", ["All files", "Needs review", "Duplicates", "Selected only"])
        for col, label, mode in zip(st.columns(4), ["Select all", "Select none", "Confident only", "Unique only"], ["all", "none", "confident", "unique"]):
            col.button(label, on_click=select_bulk, args=(mode,), width="stretch")
        st.caption("Selection shortcuts apply to the whole plan. Search and filters only change what you see.")
        plan = current_plan()
        visible = [p for p in plan if (not query or query.casefold() in f"{p.relative_source} {p.proposed_name}".casefold())
                   and (category == "All categories" or category == p.category)
                   and (attention == "All files" or (attention == "Needs review" and p.confidence < .7 and not p.duplicate_of)
                        or (attention == "Duplicates" and p.duplicate_of) or (attention == "Selected only" and p.include))]
        if visible:
            rows = [{"Move": p.include, "ID": p.id, "Current file": p.relative_source,
                     "Category": p.category, "New name": p.proposed_name,
                     "Confidence": round(p.confidence * 100)} for p in visible]
            editor_key = f"editor_{st.session_state.scan_id}_{st.session_state.revision}_{query}_{category}_{attention}"
            edited = st.data_editor(pd.DataFrame(rows), hide_index=True, width="stretch", key=editor_key,
                disabled=["ID", "Current file", "Confidence"] + (["New name"] if st.session_state.preserve_names else []),
                column_config={"ID": None, "Move": st.column_config.CheckboxColumn("Move", width="small"),
                    "Category": st.column_config.SelectboxColumn("Category", options=CATEGORIES, required=True),
                    "New name": st.column_config.TextColumn("New name", required=True),
                    "Confidence": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=100, format="%d%%")})
            changed = False
            for before, after in zip(rows, edited.to_dict("records")):
                if before != after:
                    change = {"include": bool(after["Move"]), "category": after["Category"]}
                    if before["New name"] != after["New name"]:
                        change["name"] = after["New name"]
                    st.session_state.draft.setdefault(after["ID"], {}).update(change)
                    changed = True
            if changed:
                invalidate_review()
                st.rerun()
            st.caption(f"Showing {len(visible)} of {len(plan)} files. Edit a category or filename directly in the table.")
        else:
            st.info("No files match these filters. Your other selections are preserved.")
    plan = current_plan()
    preview, approval = st.columns([1.5, 1], gap="large")
    with preview:
        with st.container(border=True, key="card_preview"):
            st.subheader("Look a little closer")
            by_id = {p.id: p for p in plan}
            pick = st.selectbox("File preview", list(by_id), format_func=lambda x: by_id[x].relative_source)
            item = by_id[pick]
            record = next(f for f in result.files if f.id == pick)
            st.caption(f"{human_size(record.size_bytes)} · Modified {record.modified_iso[:10]} · {item.confidence:.0%} confidence")
            st.write(item.reason)
            if item.duplicate_of:
                st.info(f"Identical content to: {item.duplicate_of}")
            st.caption("DESTINATION PREVIEW")
            st.code(str(Path(item.destination).relative_to(Path(result.target))), language=None, wrap_lines=True)
            with st.expander("Content preview · captured at scan time"):
                if record.snippet:
                    st.code(record.snippet, language=None, wrap_lines=True)
                else:
                    st.caption("No text preview is available for this file type. The file itself is unchanged.")
    with approval:
        with st.container(border=True, key="card_approval"):
            selected = [p for p in plan if p.include]
            ids = {p.id for p in selected}
            total = sum(f.size_bytes for f in result.files if f.id in ids)
            st.subheader("Ready when you are")
            markup(f'<div class="approval-total">{len(selected)}<span> files selected · {human_size(total)}</span></div>')
            st.caption(f"{len(plan) - len(selected)} files will stay where they are.")
            signature = json.dumps([p.to_dict() for p in plan], sort_keys=True)
            if st.session_state.get("approval_signature") != signature:
                st.session_state.pop("approval", None)
                st.session_state.approval_signature = signature
            approved = st.checkbox("I reviewed and approve these file moves.", key="approval")
            if st.button("Organise selected files", icon=":material/drive_file_move:", type="primary", width="stretch", disabled=not approved or not selected):
                try:
                    with st.spinner("Moving and verifying your selected files…"):
                        execution = execute_plan(result.target, plan, DATABASE)
                    flash("success" if execution["ok"] else "error", execution["message"])
                    clear_scan()
                    navigate("Activity")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Organisation stopped: {exc}")
            st.caption("Files are moved into FilePilot_Organized. Exact copies are kept, never deleted.")
            st.divider()
            st.caption("TAKE YOUR PLAN WITH YOU")
            downloads = st.columns(2)
            downloads[0].download_button("Export CSV", plan_csv(plan), "filepilot_plan.csv", "text/csv", width="stretch")
            downloads[1].download_button("Export JSON", json.dumps([p.to_dict() for p in plan], indent=2), "filepilot_plan.json", "application/json", width="stretch")
    with st.expander("All destinations · your complete reviewed plan"):
        st.dataframe(pd.DataFrame([{"Move": p.include, "Current file": p.relative_source, "Destination": p.destination} for p in plan]), hide_index=True, width="stretch")

def duplicates():
    heading("SAME CONTENT. CLEARER CHOICES.", "Meet your extra copies.",
            "Exact matches are detected from file content, even when their names differ.")
    result = st.session_state.analysis
    if not result:
        empty_state("Find the files you already have", "Scan a folder to reveal groups of identical files.", "▱")
        return
    data = insights(result)
    cols = st.columns(3)
    cols[0].metric("Extra copies", result.duplicate_count)
    cols[1].metric("Space in extra copies", human_size(data["duplicate_bytes"]))
    groups = defaultdict(list)
    for record in result.files:
        groups[record.sha256].append(record)
    matches = [files for files in groups.values() if len(files) > 1]
    cols[2].metric("Duplicate groups", len(matches))
    st.caption("These bytes are an insight, not space saved. FilePilot keeps all copies and moves approved duplicates into their own folder.")
    if not matches:
        empty_state("No exact duplicates found", "Every file in this scan has unique content.", "✓")
    for number, files in enumerate(matches, 1):
        with st.container(border=True, key=f"card_duplicate_{number}"):
            st.subheader(f"Group {number} · {len(files)} identical files")
            for i, record in enumerate(files):
                markup(f'<div class="duplicate-row"><span class="file-symbol">▤</span><div><strong>{esc(record.relative_path)}</strong>'
                       f'<small>{human_size(record.size_bytes)} · {"Reference copy" if i == 0 else "Extra copy"}</small></div><span class="match-tag">100% match</span></div>')
    if matches:
        st.button("Review duplicate selections", type="primary", on_click=navigate, args=("Review plan",))

def activity():
    heading("A RECORD OF EVERY MOVE", "Your workspace, with a rewind.",
            "See what changed and restore the latest completed organisation run.")
    history = recent_history(DATABASE, limit=50)
    if not history:
        empty_state("Your story starts with the first move", "Approved organisation runs will appear here, together with their undo status.", "↶")
        return
    pending = next((h for h in history if h["Status"] in ("completed", "partial_undo")), None)
    if pending:
        with st.container(border=True, key="card_restore"):
            st.subheader("Need to go back?")
            st.write(f"Restore run {pending['Run']} · {pending['Files']} files")
            st.caption(pending["Target"])
            st.caption("Changed files and occupied original locations are skipped so you can resolve conflicts and retry.")
            confirm = st.checkbox("Restore the latest completed run to its original locations.")
            if st.button("Undo latest run", icon=":material/undo:", disabled=not confirm):
                try:
                    with st.spinner("Checking and restoring files…"):
                        outcome = undo_latest(DATABASE)
                    clear_scan()
                    flash("success" if outcome["ok"] else "warning", outcome["message"])
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not finish restoring: {exc}")
    for run in history:
        with st.container(border=True, key=f"card_history_{run['Run']}"):
            status = run["Status"].replace("_", " ").title()
            stamp = datetime.fromisoformat(run["Time"]).astimezone().strftime("%d %b %Y · %I:%M %p")
            markup(f'<div class="history-title"><strong>{esc(status)}</strong><span>{esc(stamp)}</span></div>')
            st.write(f"{run['Files']} files · {run['Target']}")
            with st.expander(f"Details · {run['Run']}"):
                st.write(run["Message"])
    st.download_button("Export history CSV", pd.DataFrame(history).to_csv(index=False), "filepilot_history.csv", "text/csv")

def settings():
    heading("BUILT AROUND THE WAY YOU WORK", "Your organising preferences.",
            "Set the boundaries once. Keep every scan focused and every plan familiar.")
    left, right = st.columns(2, gap="large")
    with left:
        with st.container(border=True, key="card_scan"):
            st.subheader("Scan preferences")
            st.toggle("Include subfolders", key="recursive")
            st.slider("Maximum files per scan", 20, 1000, step=20, key="max_files")
            st.number_input("Maximum file size (MB)", min_value=1, max_value=2048, key="max_file_mb")
            st.text_input("Ignore patterns", key="exclusions", help="Comma-separated patterns. Examples: *.tmp, private*, cache")
            st.caption("Hidden files, development folders, links, and FilePilot_Organized are excluded automatically. Scan settings apply to your next scan.")
        with st.container(border=True, key="card_layout"):
            st.subheader("Folder & naming style")
            st.selectbox("Folder layout", ["Category", "Category / Year / Month"], key="layout", on_change=invalidate_review)
            st.toggle("Keep original filenames", key="preserve_names", on_change=invalidate_review)
            st.caption("Date folders use the file's last-modified date in UTC. Changes update the current review plan and require fresh approval.")
    with right:
        with st.container(border=True, key="card_ai"):
            st.subheader("Local intelligence")
            st.toggle("Use Ollama AI", key="use_ai")
            st.caption("Offline rules work immediately. Enable Ollama for semantic classification and suggested names. Only your local Ollama service receives short file previews.")
            st.text_input("Ollama model", key="model")
            st.text_input("Local Ollama address", key="base_url")
            if st.button("Test connection", icon=":material/cable:"):
                try:
                    validate_ollama_address()
                    models = ollama_models(st.session_state.base_url)
                    st.session_state.connection = (True, ", ".join(models) if models else "Connected, but no models are installed.")
                except Exception as exc:
                    st.session_state.connection = (False, f"Ollama is unavailable. Offline rules still work. {exc}")
            if st.session_state.connection:
                ok, msg = st.session_state.connection
                (st.success if ok else st.info)(msg)
            st.text_area("Organisation goal", key="goal", height=100)
            st.caption("The goal guides local AI when enabled. Offline mode uses file types and content keywords.")
        with st.container(border=True, key="card_demo"):
            st.subheader("A safe space to try things")
            st.write("Create a fresh practice folder with sample files. Each demo is separate from your own folders.")
            st.button("Create a fresh demo", icon=":material/create_new_folder:", on_click=fresh_demo)
    st.caption("Preferences stay with this browser session. Run history is saved locally in data/filepilot.db.")

{"Overview": overview, "Review plan": review, "Duplicates": duplicates,
 "Activity": activity, "Settings": settings}[st.session_state.page]()
markup('<div class="app-footer"><span>Thoughtful organisation. Local intelligence.</span><span>FILEPILOT / 2.0</span></div>')
