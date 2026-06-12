from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"
LANDING_HTML = STATIC_DIR / "landing.html"
GUIDES_HTML = STATIC_DIR / "guides.html"
POLICIES_HTML = STATIC_DIR / "policies.html"
ADS_TXT = STATIC_DIR / "ads.txt"
ROBOTS_TXT = STATIC_DIR / "robots.txt"

