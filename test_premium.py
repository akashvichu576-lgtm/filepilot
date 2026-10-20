"""Regression coverage for review edits, scanning boundaries, and the UI workflow."""
import csv
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from filepilot_core import (FilePilotSupervisor, scan_folder, execute_plan, undo_latest,
                            create_demo_folder, sanitize_filename, recent_history)
from filepilot_features import revise_plan, insights, plan_csv


class PremiumTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / "files"
        self.folder.mkdir()

    def analyze(self):
        return FilePilotSupervisor().analyze(self.folder, "Sort files", "http://localhost:1", "test", use_ai=False)

    def test_filters_recursion_size_and_limits(self):
        (self.folder / "a.txt").write_text("one")
        (self.folder / "b.tmp").write_text("ignored")
        (self.folder / "big.bin").write_bytes(b"x" * (1024 * 1024 + 1))
        nested = self.folder / "nested"
        nested.mkdir()
        (nested / "c.txt").write_text("two")
        warnings = []
        rows = scan_folder(self.folder, recursive=False, max_file_mb=1, excluded_patterns=["*.TMP"], warnings=warnings)
        self.assertEqual([f.name for f in rows], ["a.txt"])
        self.assertTrue(any("larger" in w for w in warnings))
        self.assertEqual(len(scan_folder(self.folder, max_file_mb=1, excluded_patterns=["*.tmp"])), 2)
        self.assertEqual(len(scan_folder(self.folder, max_files=1)), 1)

    def test_revision_collision_date_layout_and_selective_undo(self):
        for name in ("a.txt", "b.txt", "c.txt"):
            (self.folder / name).write_text(name)
        result = self.analyze()
        edits = {p.id: {"category": "Career", "name": "Resume.exe", "include": i < 2} for i, p in enumerate(result.plan)}
        plan = revise_plan(result, edits, "Category / Year / Month")
        self.assertEqual(plan[0].proposed_name, "Resume.txt")
        self.assertEqual(plan[1].proposed_name, "Resume (2).txt")
        date = result.files[0].modified_iso
        self.assertIn(str(Path("Career") / date[:4] / date[5:7]), plan[0].destination)
        database = self.root / "history.db"
        outcome = execute_plan(self.folder, plan, database)
        self.assertEqual(outcome["moved"], 2)
        self.assertTrue((self.folder / "c.txt").exists())
        self.assertTrue(undo_latest(database)["ok"])
        self.assertTrue(all((self.folder / n).exists() for n in ("a.txt", "b.txt", "c.txt")))

    def test_export_reflects_current_selection_and_names(self):
        (self.folder / "a.txt").write_text("one")
        result = self.analyze()
        plan = revise_plan(result, {result.plan[0].id: {"name": "=1+1.txt", "include": False}})
        row = list(csv.DictReader(io.StringIO(plan_csv(plan))))[0]
        self.assertEqual(row["Approved"], "False")
        self.assertEqual(row["New name"], "'=1+1.txt")

    def test_invalid_categories_and_windows_names(self):
        (self.folder / "a.txt").write_text("one")
        result = self.analyze()
        with self.assertRaises(ValueError):
            revise_plan(result, {result.plan[0].id: {"category": "../../escape"}})
        self.assertEqual(sanitize_filename("CON.txt", ".txt"), "_CON.txt")
        self.assertEqual(sanitize_filename("../../sample.exe", ".txt"), "sample.txt")

    def test_preserve_names_and_duplicate_bytes(self):
        (self.folder / "a.txt").write_text("same")
        (self.folder / "b.txt").write_text("same")
        result = self.analyze()
        self.assertEqual(insights(result)["duplicate_bytes"], 4)
        plan = revise_plan(result, {result.plan[0].id: {"name": "new.txt"}}, preserve_names=True)
        self.assertEqual(plan[0].proposed_name, "a.txt")

    def test_demo_never_overwrites_existing_folder(self):
        (self.folder / "important.txt").write_text("keep")
        with self.assertRaises(FileExistsError):
            create_demo_folder(self.folder)
        self.assertEqual((self.folder / "important.txt").read_text(), "keep")

    def test_conflict_during_undo_can_be_retried(self):
        original = self.folder / "a.txt"
        original.write_text("one")
        result = self.analyze()
        db = self.root / "history.db"
        execute_plan(self.folder, result.plan, db)
        original.write_text("new content")
        self.assertFalse(undo_latest(db)["ok"])
        self.assertEqual(original.read_text(), "new content")
        original.rename(self.folder / "new-content.txt")
        self.assertTrue(undo_latest(db)["ok"])
        self.assertEqual(original.read_text(), "one")
        self.assertEqual(recent_history(db)[0]["Status"], "undone")

    def test_no_selection_moves_nothing(self):
        (self.folder / "a.txt").write_text("one")
        result = self.analyze()
        plan = revise_plan(result, {result.plan[0].id: {"include": False}})
        self.assertFalse(execute_plan(self.folder, plan, self.root / "db")["ok"])
        self.assertTrue((self.folder / "a.txt").exists())


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        from streamlit.testing.v1 import AppTest
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = create_demo_folder(self.root / "demo")
        env = patch.dict(os.environ, {"FILEPILOT_DATABASE": str(self.root / "history.db")})
        env.start()
        self.addCleanup(env.stop)
        self.app = AppTest.from_file(str(Path(__file__).parent / "app.py"), default_timeout=30).run()
        self.app.session_state["folder"] = str(self.folder)

    def click(self, label):
        button = next(b for b in self.app.button if b.label == label)
        button.click().run()
        self.assertFalse(self.app.exception, [e.value for e in self.app.exception])

    def test_scan_review_approve_execute_and_undo(self):
        self.click("Scan folder")
        self.assertEqual(len(self.app.session_state["analysis"].files), 8)
        self.click("Review plan")
        action = next(b for b in self.app.button if b.label == "Organise selected files")
        self.assertTrue(action.disabled)
        self.click("Unique only")
        self.app.checkbox(key="approval").check().run()
        self.click("Organise selected files")
        self.assertEqual(self.app.session_state["page"], "Activity")
        self.assertEqual(len(list((self.folder / "FilePilot_Organized").rglob("*.*"))), 7)
        self.app.checkbox[0].check().run()
        self.click("Undo latest run")
        self.assertEqual(len(list(self.folder.glob("*.*"))), 8)

    def test_preferences_and_selection_survive_navigation(self):
        self.click("Settings")
        self.app.toggle(key="recursive").set_value(False).run()
        self.app.selectbox(key="layout").select("Category / Year / Month").run()
        self.click("Overview")
        self.click("Scan folder")
        self.click("Review plan")
        self.click("Select none")
        self.click("Duplicates")
        self.click("Review plan")
        self.assertTrue(all(not e["include"] for e in self.app.session_state["draft"].values()))
        self.click("Settings")
        self.assertFalse(self.app.toggle(key="recursive").value)
        self.assertEqual(self.app.selectbox(key="layout").value, "Category / Year / Month")

    def test_bulk_change_clears_approval_and_search_preserves_selection(self):
        self.click("Scan folder")
        self.click("Review plan")
        self.app.checkbox(key="approval").check().run()
        self.click("Select none")
        self.assertFalse(self.app.checkbox(key="approval").value)
        self.app.text_input[0].set_value("bill").run()
        self.assertTrue(all(not e["include"] for e in self.app.session_state["draft"].values()))
        self.assertFalse(self.app.exception)


if __name__ == "__main__":
    unittest.main()
