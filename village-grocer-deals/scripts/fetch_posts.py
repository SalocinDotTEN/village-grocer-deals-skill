#!/usr/bin/env python3
"""Fetch new Village Grocer Facebook posts through the ScrapeCreators API.

Subcommands:
  fetch       Print new (not yet reported) posts from the last few days as JSON.
  mark-seen   Record post ids as reported so they are skipped next time.

Standard library only. Needs SCRAPECREATORS_API_KEY in the environment
(not needed for --fixture runs).

--save-images DIR downloads each post's images into DIR and lists the local
paths per post as "image_files", so the assistant can look at them with its own
vision. No OCR or other image service is used. Village Grocer often reuses last
week's caption, so the dates on the image are the ones to trust.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API_URL = "https://api.scrapecreators.com/v1/facebook/profile/posts"
DEFAULT_PAGE = "https://www.facebook.com/myvillagegrocer/"
DEFAULT_STATE = Path.home() / ".village-grocer-deals" / "seen.json"
MAX_SEEN = 1000


class FetchError(RuntimeError):
    pass


def load_seen(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise FetchError(f"state file {path} is not valid JSON: {e}") from e
    if not isinstance(data, list):
        raise FetchError(f"state file {path} should hold a JSON list of post ids")
    return {str(x) for x in data}


def save_seen(path: Path, ids: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep the newest ids at the end; trim the oldest.
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(ids[-MAX_SEEN:]))
    tmp.replace(path)


def api_page(page_url: str, cursor: str | None, api_key: str) -> dict:
    params = {"url": page_url}
    if cursor:
        params["cursor"] = cursor
    req = urllib.request.Request(
        f"{API_URL}?{urllib.parse.urlencode(params)}",
        headers={"x-api-key": api_key, "User-Agent": "village-grocer-deals-skill/1.1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        raise FetchError(f"ScrapeCreators returned HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise FetchError(f"could not reach ScrapeCreators: {e.reason}") from e
    data = json.loads(body)
    if data.get("success") is False:
        raise FetchError(f"ScrapeCreators reported failure: {body[:300]}")
    if not isinstance(data.get("posts"), list):
        raise FetchError(f"unexpected response, no 'posts' list: {body[:300]}")
    return data


def post_time(p: dict) -> datetime:
    if p.get("creation_time"):
        return datetime.fromisoformat(str(p["creation_time"]).replace("Z", "+00:00"))
    if p.get("publishTime"):
        return datetime.fromtimestamp(int(p["publishTime"]), tz=timezone.utc)
    raise FetchError(f"post {p.get('id')} has no timestamp")


def post_images(p: dict) -> list[str]:
    imgs = p.get("images") or ([p["image"]] if p.get("image") else [])
    if not imgs:
        thumb = (p.get("videoDetails") or {}).get("thumbnailUrl")
        imgs = [thumb] if thumb else []
    return [str(u) for u in imgs][:3]


def save_images(posts: list[dict], folder: Path) -> int:
    """Download each post's images into folder; fill post["image_files"]. Returns failures."""
    folder.mkdir(parents=True, exist_ok=True)
    failed = 0
    for post in posts:
        files, errors = [], []
        for i, url in enumerate(post["images"]):
            dest = folder / f"{post['id']}_{i}.jpg"
            try:
                if url.startswith(("http://", "https://")):
                    req = urllib.request.Request(url, headers={"User-Agent": "village-grocer-deals-skill/1.1"})
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        dest.write_bytes(resp.read())
                else:  # local path, used by tests
                    dest.write_bytes(Path(url).read_bytes())
                files.append(str(dest))
            except Exception as e:  # one broken image should not sink the run
                failed += 1
                errors.append(f"{url[:80]}: {e}")
        post["image_files"] = files
        if errors:
            post["image_errors"] = errors
    return failed


def cmd_fetch(args: argparse.Namespace) -> int:
    seen = set() if args.all else load_seen(Path(args.state).expanduser())
    since = datetime.now(timezone.utc) - timedelta(days=args.lookback_days)

    fixture_pages: list[dict] | None = None
    api_key = ""
    if args.fixture:
        fixture_pages = json.loads(Path(args.fixture).read_text())
    else:
        api_key = os.environ.get("SCRAPECREATORS_API_KEY", "").strip()
        if not api_key:
            raise FetchError("SCRAPECREATORS_API_KEY is not set")

    collected: list[dict] = []
    cursor = None
    pages = 0
    done = False
    while pages < args.max_pages and not done:
        if fixture_pages is not None:
            if pages >= len(fixture_pages):
                break
            data = fixture_pages[pages]
        else:
            data = api_page(args.page_url, cursor, api_key)
        pages += 1
        posts = data.get("posts") or []
        for p in posts:
            if post_time(p) < since:
                done = True
                continue
            collected.append(p)
        # A page made only of already-reported posts means older ones were covered before.
        if posts and seen and all(str(p.get("id")) in seen for p in posts):
            done = True
        cursor = data.get("cursor")
        if not cursor or not posts:
            break

    if pages == 1 and not collected and not done:
        raise FetchError("first page returned no posts; cannot confirm the page was read")

    new = [
        {
            "id": str(p["id"]),
            "url": p.get("url") or p.get("permalink"),
            "created": post_time(p).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "text": p.get("text") or "",
            "images": post_images(p),
        }
        for p in collected
        if str(p.get("id")) not in seen
    ]
    out = {
        "page_url": args.page_url,
        "pages_read": pages,
        "posts_in_window": len(collected),
        "new_posts": new,
    }
    if args.save_images:
        out["image_download_failures"] = save_images(new, Path(args.save_images).expanduser())
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_mark_seen(args: argparse.Namespace) -> int:
    path = Path(args.state).expanduser()
    current = [x for x in (json.loads(path.read_text()) if path.exists() else [])]
    for i in args.ids:
        if i not in current:
            current.append(i)
    save_seen(path, current)
    print(json.dumps({"marked": len(args.ids), "stored": min(len(current), MAX_SEEN), "state": str(path)}))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="print new posts as JSON")
    f.add_argument("--page-url", default=DEFAULT_PAGE)
    f.add_argument("--lookback-days", type=int, default=3)
    f.add_argument("--max-pages", type=int, default=5)
    f.add_argument("--state", default=str(DEFAULT_STATE))
    f.add_argument("--all", action="store_true", help="ignore the reported-posts list")
    f.add_argument("--save-images", metavar="DIR",
                   help="download post images into DIR so they can be viewed locally")
    f.add_argument("--fixture", help=argparse.SUPPRESS)  # JSON list of API pages, for tests
    f.set_defaults(func=cmd_fetch)

    m = sub.add_parser("mark-seen", help="record post ids as reported")
    m.add_argument("ids", nargs="+")
    m.add_argument("--state", default=str(DEFAULT_STATE))
    m.set_defaults(func=cmd_mark_seen)

    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except FetchError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
