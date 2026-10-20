"""Review customisation and exports. These functions never move files."""
from __future__ import annotations

import csv
import io
from collections import Counter
from dataclasses import replace
from pathlib import Path

from filepilot_core import (
    AnalysisResult, CATEGORIES, ORGANIZED_FOLDER, PlanItem,
    sanitize_filename, unique_destination, validate_plan,
)


def revise_plan(result: AnalysisResult, edits: dict[str, dict] | None = None,
                layout: str = "Category", preserve_names: bool = False) -> list[PlanItem]:
    """Rebuild collision-free destinations from explicit review choices."""
    if layout not in ("Category", "Category / Year / Month"):
        raise ValueError("Unknown folder layout.")
    edits = edits or {}
    reserved: set[str] = set()
    records = {f.id: f for f in result.files}
    revised = []
    for item in result.plan:
        change = edits.get(item.id, {})
        category = change.get("category", item.category)
        if category not in CATEGORIES:
            raise ValueError(f"Unknown category: {category}")
        record = records[item.id]
        name = record.name if preserve_names else change.get("name", item.proposed_name)
        name = sanitize_filename(name, record.extension)
        folder = Path(result.target) / ORGANIZED_FOLDER / category
        if layout == "Category / Year / Month":
            folder = folder / record.modified_iso[:4] / record.modified_iso[5:7]
        destination = unique_destination(folder, name, reserved)
        revised.append(replace(item, category=category, proposed_name=destination.name,
                               destination=str(destination), include=bool(change.get("include", item.include))))
    validate_plan(result.target, revised)
    return revised


def plan_csv(plan: list[PlanItem]) -> str:
    """Export exactly the reviewed selection; neutralise spreadsheet formulas."""
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["Approved", "Current file", "Category", "New name", "Destination", "Confidence", "Duplicate of", "Reason"])
    def safe(value):
        text = str(value)
        return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")) else text
    for item in plan:
        writer.writerow([item.include, safe(item.relative_source), item.category,
                         safe(item.proposed_name), safe(item.destination),
                         round(item.confidence * 100), safe(item.duplicate_of), safe(item.reason)])
    return output.getvalue()


def insights(result: AnalysisResult) -> dict:
    duplicate_ids = {p.id for p in result.plan if p.duplicate_of}
    return {
        "categories": dict(Counter(p.category for p in result.plan)),
        "duplicate_bytes": sum(f.size_bytes for f in result.files if f.id in duplicate_ids),
        "needs_review": sum(p.confidence < .7 and not p.duplicate_of for p in result.plan),
        "largest": sorted(result.files, key=lambda f: f.size_bytes, reverse=True)[:5],
    }
