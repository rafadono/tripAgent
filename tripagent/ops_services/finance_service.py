from __future__ import annotations

from typing import Any

from tripagent.config import AppSettings
from tripagent.finance import annual_cashflow, cashflow_month, current_month_ym, feasibility_summary, reconcile_month
from tripagent.persistence import PERSISTENCE
from tripagent.reporting import write_annual_finance_report, write_monthly_finance_report


class OpsFinanceService:
    def cashflow(self, settings: AppSettings, month_ym: str | None = None) -> dict[str, Any]:
        month = month_ym or current_month_ym()
        return cashflow_month(settings, month)

    def upsert_infra_cost(self, month_ym: str | None, amount: float, notes: str | None = None) -> dict[str, Any]:
        month = month_ym or current_month_ym()
        PERSISTENCE.upsert_infra_cost(month_ym=month, amount=amount, notes=notes)
        return {"ok": True, "month_ym": month, "amount": float(amount), "notes": notes}

    def reconcile(self, settings: AppSettings, month_ym: str | None, apply_price: bool) -> dict[str, Any]:
        month = month_ym or current_month_ym()
        return reconcile_month(settings, month, apply_price=apply_price)

    def feasibility(self, settings: AppSettings) -> dict[str, Any]:
        return feasibility_summary(settings)

    def report_monthly(self, settings: AppSettings, month_ym: str | None, apply_price: bool) -> dict[str, Any]:
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
        return {
            "month_ym": month,
            "report_files": files,
            "reconcile": rec,
            "feasibility": feasibility,
        }

    def report_annual(self, settings: AppSettings, year: int | None, scope: str) -> dict[str, Any]:
        resolved_year = year or int(current_month_ym().split("-")[0])
        resolved_scope = "from_start" if scope == "from_start" else "calendar"
        annual = annual_cashflow(settings, year=resolved_year, scope=resolved_scope)
        files = write_annual_finance_report(out_dir="out", year=resolved_year, scope=resolved_scope, annual=annual)
        return {"year": resolved_year, "scope": resolved_scope, "report_files": files, "annual": annual}
