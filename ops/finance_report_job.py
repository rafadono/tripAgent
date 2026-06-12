from __future__ import annotations

import argparse
from calendar import monthrange
from datetime import UTC, datetime

from tripagent.config import get_settings, load_env
from tripagent.finance import annual_cashflow, current_month_ym, feasibility_summary, reconcile_month
from tripagent.reporting import write_annual_finance_report, write_monthly_finance_report


def _is_last_day(dt: datetime) -> bool:
    return dt.day == monthrange(dt.year, dt.month)[1]


def run_monthly(apply_price: bool, month_ym: str | None = None) -> dict[str, str]:
    settings = get_settings()
    month = month_ym or current_month_ym()
    rec = reconcile_month(settings, month, apply_price=apply_price)
    feasibility = feasibility_summary(settings)
    files = write_monthly_finance_report(
        out_dir="out",
        month_ym=month,
        cashflow=rec["flow"],
        recommendation=rec.get("recommendation"),
        feasibility=feasibility,
        applied_price_change=bool(rec.get("applied")),
    )
    return files


def run_annual(year: int, scope: str) -> dict[str, str]:
    settings = get_settings()
    annual = annual_cashflow(settings, year=year, scope=scope)
    return write_annual_finance_report(out_dir="out", year=year, scope=scope, annual=annual)


def main() -> None:
    load_env()
    parser = argparse.ArgumentParser(description="Genera informes financieros automaticos")
    parser.add_argument("--mode", choices=["auto", "monthly", "annual"], default="auto")
    parser.add_argument("--month", default=None, help="YYYY-MM para mensual")
    parser.add_argument("--year", type=int, default=None, help="YYYY para anual")
    parser.add_argument("--scope", choices=["calendar", "from_start"], default="calendar")
    parser.add_argument("--apply-price", action="store_true")
    args = parser.parse_args()

    now = datetime.now(UTC)
    if args.mode == "monthly":
        files = run_monthly(apply_price=args.apply_price, month_ym=args.month)
        print({"monthly_report": files})
        return

    if args.mode == "annual":
        year = args.year or now.year
        files = run_annual(year=year, scope=args.scope)
        print({"annual_report": files})
        return

    if _is_last_day(now):
        month_files = run_monthly(apply_price=args.apply_price, month_ym=now.strftime("%Y-%m"))
        out = {"monthly_report": month_files}
        if now.month == 12:
            out["annual_calendar"] = run_annual(year=now.year, scope="calendar")
            out["annual_from_start"] = run_annual(year=now.year, scope="from_start")
        print(out)
    else:
        print({"status": "skipped", "reason": "today_is_not_last_day_of_month"})


if __name__ == "__main__":
    main()
