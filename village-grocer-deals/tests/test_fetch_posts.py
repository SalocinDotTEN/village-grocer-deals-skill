"""Offline tests for scripts/fetch_posts.py. Run: python3 -m unittest discover tests"""
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "fetch_posts.py"


def iso(days_ago: float) -> str:
    t = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return t.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def run(*args):
    p = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.state = self.tmp / "seen.json"
        pages = [
            {"posts": [
                {"id": "1", "url": "https://fb/p1", "text": "B1F1 bread", "creation_time": iso(0.2),
                 "image": "https://img/1a", "images": ["https://img/1a", "https://img/1b"]},
                {"id": "2", "url": "https://fb/p2", "text": "Video promo", "publishTime": int((datetime.now(timezone.utc) - timedelta(days=1)).timestamp()),
                 "videoDetails": {"thumbnailUrl": "https://img/2t"}},
                {"id": "3", "url": "https://fb/p3", "text": "Grouper RM55.99", "creation_time": iso(2)},
            ], "cursor": "c1"},
            {"posts": [
                {"id": "4", "url": "https://fb/p4", "text": "Old post", "creation_time": iso(10)},
            ], "cursor": "c2"},
        ]
        self.fixture = self.tmp / "pages.json"
        self.fixture.write_text(json.dumps(pages))

    def fetch(self, *extra):
        code, out, err = run("fetch", "--fixture", str(self.fixture), "--state", str(self.state), *extra)
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def test_new_posts_window_and_images(self):
        r = self.fetch()
        self.assertEqual([p["id"] for p in r["new_posts"]], ["1", "2", "3"])
        self.assertEqual(r["new_posts"][0]["images"], ["https://img/1a", "https://img/1b"])
        self.assertEqual(r["new_posts"][1]["images"], ["https://img/2t"])
        self.assertEqual(r["pages_read"], 2)

    def test_mark_seen_then_refetch_skips(self):
        code, _, err = run("mark-seen", "1", "2", "--state", str(self.state))
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(self.state.read_text()), ["1", "2"])
        r = self.fetch()
        self.assertEqual([p["id"] for p in r["new_posts"]], ["3"])
        r_all = self.fetch("--all")
        self.assertEqual(len(r_all["new_posts"]), 3)

    def test_missing_key_fails_loudly(self):
        code, _, err = run("fetch", "--state", str(self.state))
        # Only meaningful when no key is set in the test environment.
        import os
        if not os.environ.get("SCRAPECREATORS_API_KEY"):
            self.assertEqual(code, 2)
            self.assertIn("SCRAPECREATORS_API_KEY", err)

    def test_empty_first_page_is_error(self):
        self.fixture.write_text(json.dumps([{"posts": [], "cursor": None}]))
        code, _, err = run("fetch", "--fixture", str(self.fixture), "--state", str(self.state))
        self.assertEqual(code, 2)
        self.assertIn("no posts", err)


    def test_save_images_downloads_local_copies(self):
        img = self.tmp / "src.jpg"
        img.write_bytes(b"\xff\xd8fake-jpeg")
        pages = [{"posts": [
            {"id": "9", "url": "https://fb/p9", "creation_time": iso(0.1),
             "text": "Bumper Sale! Offers valid from 13 - 16 November",  # stale caption
             "images": [str(img), str(self.tmp / "missing.jpg")]},
        ], "cursor": None}]
        self.fixture.write_text(json.dumps(pages))
        out_dir = self.tmp / "imgs"
        r = self.fetch("--save-images", str(out_dir))
        post = r["new_posts"][0]
        self.assertEqual(post["image_files"], [str(out_dir / "9_0.jpg")])
        self.assertEqual((out_dir / "9_0.jpg").read_bytes(), b"\xff\xd8fake-jpeg")
        self.assertEqual(r["image_download_failures"], 1)
        self.assertEqual(len(post["image_errors"]), 1)

    def test_no_image_fields_without_flag(self):
        r = self.fetch()
        self.assertNotIn("image_files", r["new_posts"][0])
        self.assertNotIn("image_download_failures", r)


if __name__ == "__main__":
    unittest.main()
