from __future__ import annotations

import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tripagent.jsonx import dumps_str


class Persistence:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _connection(self):
        conn = self._connect()
        try:
            yield conn
        finally:
            conn.close()

    @staticmethod
    def _now_unix() -> int:
        return int(time.time())

    @staticmethod
    def _today_ymd() -> str:
        return datetime.now(UTC).strftime("%Y-%m-%d")

    @staticmethod
    def _current_month_ym() -> str:
        return datetime.now(UTC).strftime("%Y-%m")

    def _init_db(self) -> None:
        with self._connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    expires_at INTEGER NOT NULL,
                    created_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS daily_quota (
                    username TEXT NOT NULL,
                    day TEXT NOT NULL,
                    count INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (username, day)
                );

                CREATE TABLE IF NOT EXISTS queued_plan_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued',
                    created_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS business_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT NOT NULL,
                    status_code INTEGER NOT NULL,
                    session_id TEXT,
                    user_id TEXT,
                    est_api_cost REAL NOT NULL DEFAULT 0,
                    est_ads_revenue REAL NOT NULL DEFAULT 0,
                    latency_ms REAL NOT NULL DEFAULT 0,
                    meta_json TEXT,
                    created_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ab_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    user_id TEXT,
                    experiment TEXT NOT NULL,
                    variant TEXT NOT NULL,
                    objective TEXT,
                    event_type TEXT NOT NULL,
                    value REAL NOT NULL DEFAULT 0,
                    meta_json TEXT,
                    created_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS user_subscriptions (
                    username TEXT PRIMARY KEY,
                    plan_tier TEXT NOT NULL DEFAULT 'free',
                    status TEXT NOT NULL DEFAULT 'inactive',
                    renews_at INTEGER,
                    monthly_price REAL NOT NULL DEFAULT 0,
                    updated_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS revenue_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    source TEXT NOT NULL,
                    amount REAL NOT NULL DEFAULT 0,
                    meta_json TEXT,
                    created_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    created_at INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active'
                );

                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id INTEGER PRIMARY KEY,
                    email TEXT,
                    full_name TEXT,
                    country_code TEXT,
                    timezone TEXT,
                    marketing_opt_in INTEGER NOT NULL DEFAULT 0,
                    updated_at INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS plans (
                    code TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    monthly_price REAL NOT NULL DEFAULT 0,
                    daily_quota INTEGER NOT NULL DEFAULT 0,
                    active INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    plan_code TEXT NOT NULL,
                    status TEXT NOT NULL,
                    starts_at INTEGER NOT NULL,
                    ends_at INTEGER,
                    renews_at INTEGER,
                    price_monthly REAL NOT NULL DEFAULT 0,
                    currency TEXT NOT NULL DEFAULT 'CLP',
                    created_at INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (plan_code) REFERENCES plans(code)
                );

                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    subscription_id INTEGER,
                    provider TEXT NOT NULL,
                    external_payment_id TEXT,
                    amount REAL NOT NULL DEFAULT 0,
                    currency TEXT NOT NULL DEFAULT 'CLP',
                    status TEXT NOT NULL,
                    paid_at INTEGER,
                    created_at INTEGER NOT NULL,
                    meta_json TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (subscription_id) REFERENCES subscriptions(id)
                );

                CREATE TABLE IF NOT EXISTS ledger_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_type TEXT NOT NULL,
                    category TEXT NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT NOT NULL DEFAULT 'CLP',
                    month_ym TEXT NOT NULL,
                    ref_type TEXT,
                    ref_id TEXT,
                    created_at INTEGER NOT NULL,
                    meta_json TEXT
                );

                CREATE TABLE IF NOT EXISTS pricing_state (
                    key TEXT PRIMARY KEY,
                    value REAL NOT NULL,
                    updated_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS pricing_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    price_type TEXT NOT NULL,
                    old_value REAL NOT NULL,
                    new_value REAL NOT NULL,
                    reason TEXT,
                    created_at INTEGER NOT NULL,
                    meta_json TEXT
                );

                CREATE TABLE IF NOT EXISTS infra_cost_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    month_ym TEXT NOT NULL,
                    amount REAL NOT NULL DEFAULT 0,
                    notes TEXT,
                    created_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS finance_reconcile_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    month_ym TEXT NOT NULL UNIQUE,
                    revenue_total REAL NOT NULL DEFAULT 0,
                    cost_total REAL NOT NULL DEFAULT 0,
                    margin REAL NOT NULL DEFAULT 0,
                    recommended_price REAL NOT NULL DEFAULT 0,
                    applied INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    meta_json TEXT
                );
                """
            )
            conn.execute(
                """
                INSERT INTO plans(code, name, monthly_price, daily_quota, active)
                VALUES
                    ('free', 'Free', 0, 10, 1),
                    ('pro', 'Pro', 0, 100, 1)
                ON CONFLICT(code) DO NOTHING
                """
            )
            conn.commit()

    def save_session(self, token: str, username: str, expires_at: int) -> None:
        now = self._now_unix()
        with self._lock, self._connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sessions(token, username, expires_at, created_at) VALUES(?,?,?,?)",
                (token, username, expires_at, now),
            )
            conn.commit()

    def get_session(self, token: str) -> dict[str, Any] | None:
        now = self._now_unix()
        with self._lock, self._connection() as conn:
            row = conn.execute(
                "SELECT token, username, expires_at FROM sessions WHERE token = ?",
                (token,),
            ).fetchone()
            if not row:
                return None
            if int(row["expires_at"]) <= now:
                conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
                conn.commit()
                return None
            return {"token": row["token"], "username": row["username"], "expires_at": int(row["expires_at"])}

    def increment_daily_quota(self, username: str) -> int:
        day = self._today_ymd()
        with self._lock, self._connection() as conn:
            conn.execute(
                "INSERT INTO daily_quota(username, day, count) VALUES(?,?,1) ON CONFLICT(username, day) DO UPDATE SET count = count + 1",
                (username, day),
            )
            row = conn.execute(
                "SELECT count FROM daily_quota WHERE username = ? AND day = ?",
                (username, day),
            ).fetchone()
            conn.commit()
            return int(row["count"]) if row else 0

    def try_increment_daily_quota(self, username: str, limit: int) -> tuple[bool, int]:
        day = self._today_ymd()
        safe_limit = max(1, int(limit))
        with self._lock, self._connection() as conn:
            conn.execute(
                "INSERT INTO daily_quota(username, day, count) VALUES(?,?,0) ON CONFLICT(username, day) DO NOTHING",
                (username, day),
            )
            cur = conn.execute(
                "UPDATE daily_quota SET count = count + 1 WHERE username = ? AND day = ? AND count < ?",
                (username, day, safe_limit),
            )
            row = conn.execute(
                "SELECT count FROM daily_quota WHERE username = ? AND day = ?",
                (username, day),
            ).fetchone()
            conn.commit()
            used = int(row["count"]) if row else 0
            return cur.rowcount > 0, used

    def decrement_daily_quota(self, username: str) -> int:
        day = self._today_ymd()
        with self._lock, self._connection() as conn:
            conn.execute(
                "UPDATE daily_quota SET count = CASE WHEN count > 0 THEN count - 1 ELSE 0 END WHERE username = ? AND day = ?",
                (username, day),
            )
            row = conn.execute(
                "SELECT count FROM daily_quota WHERE username = ? AND day = ?",
                (username, day),
            ).fetchone()
            conn.commit()
            return int(row["count"]) if row else 0

    def get_daily_quota(self, username: str) -> int:
        day = self._today_ymd()
        with self._lock, self._connection() as conn:
            row = conn.execute(
                "SELECT count FROM daily_quota WHERE username = ? AND day = ?",
                (username, day),
            ).fetchone()
            return int(row["count"]) if row else 0

    def enqueue_plan_request(self, username: str, payload: dict[str, Any], reason: str) -> int:
        now = self._now_unix()
        with self._lock, self._connection() as conn:
            cur = conn.execute(
                "INSERT INTO queued_plan_requests(username, payload_json, reason, created_at) VALUES(?,?,?,?)",
                (username, dumps_str(payload), reason, now),
            )
            conn.commit()
            return int(cur.lastrowid)

    def list_queue_for_user(self, username: str, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock, self._connection() as conn:
            rows = conn.execute(
                "SELECT id, reason, status, created_at FROM queued_plan_requests WHERE username = ? ORDER BY id DESC LIMIT ?",
                (username, max(1, limit)),
            ).fetchall()
            return [
                {
                    "id": int(r["id"]),
                    "reason": r["reason"],
                    "status": r["status"],
                    "created_at": int(r["created_at"]),
                }
                for r in rows
            ]

    def record_business_event(
        self,
        *,
        endpoint: str,
        status_code: int,
        session_id: str | None,
        user_id: str | None,
        est_api_cost: float,
        est_ads_revenue: float,
        latency_ms: float,
        meta: dict[str, Any] | None,
    ) -> None:
        now = self._now_unix()
        month_ym = self._current_month_ym()
        with self._lock, self._connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO business_events(endpoint, status_code, session_id, user_id, est_api_cost, est_ads_revenue, latency_ms, meta_json, created_at)
                VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    endpoint,
                    status_code,
                    session_id,
                    user_id,
                    float(est_api_cost),
                    float(est_ads_revenue),
                    float(latency_ms),
                    dumps_str(meta or {}),
                    now,
                ),
            )
            ref_id = str(cur.lastrowid)
            api_cost = float(est_api_cost)
            ads_revenue = float(est_ads_revenue)
            if api_cost > 0:
                conn.execute(
                    """
                    INSERT INTO ledger_entries(entry_type, category, amount, currency, month_ym, ref_type, ref_id, created_at, meta_json)
                    VALUES('cost', 'api', ?, 'CLP', ?, 'business_events', ?, ?, ?)
                    """,
                    (api_cost, month_ym, ref_id, now, dumps_str({"endpoint": endpoint})),
                )
            if ads_revenue > 0:
                conn.execute(
                    """
                    INSERT INTO ledger_entries(entry_type, category, amount, currency, month_ym, ref_type, ref_id, created_at, meta_json)
                    VALUES('revenue', 'ads', ?, 'CLP', ?, 'business_events', ?, ?, ?)
                    """,
                    (ads_revenue, month_ym, ref_id, now, dumps_str({"endpoint": endpoint})),
                )
            conn.commit()

    def business_snapshot(self) -> dict[str, Any]:
        with self._lock, self._connection() as conn:
            totals = conn.execute(
                """
                SELECT
                    COUNT(*) AS requests,
                    COALESCE(SUM(est_api_cost),0) AS api_cost,
                    COALESCE(SUM(est_ads_revenue),0) AS ads_revenue,
                    COALESCE(AVG(latency_ms),0) AS avg_latency
                FROM business_events
                """
            ).fetchone()
            per_user = conn.execute(
                """
                SELECT user_id, COUNT(*) AS reqs,
                       COALESCE(SUM(est_ads_revenue),0) AS ads_revenue,
                       COALESCE(SUM(est_api_cost),0) AS api_cost
                FROM business_events
                WHERE user_id IS NOT NULL
                GROUP BY user_id
                ORDER BY reqs DESC
                LIMIT 50
                """
            ).fetchall()
            return {
                "totals": {
                    "requests": int(totals["requests"]),
                    "api_cost": float(totals["api_cost"]),
                    "ads_revenue": float(totals["ads_revenue"]),
                    "margin": float(totals["ads_revenue"]) - float(totals["api_cost"]),
                    "avg_latency_ms": round(float(totals["avg_latency"]), 2),
                },
                "users": [
                    {
                        "user_id": row["user_id"],
                        "requests": int(row["reqs"]),
                        "ads_revenue": float(row["ads_revenue"]),
                        "api_cost": float(row["api_cost"]),
                        "margin": float(row["ads_revenue"]) - float(row["api_cost"]),
                    }
                    for row in per_user
                ],
            }

    def business_snapshot_since(self, since_unix: int) -> dict[str, Any]:
        with self._lock, self._connection() as conn:
            totals = conn.execute(
                """
                SELECT
                    COUNT(*) AS requests,
                    COALESCE(SUM(est_api_cost),0) AS api_cost,
                    COALESCE(SUM(est_ads_revenue),0) AS ads_revenue,
                    COALESCE(AVG(latency_ms),0) AS avg_latency
                FROM business_events
                WHERE created_at >= ?
                """,
                (int(since_unix),),
            ).fetchone()
            by_endpoint = conn.execute(
                """
                SELECT endpoint,
                       COUNT(*) AS requests,
                       COALESCE(SUM(est_api_cost),0) AS api_cost,
                       COALESCE(AVG(latency_ms),0) AS avg_latency
                FROM business_events
                WHERE created_at >= ?
                GROUP BY endpoint
                ORDER BY requests DESC
                """,
                (int(since_unix),),
            ).fetchall()
            return {
                "totals": {
                    "requests": int(totals["requests"]),
                    "api_cost": float(totals["api_cost"]),
                    "ads_revenue": float(totals["ads_revenue"]),
                    "margin": float(totals["ads_revenue"]) - float(totals["api_cost"]),
                    "avg_latency_ms": round(float(totals["avg_latency"]), 2),
                },
                "by_endpoint": [
                    {
                        "endpoint": row["endpoint"],
                        "requests": int(row["requests"]),
                        "api_cost": float(row["api_cost"]),
                        "avg_latency_ms": round(float(row["avg_latency"]), 2),
                    }
                    for row in by_endpoint
                ],
            }

    def record_ab_event(
        self,
        *,
        session_id: str | None,
        user_id: str | None,
        experiment: str,
        variant: str,
        objective: str | None,
        event_type: str,
        value: float = 0.0,
        meta: dict[str, Any] | None = None,
    ) -> None:
        now = self._now_unix()
        with self._lock, self._connection() as conn:
            conn.execute(
                """
                INSERT INTO ab_events(session_id, user_id, experiment, variant, objective, event_type, value, meta_json, created_at)
                VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    session_id,
                    user_id,
                    experiment,
                    variant,
                    objective,
                    event_type,
                    float(value),
                    dumps_str(meta or {}),
                    now,
                ),
            )
            conn.commit()

    def ab_report(self, experiment: str, since_unix: int) -> dict[str, Any]:
        with self._lock, self._connection() as conn:
            rows = conn.execute(
                """
                SELECT variant,
                       event_type,
                       COUNT(*) AS n,
                       COALESCE(SUM(value),0) AS total_value
                FROM ab_events
                WHERE experiment = ? AND created_at >= ?
                GROUP BY variant, event_type
                """,
                (experiment, int(since_unix)),
            ).fetchall()
            by_variant: dict[str, dict[str, Any]] = {}
            for row in rows:
                variant = str(row["variant"])
                event_type = str(row["event_type"])
                info = by_variant.setdefault(
                    variant,
                    {
                        "variant": variant,
                        "exposures": 0,
                        "conversions": 0,
                        "retained_users": 0,
                        "value_total": 0.0,
                    },
                )
                n = int(row["n"])
                if event_type == "exposure":
                    info["exposures"] = n
                elif event_type == "conversion":
                    info["conversions"] = n
                    info["value_total"] = float(row["total_value"])
                elif event_type == "retention":
                    info["retained_users"] = n
            out = []
            for item in by_variant.values():
                exposures = max(1, int(item["exposures"]))
                item["conversion_rate"] = round(float(item["conversions"]) / exposures, 4)
                item["retention_rate"] = round(float(item["retained_users"]) / exposures, 4)
                item["value_total"] = round(float(item["value_total"]), 4)
                out.append(item)
            out.sort(key=lambda x: x["variant"])
            return {"experiment": experiment, "variants": out}

    def ensure_user_plan(self, username: str) -> None:
        self.ensure_user(username)
        now = self._now_unix()
        with self._lock, self._connection() as conn:
            conn.execute(
                """
                INSERT INTO user_subscriptions(username, plan_tier, status, renews_at, monthly_price, updated_at)
                VALUES(?, 'free', 'inactive', NULL, 0, ?)
                ON CONFLICT(username) DO NOTHING
                """,
                (username, now),
            )
            conn.commit()

    def ensure_user(self, username: str) -> int:
        now = self._now_unix()
        with self._lock, self._connection() as conn:
            conn.execute(
                "INSERT INTO users(username, created_at, status) VALUES(?,?, 'active') ON CONFLICT(username) DO NOTHING",
                (username, now),
            )
            row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            conn.commit()
            if not row:
                raise RuntimeError(f"Could not ensure user row for {username}")
            return int(row["id"])

    def get_user_plan(self, username: str) -> dict[str, Any]:
        self.ensure_user_plan(username)
        with self._lock, self._connection() as conn:
            row = conn.execute(
                """
                SELECT username, plan_tier, status, renews_at, monthly_price, updated_at
                FROM user_subscriptions
                WHERE username = ?
                """,
                (username,),
            ).fetchone()
            if not row:
                return {
                    "username": username,
                    "plan_tier": "free",
                    "status": "inactive",
                    "renews_at": None,
                    "monthly_price": 0.0,
                    "updated_at": int(time.time()),
                }
            return {
                "username": row["username"],
                "plan_tier": row["plan_tier"],
                "status": row["status"],
                "renews_at": int(row["renews_at"]) if row["renews_at"] is not None else None,
                "monthly_price": float(row["monthly_price"]),
                "updated_at": int(row["updated_at"]),
            }

    def set_user_subscription(
        self,
        *,
        username: str,
        plan_tier: str,
        status: str,
        renews_at: int | None,
        monthly_price: float,
    ) -> None:
        now = self._now_unix()
        user_id = self.ensure_user(username)
        with self._lock, self._connection() as conn:
            conn.execute(
                """
                INSERT INTO user_subscriptions(username, plan_tier, status, renews_at, monthly_price, updated_at)
                VALUES(?,?,?,?,?,?)
                ON CONFLICT(username) DO UPDATE SET
                    plan_tier = excluded.plan_tier,
                    status = excluded.status,
                    renews_at = excluded.renews_at,
                    monthly_price = excluded.monthly_price,
                    updated_at = excluded.updated_at
                """,
                (username, plan_tier, status, renews_at, float(monthly_price), now),
            )
            conn.commit()
        self.record_subscription_snapshot(
            username=username,
            plan_tier=plan_tier,
            status=status,
            renews_at=renews_at,
            monthly_price=monthly_price,
            user_id=user_id,
        )

    def record_subscription_snapshot(
        self,
        *,
        username: str,
        plan_tier: str,
        status: str,
        renews_at: int | None,
        monthly_price: float,
        user_id: int | None = None,
    ) -> None:
        now = self._now_unix()
        uid = user_id if user_id is not None else self.ensure_user(username)
        with self._lock, self._connection() as conn:
            conn.execute(
                """
                INSERT INTO subscriptions(user_id, plan_code, status, starts_at, ends_at, renews_at, price_monthly, currency, created_at)
                VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    uid,
                    plan_tier,
                    status,
                    now,
                    None if status == "active" else now,
                    renews_at,
                    float(monthly_price),
                    "CLP",
                    now,
                ),
            )
            conn.commit()

    def record_revenue_event(
        self,
        *,
        username: str | None,
        source: str,
        amount: float,
        meta: dict[str, Any] | None = None,
    ) -> None:
        now = self._now_unix()
        month_ym = self._current_month_ym()
        ref_id = None
        user_id = None
        if username:
            user_id = self.ensure_user(username)
        with self._lock, self._connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO revenue_events(username, source, amount, meta_json, created_at)
                VALUES(?,?,?,?,?)
                """,
                (username, source, float(amount), dumps_str(meta or {}), now),
            )
            ref_id = str(cur.lastrowid)
            conn.execute(
                """
                INSERT INTO ledger_entries(entry_type, category, amount, currency, month_ym, ref_type, ref_id, created_at, meta_json)
                VALUES('revenue', ?, ?, 'CLP', ?, 'revenue_events', ?, ?, ?)
                """,
                (
                    source,
                    float(amount),
                    month_ym,
                    ref_id,
                    now,
                    dumps_str({"username": username, "user_id": user_id}),
                ),
            )
            conn.commit()

    def revenue_snapshot_since(self, since_unix: int) -> dict[str, Any]:
        with self._lock, self._connection() as conn:
            totals = conn.execute(
                """
                SELECT
                    COUNT(*) AS events,
                    COALESCE(SUM(amount),0) AS amount
                FROM revenue_events
                WHERE created_at >= ?
                """,
                (int(since_unix),),
            ).fetchone()
            by_source = conn.execute(
                """
                SELECT source, COUNT(*) AS events, COALESCE(SUM(amount),0) AS amount
                FROM revenue_events
                WHERE created_at >= ?
                GROUP BY source
                ORDER BY amount DESC
                """,
                (int(since_unix),),
            ).fetchall()
            return {
                "totals": {
                    "events": int(totals["events"]),
                    "amount": float(totals["amount"]),
                },
                "sources": [
                    {"source": row["source"], "events": int(row["events"]), "amount": float(row["amount"])}
                    for row in by_source
                ],
            }

    def set_current_subscription_price(self, value: float, reason: str, meta: dict[str, Any] | None = None) -> None:
        now = self._now_unix()
        old_value = self.get_current_subscription_price(default=0.0)
        with self._lock, self._connection() as conn:
            conn.execute(
                """
                INSERT INTO pricing_state(key, value, updated_at)
                VALUES('subscription_monthly_price', ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (float(value), now),
            )
            conn.execute(
                """
                INSERT INTO pricing_history(price_type, old_value, new_value, reason, created_at, meta_json)
                VALUES('subscription_monthly_price', ?, ?, ?, ?, ?)
                """,
                (float(old_value), float(value), reason, now, dumps_str(meta or {})),
            )
            conn.commit()

    def get_current_subscription_price(self, default: float) -> float:
        with self._lock, self._connection() as conn:
            row = conn.execute(
                "SELECT value FROM pricing_state WHERE key = 'subscription_monthly_price'"
            ).fetchone()
            if not row:
                return float(default)
            return float(row["value"])

    def upsert_infra_cost(self, month_ym: str, amount: float, notes: str | None = None) -> None:
        now = self._now_unix()
        with self._lock, self._connection() as conn:
            conn.execute(
                "DELETE FROM infra_cost_events WHERE month_ym = ?",
                (month_ym,),
            )
            conn.execute(
                """
                INSERT INTO infra_cost_events(month_ym, amount, notes, created_at)
                VALUES(?,?,?,?)
                """,
                (month_ym, float(amount), notes, now),
            )
            conn.execute(
                """
                INSERT INTO ledger_entries(entry_type, category, amount, currency, month_ym, ref_type, ref_id, created_at, meta_json)
                VALUES('cost', 'infra', ?, 'CLP', ?, 'infra_cost_events', ?, ?, ?)
                """,
                (
                    float(amount),
                    month_ym,
                    month_ym,
                    now,
                    dumps_str({"notes": notes or ""}),
                ),
            )
            conn.commit()

    def get_infra_cost(self, month_ym: str) -> float:
        with self._lock, self._connection() as conn:
            row = conn.execute(
                "SELECT amount FROM infra_cost_events WHERE month_ym = ? ORDER BY id DESC LIMIT 1",
                (month_ym,),
            ).fetchone()
            if not row:
                return 0.0
            return float(row["amount"])

    def month_cashflow(self, month_ym: str) -> dict[str, Any]:
        with self._lock, self._connection() as conn:
            revenue = conn.execute(
                """
                SELECT COALESCE(SUM(amount),0) AS amount
                FROM ledger_entries
                WHERE month_ym = ? AND entry_type = 'revenue'
                """,
                (month_ym,),
            ).fetchone()
            cost = conn.execute(
                """
                SELECT COALESCE(SUM(amount),0) AS amount
                FROM ledger_entries
                WHERE month_ym = ? AND entry_type = 'cost'
                """,
                (month_ym,),
            ).fetchone()
            by_category = conn.execute(
                """
                SELECT entry_type, category, COALESCE(SUM(amount),0) AS amount
                FROM ledger_entries
                WHERE month_ym = ?
                GROUP BY entry_type, category
                ORDER BY entry_type, amount DESC
                """,
                (month_ym,),
            ).fetchall()
            revenue_total = float(revenue["amount"])
            cost_total = float(cost["amount"])
            return {
                "month_ym": month_ym,
                "revenue_total": revenue_total,
                "cost_total": cost_total,
                "margin": revenue_total - cost_total,
                "lines": [
                    {
                        "entry_type": row["entry_type"],
                        "category": row["category"],
                        "amount": float(row["amount"]),
                    }
                    for row in by_category
                ],
            }

    def log_cost_entry(self, month_ym: str, category: str, amount: float, ref_type: str, ref_id: str) -> None:
        now = self._now_unix()
        with self._lock, self._connection() as conn:
            conn.execute(
                """
                INSERT INTO ledger_entries(entry_type, category, amount, currency, month_ym, ref_type, ref_id, created_at, meta_json)
                VALUES('cost', ?, ?, 'CLP', ?, ?, ?, ?, ?)
                """,
                (category, float(amount), month_ym, ref_type, ref_id, now, dumps_str({})),
            )
            conn.commit()

    def record_finance_reconcile(
        self,
        *,
        month_ym: str,
        revenue_total: float,
        cost_total: float,
        margin: float,
        recommended_price: float,
        applied: bool,
        meta: dict[str, Any] | None = None,
    ) -> None:
        now = self._now_unix()
        with self._lock, self._connection() as conn:
            conn.execute(
                """
                INSERT INTO finance_reconcile_runs(month_ym, revenue_total, cost_total, margin, recommended_price, applied, created_at, meta_json)
                VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(month_ym) DO UPDATE SET
                    revenue_total = excluded.revenue_total,
                    cost_total = excluded.cost_total,
                    margin = excluded.margin,
                    recommended_price = excluded.recommended_price,
                    applied = excluded.applied,
                    created_at = excluded.created_at,
                    meta_json = excluded.meta_json
                """,
                (
                    month_ym,
                    float(revenue_total),
                    float(cost_total),
                    float(margin),
                    float(recommended_price),
                    1 if applied else 0,
                    now,
                    dumps_str(meta or {}),
                ),
            )
            conn.commit()

    def count_user_tiers(self) -> dict[str, int]:
        with self._lock, self._connection() as conn:
            rows = conn.execute(
                """
                SELECT plan_tier, COUNT(*) AS n
                FROM user_subscriptions
                GROUP BY plan_tier
                """
            ).fetchall()
            out = {"free": 0, "pro": 0}
            for row in rows:
                tier = str(row["plan_tier"]).lower()
                out[tier] = int(row["n"])
            return out

    def ledger_months(self) -> list[str]:
        with self._lock, self._connection() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT month_ym
                FROM ledger_entries
                ORDER BY month_ym
                """
            ).fetchall()
            return [str(row["month_ym"]) for row in rows if row["month_ym"]]


DB_PATH = os.getenv("TRIPAGENT_DB_PATH", "out/tripagent.db")
PERSISTENCE = Persistence(DB_PATH)


