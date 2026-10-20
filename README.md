# FilePilot 2.0 — Your files, in order

A local file organiser with a premium forest-green dashboard, editable plans,
exact duplicate insights, verified moves, and undo. Built with Python and Streamlit.

## Start on Windows

1. Extract the ZIP into a normal folder.
2. Install Python 3.11 or newer if needed. Enable **Add Python to PATH** during installation.
3. Double-click **setup.bat** once. An internet connection is needed to install packages.
4. Double-click **start_filepilot.bat**. Open http://localhost:8501 if the browser does not open automatically.
5. Click **Try demo** for a fresh practice folder, or enter a local folder and click **Scan folder**.

Offline rules are enabled by default. Ollama and an API key are not required to use the app.

## What's new

- Premium responsive interface: dark forest sidebar, light cards, editorial headings,
  local CSS illustration, category charts, and clear empty states.
- Separate Overview, Review plan, Duplicates, Activity, and Settings pages.
- Search by original or proposed filename; filter by category, duplicates, confidence, or selection.
- Edit categories and filenames directly in the review table.
- Bulk selection: all, none, confident files, or unique files. Shortcuts apply to the whole plan.
- A preview of the exact destination and a short text preview captured during the scan.
- Category folders or Category / Year / Month folders, using last-modified time in UTC.
- Optional preservation of original filenames. Extensions and name collisions are handled automatically.
- Duplicate groups and the size of extra copies. This does not claim space has been freed.
- CSV and JSON exports of the current edited plan, including inclusion choices and final destinations.
- Scan limits, maximum file size, subfolder switch, and comma-separated ignore patterns.
- Explicit offline / local Ollama controls and connection check.
- Readable run history, export, and confirmed undo with conflict reporting.
- A fresh demo folder for each practice session; existing folders are never reset or deleted.
- Approval is cleared when the scan, selected files, names, categories, or destinations change.
- Fixed Windows SQLite connection locking and deterministic ordering of runs created in the same second.

## A two-minute demonstration

1. Choose **Try demo** on Overview. It scans eight sample files without moving anything.
2. Show the category breakdown and duplicate count.
3. Open **Duplicates** to see two files with identical content.
4. Open **Review plan**. Rename the invoice and change a category.
5. Try **Unique only** to leave the extra copy where it is.
6. Review the destination preview and export the plan if desired.
7. Tick the approval checkbox and select **Organise selected files**.
8. Open **Activity**, confirm restore, and select **Undo latest run**.

## Optional local AI

Install Ollama from its official website, then run:

```powershell
ollama pull qwen2.5:3b
```

In Settings, enable **Use Ollama AI**, keep `http://localhost:11434`, and select
**Test connection**. Your next scan uses the selected model. If it is unavailable,
FilePilot uses offline rules and explains that in the scan result.

The organisation goal guides AI classification. Offline rules use file types and
content keywords; they do not interpret arbitrary goals or generate semantic names.
The UI accepts only loopback HTTP addresses for Ollama. Short local file previews
are sent to that service. No cloud connection is required for organisation.

## Important behaviour

- A scan only inspects files and proposes changes. Moving requires explicit approval.
- Output is always inside the scanned folder's `FilePilot_Organized` directory.
- Hashes are checked before and after moves. Exceptions trigger rollback attempts.
- FilePilot does not delete duplicates. Moving duplicates does not free disk space.
- Undo restores the latest eligible run across all folders recorded in this app's database.
  It skips files that changed or whose original location is occupied. Resolve the
  conflict, then retry undo. Keep `data/filepilot.db` if you need your history.
- Hidden files, links, development folders, and organised output are skipped.
  Files over the size limit are skipped; limits and unreadable-file notices appear
  in **Scan activity & notices**. Statistics describe indexed files, not the whole disk.
- Text previews support text/code/CSV, the first two PDF pages, and DOCX paragraphs.
  Unsupported formats still receive metadata-based classification.
- Confidence is a classifier estimate, not a calibrated probability.
- Preferences and unexecuted plans live in the current browser session; refreshing or
  closing it can discard the plan. Completed run history persists in SQLite.
- Transaction rollback handles caught errors; this is not a backup system and does not
  promise recovery from abrupt power loss or simultaneous external file changes.
- The app listens on this computer only. It is intended for one local user.

## Manual installation

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

No PowerShell environment activation is required.

## Tests

Double-click **run_tests.bat**, or run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
```

The 14 tests cover scanning, duplicates, limits, exclusions, category/name changes,
collision resolution, date layout, selected-file execution, rollback, undo conflicts,
exports, safe demo creation, approval reset, and UI navigation/preferences.

Verified with Python 3.12 and Streamlit 1.65. The live Ollama model path was not
available for verification; offline mode and the existing AI fallback remain supported.

## Project map

- `app.py` — Streamlit pages, review state, and approval flow
- `assets/style.css` — Premium responsive styling, no external visual assets
- `.streamlit/config.toml` — Consistent theme and local server settings
- `filepilot_core.py` — Scanning, classification, move verification, history, undo
- `filepilot_features.py` — Review edits, collision-safe destinations, insights, exports
- `demo_folder/` — Included sample files
- `practice/` — Fresh demo folders created when requested
- `data/filepilot.db` — Local history, created when needed
- `test_filepilot.py`, `test_premium.py` — Functional and interface tests

Streamlit API reference: https://docs.streamlit.io/develop/api-reference
