from __future__ import annotations

from pathlib import Path
from typing import Any

from tripagent.jsonx import dumps_str


def write_monthly_finance_report(
    out_dir: str,
    *,
    month_ym: str,
    cashflow: dict[str, Any],
    recommendation: dict[str, Any] | None,
    feasibility: dict[str, Any],
    applied_price_change: bool,
) -> dict[str, str]:
    base = Path(out_dir) / "reports"
    base.mkdir(parents=True, exist_ok=True)
    md_path = base / f"finance_report_{month_ym}.md"
    json_path = base / f"finance_report_{month_ym}.json"

    lines = []
    lines.append(f"# Monthly Financial Report - {month_ym}")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Revenue: {cashflow.get('revenue_total', 0):.2f} CLP")
    lines.append(f"- Expenses: {cashflow.get('cost_total', 0):.2f} CLP")
    lines.append(f"- Margin: {cashflow.get('margin', 0):.2f} CLP")
    lines.append(f"- Recommended subscription price: {((recommendation or {}).get('recommended_price', 0)):.2f} CLP")
    lines.append(f"- Price adjustment applied: {'yes' if applied_price_change else 'no'}")
    lines.append("")
    lines.append("## Feasibility")
    lines.append(f"- Project sustainable now: {'yes' if feasibility.get('sustainable_now') else 'no'}")
    lines.append(f"- Current free->pro conversion: {float(feasibility.get('current_conversion_rate', 0))*100:.2f}%")
    lines.append(f"- Target conversion: {float(feasibility.get('target_conversion_rate', 0))*100:.2f}%")
    lines.append(f"- Price within affordability threshold: {'yes' if feasibility.get('affordability_flag') else 'no'}")
    lines.append("")
    lines.append("## Cash Flow Detail")
    for row in cashflow.get("lines", []):
        lines.append(
            f"- [{row.get('entry_type')}] {row.get('category')}: {float(row.get('amount', 0)):.2f} CLP"
        )

    md_path.write_text("\n".join(lines), encoding="utf-8")
    json_path.write_text(
        dumps_str(
            {
                "month_ym": month_ym,
                "cashflow": cashflow,
                "recommendation": recommendation,
                "feasibility": feasibility,
                "applied_price_change": applied_price_change,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return {"markdown_path": str(md_path), "json_path": str(json_path)}


def write_annual_finance_report(
    out_dir: str,
    *,
    year: int,
    scope: str,
    annual: dict[str, Any],
) -> dict[str, str]:
    base = Path(out_dir) / "reports"
    base.mkdir(parents=True, exist_ok=True)
    suffix = "from_start" if scope == "from_start" else "calendar"
    md_path = base / f"finance_report_{year}_{suffix}.md"
    json_path = base / f"finance_report_{year}_{suffix}.json"

    totals = annual.get("totals", {})
    lines = []
    lines.append(f"# Annual Financial Report - {year} ({suffix})")
    lines.append("")
    lines.append("## Totals")
    lines.append(f"- Revenue: {float(totals.get('revenue_total', 0)):.2f} CLP")
    lines.append(f"- Expenses: {float(totals.get('cost_total', 0)):.2f} CLP")
    lines.append(f"- Margin: {float(totals.get('margin', 0)):.2f} CLP")
    lines.append(f"- Margin %: {float(totals.get('margin_rate', 0))*100:.2f}%")
    lines.append("")
    lines.append("## Monthly Evolution")
    for row in annual.get("months", []):
        lines.append(
            f"- {row.get('month_ym')}: revenue {float(row.get('revenue_total', 0)):.2f}, "
            f"expenses {float(row.get('cost_total', 0)):.2f}, margin {float(row.get('margin', 0)):.2f} CLP"
        )

    md_path.write_text("\n".join(lines), encoding="utf-8")
    json_path.write_text(dumps_str(annual, indent=2), encoding="utf-8")
    return {"markdown_path": str(md_path), "json_path": str(json_path)}
