import tempfile
import unittest
from pathlib import Path

from filepilot_core import (
    FilePilotSupervisor,
    execute_plan,
    find_duplicates,
    scan_folder,
    undo_latest,
)


class FilePilotTests(unittest.TestCase):
    def test_scan_and_duplicate_detection(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "one.txt").write_text("same", encoding="utf-8")
            (folder / "two.txt").write_text("same", encoding="utf-8")
            records = scan_folder(folder)
            self.assertEqual(len(records), 2)
            self.assertEqual(len(find_duplicates(records)), 1)

    def test_plan_execute_verify_and_undo(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "target"
            folder.mkdir()
            original = folder / "assignment.txt"
            original.write_text("College assignment for Agentic AI", encoding="utf-8")
            database = Path(temp) / "history.db"

            result = FilePilotSupervisor().analyze(
                folder,
                goal="Organise college files",
                base_url="http://127.0.0.1:1",
                model="qwen2.5:3b",
                use_ai=False,
            )
            self.assertEqual(len(result.plan), 1)
            self.assertEqual(result.plan[0].category, "College")

            execution = execute_plan(folder, result.plan, database)
            self.assertTrue(execution["ok"])
            self.assertFalse(original.exists())
            self.assertTrue(Path(result.plan[0].destination).exists())

            undone = undo_latest(database)
            self.assertTrue(undone["ok"])
            self.assertTrue(original.exists())

    def test_changed_file_stops_run_and_rolls_back_completed_moves(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "target"
            folder.mkdir()
            first = folder / "a_assignment.txt"
            second = folder / "b_assignment.txt"
            first.write_text("College assignment one", encoding="utf-8")
            second.write_text("College assignment two", encoding="utf-8")
            database = Path(temp) / "history.db"

            result = FilePilotSupervisor().analyze(
                folder,
                goal="Organise college files",
                base_url="http://127.0.0.1:1",
                model="qwen2.5:3b",
                use_ai=False,
            )
            second.write_text("Changed after the plan was made", encoding="utf-8")
            execution = execute_plan(folder, result.plan, database)

            self.assertFalse(execution["ok"])
            self.assertTrue(first.exists())
            self.assertTrue(second.exists())
            self.assertFalse(Path(result.plan[0].destination).exists())


if __name__ == "__main__":
    unittest.main()

