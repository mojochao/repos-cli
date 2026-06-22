import unittest
from datetime import datetime

from repos_cli.models import RepoInfo
from repos_cli.render import render

ESC = "\x1b"
DAY = 86_400
NOW = 1_700_000_000


def make(name="repo", branch="main", dirty=False, committed_at=NOW, author="Ada", remote="git@example.com:acme/proj.git", path="/p/repo"):
    return RepoInfo(name=name, branch=branch, dirty=dirty, committed_at=committed_at, author=author, remote=remote, path=path)


def stamp(epoch):
    return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M")


class RenderTest(unittest.TestCase):
    def test_header_lists_columns_in_order(self):
        out = render([make()], now=NOW)
        self.assertLess(out.index("Name"), out.index("Status"))
        self.assertLess(out.index("Status"), out.index("Updated"))
        self.assertLess(out.index("Updated"), out.index("Author"))

    def test_updated_shows_days_since_last_commit(self):
        out = render([make(committed_at=NOW - 11 * DAY)], now=NOW)
        self.assertIn("11d", out)

    def test_updated_shows_zero_days_for_a_recent_commit(self):
        out = render([make(committed_at=NOW - 3600)], now=NOW)
        self.assertIn("0d", out)

    def test_updated_is_dash_when_no_commits(self):
        out = render([make(committed_at=None, author=None)], now=NOW)
        self.assertEqual(out.count("—"), 2)

    def test_clean_repo_has_no_dirty_marker(self):
        out = render([make(name="clean", dirty=False)], now=NOW)
        self.assertIn("main", out)
        self.assertNotIn("*", out)

    def test_dirty_repo_has_marker(self):
        out = render([make(name="messy", dirty=True)], now=NOW)
        self.assertIn("*", out)

    def test_time_column_hidden_by_default(self):
        out = render([make(committed_at=NOW)], now=NOW)
        self.assertNotIn("Time", out)
        self.assertNotIn(stamp(NOW), out)

    def test_time_column_shown_after_updated(self):
        out = render([make(committed_at=NOW)], show_time=True, now=NOW)
        self.assertIn("Time", out)
        self.assertIn(stamp(NOW), out)
        self.assertLess(out.index("Updated"), out.index("Time"))
        self.assertLess(out.index("Time"), out.index("Author"))

    def test_time_column_is_dash_when_no_commits(self):
        out = render([make(committed_at=None, author="Ada")], show_time=True, now=NOW)
        self.assertIn("Time", out)
        self.assertEqual(out.count("—"), 2)  # Updated and Time

    def test_remote_column_hidden_by_default(self):
        out = render([make(remote="git@example.com:acme/proj.git")], now=NOW)
        self.assertNotIn("Remote", out)
        self.assertNotIn("git@example.com:acme/proj.git", out)

    def test_remote_column_shows_remote_url(self):
        out = render([make(remote="git@example.com:acme/proj.git")], show_remote=True, now=NOW)
        self.assertIn("Remote", out)
        self.assertIn("git@example.com:acme/proj.git", out)

    def test_remote_column_shows_local_when_no_remote(self):
        out = render([make(remote="local")], show_remote=True, now=NOW)
        self.assertIn("local", out)

    def test_remote_column_comes_after_author(self):
        out = render([make()], show_remote=True, now=NOW)
        self.assertLess(out.index("Author"), out.index("Remote"))

    def test_remote_column_comes_before_path(self):
        out = render([make(remote="git@h:r.git", path="/p/x")], show_remote=True, show_path=True, now=NOW)
        self.assertLess(out.index("Remote"), out.index("Path"))

    def test_path_column_hidden_by_default(self):
        out = render([make(path="/home/u/code/repo")], now=NOW)
        self.assertNotIn("Path", out)
        self.assertNotIn("/home/u/code/repo", out)

    def test_path_column_shown_when_requested(self):
        out = render([make(path="/home/u/code/repo")], show_path=True, now=NOW)
        self.assertIn("Path", out)
        self.assertIn("/home/u/code/repo", out)

    def test_columns_aligned_across_rows(self):
        out = render([make(name="a"), make(name="bb")], now=NOW)
        data_lines = [ln for ln in out.splitlines() if "main" in ln]
        self.assertEqual(len(data_lines), 2)
        self.assertEqual(data_lines[0].index("main"), data_lines[1].index("main"))

    def test_no_color_output_has_no_ansi_escapes(self):
        out = render([make(dirty=True)], show_path=True, show_time=True, show_remote=True, use_color=False, now=NOW)
        self.assertNotIn(ESC, out)

    def test_color_output_has_ansi_escapes(self):
        out = render([make(dirty=True)], use_color=True, now=NOW)
        self.assertIn(ESC, out)


if __name__ == "__main__":
    unittest.main()
