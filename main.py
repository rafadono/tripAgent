import argparse
from pathlib import Path

from tripagent.config import load_env
from tripagent.models import PlanRequest
from tripagent.service import plan


def _print_banner(host: str, port: int) -> None:
    display_host = "localhost" if host == "0.0.0.0" else host
    base = f"http://{display_host}:{port}"
    print("\n" + "─" * 52)
    print("  🗺️  TripAgent is running")
    print("─" * 52)
    print(f"  🌐  Visual Interface →  {base}/")
    print(f"  📄  Swagger / Docs   →  {base}/docs")
    print(f"  💚  Health check     →  {base}/health/ready")
    print(f"  📡  API              →  {base}/plan")
    print("─" * 52 + "\n")


def main():
    load_env()

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan", help="Run planner (CLI)")
    p_plan.add_argument("--infile", required=True)
    p_plan.add_argument("--outdir", default="out")

    p_serve = sub.add_parser("serve", help="Run API (uvicorn)")
    p_serve.add_argument("--host", default="0.0.0.0")
    p_serve.add_argument("--port", default=8000, type=int)
    p_serve.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    p_serve.add_argument("--workers", default=1, type=int, help="Number of Uvicorn worker processes")

    args = parser.parse_args()

    if args.cmd == "plan":
        req = PlanRequest.model_validate_json(Path(args.infile).read_text(encoding="utf-8"))
        resp = plan(req, out_dir=args.outdir)
        print(resp.model_dump_json(indent=2, ensure_ascii=False))
        return

    if args.cmd == "serve":
        import uvicorn
        _print_banner(args.host, args.port)
        workers = max(1, int(args.workers))
        uvicorn.run(
            "tripagent.api:app",
            host=args.host,
            port=args.port,
            reload=bool(args.reload),
            workers=1 if args.reload else workers,
        )
        return


if __name__ == "__main__":
    main()
