import os
import tempfile
import unittest

from tripagent.persistence import Persistence


class PersistenceTests(unittest.TestCase):
    def _tmp_db_path(self) -> str:
        fd, path = tempfile.mkstemp(prefix="tripagent_test_", suffix=".db")
        os.close(fd)
        return path

    def test_quota_increment(self):
        db_path = self._tmp_db_path()
        try:
            p = Persistence(db_path)
            before = p.get_daily_quota("u1")
            self.assertEqual(before, 0)
            now = p.increment_daily_quota("u1")
            self.assertEqual(now, 1)
            now2 = p.increment_daily_quota("u1")
            self.assertEqual(now2, 2)
        finally:
            try:
                os.remove(db_path)
            except OSError:
                pass

    def test_queue_insert(self):
        db_path = self._tmp_db_path()
        try:
            p = Persistence(db_path)
            qid = p.enqueue_plan_request("u1", {"k": 1}, "fallback")
            self.assertTrue(qid > 0)
            items = p.list_queue_for_user("u1")
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["id"], qid)
        finally:
            try:
                os.remove(db_path)
            except OSError:
                pass

    def test_try_increment_daily_quota_respects_limit(self):
        db_path = self._tmp_db_path()
        try:
            p = Persistence(db_path)
            ok1, used1 = p.try_increment_daily_quota("u1", 2)
            ok2, used2 = p.try_increment_daily_quota("u1", 2)
            ok3, used3 = p.try_increment_daily_quota("u1", 2)
            self.assertTrue(ok1)
            self.assertTrue(ok2)
            self.assertFalse(ok3)
            self.assertEqual(used1, 1)
            self.assertEqual(used2, 2)
            self.assertEqual(used3, 2)
        finally:
            try:
                os.remove(db_path)
            except OSError:
                pass

    def test_decrement_daily_quota(self):
        db_path = self._tmp_db_path()
        try:
            p = Persistence(db_path)
            p.try_increment_daily_quota("u1", 5)
            p.try_increment_daily_quota("u1", 5)
            now = p.decrement_daily_quota("u1")
            self.assertEqual(now, 1)
        finally:
            try:
                os.remove(db_path)
            except OSError:
                pass

    def test_business_snapshot_since(self):
        db_path = self._tmp_db_path()
        try:
            p = Persistence(db_path)
            p.record_business_event(
                endpoint="/plan",
                status_code=200,
                session_id="s1",
                user_id="u1",
                est_api_cost=1.2,
                est_ads_revenue=0.1,
                latency_ms=50,
                meta={},
            )
            snap = p.business_snapshot_since(0)
            self.assertGreaterEqual(snap["totals"]["requests"], 1)
            self.assertTrue(any(row["endpoint"] == "/plan" for row in snap["by_endpoint"]))
        finally:
            try:
                os.remove(db_path)
            except OSError:
                pass

    def test_ab_report(self):
        db_path = self._tmp_db_path()
        try:
            p = Persistence(db_path)
            p.record_ab_event(
                session_id="sid1",
                user_id="u1",
                experiment="objective_default",
                variant="time",
                objective="time",
                event_type="exposure",
                value=0.0,
                meta={},
            )
            p.record_ab_event(
                session_id="sid1",
                user_id="u1",
                experiment="objective_default",
                variant="time",
                objective="time",
                event_type="conversion",
                value=1.0,
                meta={},
            )
            report = p.ab_report("objective_default", 0)
            self.assertEqual(report["experiment"], "objective_default")
            self.assertTrue(any(v["variant"] == "time" for v in report["variants"]))
        finally:
            try:
                os.remove(db_path)
            except OSError:
                pass

    def test_user_subscription_and_revenue(self):
        db_path = self._tmp_db_path()
        try:
            p = Persistence(db_path)
            p.ensure_user_plan("demo")
            base = p.get_user_plan("demo")
            self.assertEqual(base["plan_tier"], "free")
            p.set_user_subscription(
                username="demo",
                plan_tier="pro",
                status="active",
                renews_at=9999999999,
                monthly_price=9.9,
            )
            plan = p.get_user_plan("demo")
            self.assertEqual(plan["plan_tier"], "pro")
            p.record_revenue_event(username="demo", source="subscription", amount=9.9, meta={})
            snap = p.revenue_snapshot_since(0)
            self.assertGreaterEqual(snap["totals"]["amount"], 9.9)
        finally:
            try:
                os.remove(db_path)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
