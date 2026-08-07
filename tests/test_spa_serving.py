"""SPA 静态资源服务测试。"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from outlook_web import spa as spa_support


class TestSpaServing(unittest.TestCase):
    def test_spa_disabled_without_build(self):
        with mock.patch.dict(os.environ, {"SPA_ENABLED": "false"}, clear=False):
            self.assertFalse(spa_support.spa_enabled())

    def test_spa_enabled_when_dist_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dist = Path(tmpdir)
            (dist / "index.html").write_text("<html>spa</html>", encoding="utf-8")
            with mock.patch.object(spa_support, "spa_dist_dir", return_value=dist):
                with mock.patch.dict(os.environ, {"SPA_ENABLED": ""}, clear=False):
                    self.assertTrue(spa_support.spa_enabled())

    def test_send_spa_index_and_asset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dist = Path(tmpdir)
            (dist / "index.html").write_text("<html>spa</html>", encoding="utf-8")
            (dist / "umi.js").write_text("console.log('ok')", encoding="utf-8")

            with mock.patch.object(spa_support, "spa_dist_dir", return_value=dist):
                from flask import Flask

                app = Flask(__name__)
                with app.test_request_context("/overview"):
                    index_resp = spa_support.send_spa_index()
                    self.assertEqual(index_resp.status_code, 200)
                    self.assertEqual(index_resp.mimetype, "text/html")

                    asset_resp = spa_support.send_spa_asset("umi.js")
                    self.assertEqual(asset_resp.status_code, 200)

                    fallback_resp = spa_support.send_spa_asset("overview")
                    self.assertEqual(fallback_resp.status_code, 200)
                    self.assertEqual(fallback_resp.mimetype, "text/html")


if __name__ == "__main__":
    unittest.main()
