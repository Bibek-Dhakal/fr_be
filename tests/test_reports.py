import os
import unittest

os.environ["REPORTS_IN_MEMORY"] = "1"

from app.reports import ReportStore  # noqa: E402


class ReportStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = ReportStore()

    def test_report_lifecycle_and_idempotent_completion(self) -> None:
        report = self.store.create("cats")
        self.assertEqual(report["status"], "pending")
        self.assertTrue(self.store.claim(report["id"]))
        self.assertFalse(self.store.claim(report["id"]))
        self.assertTrue(self.store.complete(report["id"], "ready"))
        self.assertFalse(self.store.complete(report["id"], "ready again"))
        self.assertEqual(self.store.get(report["id"])["status"], "done")

    def test_unknown_report_is_missing(self) -> None:
        self.assertIsNone(self.store.get("missing"))


if __name__ == "__main__":
    unittest.main()
