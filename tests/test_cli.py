import contextlib
import io
import os
import subprocess
import tempfile
import unittest

from repos_cli.cli import build_parser, main, should_use_color


def init_repo(path):
    os.makedirs(path, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True, text=True)
    return os.path.realpath(path)


def add_remote(path, url, name="origin"):
    subprocess.run(["git", "remote", "add", name, url], cwd=path, check=True, capture_output=True, text=True)


def commit(path, author):
    for cfg in (("user.email", "t@example.com"), ("user.name", author), ("commit.gpgsign", "false")):
        subprocess.run(["git", "config", *cfg], cwd=path, check=True, capture_output=True, text=True)
    with open(os.path.join(path, "f.txt"), "w") as fh:
        fh.write("x")
    subprocess.run(["git", "add", "f.txt"], cwd=path, check=True, capture_output=True, text=True)
    env = dict(os.environ, GIT_AUTHOR_DATE="2026-01-01T00:00:00", GIT_COMMITTER_DATE="2026-01-01T00:00:00")
    subprocess.run(["git", "commit", "-m", "x"], cwd=path, check=True, capture_output=True, text=True, env=env)


class ParserTest(unittest.TestCase):
    def test_requires_at_least_one_parent(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args([])

    def test_collects_multiple_parents(self):
        self.assertEqual(build_parser().parse_args(["a", "b"]).parents, ["a", "b"])

    def test_path_flag_defaults_off_and_turns_on(self):
        self.assertFalse(build_parser().parse_args(["a"]).path)
        self.assertTrue(build_parser().parse_args(["a", "--path"]).path)

    def test_no_color_flag_defaults_off_and_turns_on(self):
        self.assertFalse(build_parser().parse_args(["a"]).no_color)
        self.assertTrue(build_parser().parse_args(["a", "--no-color"]).no_color)

    def test_time_flag_defaults_off_and_turns_on(self):
        self.assertFalse(build_parser().parse_args(["a"]).time)
        self.assertTrue(build_parser().parse_args(["a", "--time"]).time)

    def test_remote_flag_defaults_off_and_turns_on(self):
        self.assertFalse(build_parser().parse_args(["a"]).remote)
        self.assertTrue(build_parser().parse_args(["a", "--remote"]).remote)

    def test_sort_defaults_to_none_and_accepts_value(self):
        self.assertIsNone(build_parser().parse_args(["a"]).sort)
        self.assertEqual(build_parser().parse_args(["a", "--sort", "author,name"]).sort, "author,name")

    def test_desc_flag_defaults_off_and_turns_on(self):
        self.assertFalse(build_parser().parse_args(["a"]).desc)
        self.assertTrue(build_parser().parse_args(["a", "--desc"]).desc)

    def test_forge_defaults_to_none_and_appends(self):
        self.assertIsNone(build_parser().parse_args(["a"]).forge)
        args = build_parser().parse_args(["a", "--forge", "github", "--forge", "gitlab"])
        self.assertEqual(args.forge, ["github", "gitlab"])


class ShouldUseColorTest(unittest.TestCase):
    def test_on_when_tty_and_allowed(self):
        self.assertTrue(should_use_color(no_color=False, isatty=True, env={}))

    def test_off_when_no_color_flag_set(self):
        self.assertFalse(should_use_color(no_color=True, isatty=True, env={}))

    def test_off_when_not_a_tty(self):
        self.assertFalse(should_use_color(no_color=False, isatty=False, env={}))

    def test_off_when_no_color_env_var_present(self):
        self.assertFalse(should_use_color(no_color=False, isatty=True, env={"NO_COLOR": "1"}))


class MainTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def test_lists_repos_sorted_by_name(self):
        init_repo(os.path.join(self.root, "zebra"))
        init_repo(os.path.join(self.root, "alpha"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main([self.root])
        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("alpha", text)
        self.assertIn("zebra", text)
        self.assertLess(text.index("alpha"), text.index("zebra"))

    def test_desc_reverses_default_name_order(self):
        init_repo(os.path.join(self.root, "alpha"))
        init_repo(os.path.join(self.root, "zebra"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main([self.root, "--desc"])
        text = out.getvalue()
        self.assertLess(text.index("zebra"), text.index("alpha"))

    def test_sorts_by_explicit_column(self):
        commit(init_repo(os.path.join(self.root, "zzz")), author="Alice")
        commit(init_repo(os.path.join(self.root, "aaa")), author="Zoe")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main([self.root, "--sort", "author"])
        text = out.getvalue()
        self.assertLess(text.index("zzz"), text.index("aaa"))  # Alice sorts before Zoe

    def test_invalid_sort_column_errors(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                main([self.root, "--sort", "bogus"])

    def test_forge_filters_to_requested(self):
        add_remote(init_repo(os.path.join(self.root, "ghrepo")), "git@github.com:acme/ghrepo.git")
        add_remote(init_repo(os.path.join(self.root, "glrepo")), "git@gitlab.com:acme/glrepo.git")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main([self.root, "--forge", "github"])
        text = out.getvalue()
        self.assertIn("ghrepo", text)
        self.assertNotIn("glrepo", text)

    def test_forge_local_shows_only_remoteless_repos(self):
        init_repo(os.path.join(self.root, "loner"))  # no remote
        add_remote(init_repo(os.path.join(self.root, "hosted")), "git@github.com:acme/hosted.git")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main([self.root, "--forge", "local"])
        text = out.getvalue()
        self.assertIn("loner", text)
        self.assertNotIn("hosted", text)

    def test_invalid_forge_errors(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                main([self.root, "--forge", "bogus"])

    def test_warns_and_exits_nonzero_for_missing_parent(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = main([os.path.join(self.root, "missing")])
        self.assertNotEqual(code, 0)
        self.assertIn("missing", err.getvalue())

    def test_reports_when_no_repos_found(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = main([self.root])
        self.assertEqual(code, 0)
        self.assertIn("No repositories found", err.getvalue())

    def test_path_flag_shows_full_path(self):
        repo = init_repo(os.path.join(self.root, "proj"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main([self.root, "--path"])
        self.assertIn(repo, out.getvalue())

    def test_time_flag_adds_time_column(self):
        init_repo(os.path.join(self.root, "proj"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main([self.root, "--time"])
        self.assertIn("Time", out.getvalue())

    def test_remote_flag_adds_remote_column(self):
        init_repo(os.path.join(self.root, "proj"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main([self.root, "--remote"])
        text = out.getvalue()
        self.assertIn("Remote", text)
        self.assertIn("local", text)

    def test_remote_column_absent_without_flag(self):
        init_repo(os.path.join(self.root, "proj"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main([self.root])
        self.assertNotIn("Remote", out.getvalue())


if __name__ == "__main__":
    unittest.main()
