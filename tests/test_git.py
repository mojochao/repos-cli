import os
import subprocess
import tempfile
import unittest
from datetime import datetime

from repos_cli.git import get_info, short_remote


def _run(args, cwd, env=None):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True, env=env)


def init_repo(path, *, branch="main"):
    os.makedirs(path, exist_ok=True)
    _run(["git", "init", "-b", branch], path)
    _run(["git", "config", "user.email", "test@example.com"], path)
    _run(["git", "config", "user.name", "Test Author"], path)
    _run(["git", "config", "commit.gpgsign", "false"], path)
    return path


def commit(path, name="file.txt", content="hello", *, message="init", date="2026-06-22T14:09:00"):
    with open(os.path.join(path, name), "w") as fh:
        fh.write(content)
    _run(["git", "add", name], path)
    env = dict(os.environ, GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    _run(["git", "commit", "-m", message], path, env=env)


class GitInfoTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def repo(self, name="proj"):
        return init_repo(os.path.join(self._tmp.name, name))

    def test_name_is_the_repo_basedir(self):
        path = self.repo("myproj")
        self.assertEqual(get_info(path).name, "myproj")

    def test_reports_current_branch(self):
        path = self.repo()
        commit(path)
        self.assertEqual(get_info(path).branch, "main")

    def test_clean_repo_is_not_dirty(self):
        path = self.repo()
        commit(path)
        self.assertFalse(get_info(path).dirty)

    def test_modified_tracked_file_is_dirty(self):
        path = self.repo()
        commit(path)
        with open(os.path.join(path, "file.txt"), "w") as fh:
            fh.write("changed")
        self.assertTrue(get_info(path).dirty)

    def test_untracked_file_alone_is_not_dirty(self):
        path = self.repo()
        commit(path)
        with open(os.path.join(path, "new.txt"), "w") as fh:
            fh.write("brand new")
        self.assertFalse(get_info(path).dirty)

    def test_staged_change_is_dirty(self):
        path = self.repo()
        commit(path)
        with open(os.path.join(path, "staged.txt"), "w") as fh:
            fh.write("x")
        _run(["git", "add", "staged.txt"], path)
        self.assertTrue(get_info(path).dirty)

    def test_last_commit_time_and_author(self):
        path = self.repo()
        commit(path, date="2026-06-22T14:09:00")
        info = get_info(path)
        self.assertIsNotNone(info.committed_at)
        stamp = datetime.fromtimestamp(info.committed_at).strftime("%Y-%m-%d %H:%M")
        self.assertEqual(stamp, "2026-06-22 14:09")
        self.assertEqual(info.author, "Test Author")

    def test_repo_without_commits_has_no_metadata(self):
        path = self.repo()
        info = get_info(path)
        self.assertIsNone(info.committed_at)
        self.assertIsNone(info.author)
        self.assertEqual(info.branch, "main")

    def test_remote_url_is_reported_in_short_form(self):
        path = self.repo()
        _run(["git", "remote", "add", "origin", "git@example.com:acme/proj.git"], path)
        self.assertEqual(get_info(path).remote, "example.com/acme/proj")

    def test_prefers_origin_when_multiple_remotes(self):
        path = self.repo()
        _run(["git", "remote", "add", "upstream", "git@example.com:upstream/proj.git"], path)
        _run(["git", "remote", "add", "origin", "git@example.com:me/proj.git"], path)
        self.assertEqual(get_info(path).remote, "example.com/me/proj")

    def test_repo_without_remote_is_local(self):
        path = self.repo()
        self.assertEqual(get_info(path).remote, "local")

    def test_detached_head_shows_short_sha(self):
        path = self.repo()
        commit(path)
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=path, capture_output=True, text=True, check=True,
        ).stdout.strip()
        _run(["git", "checkout", sha], path)
        self.assertEqual(get_info(path).branch, sha)


class ShortRemoteTest(unittest.TestCase):
    def test_scp_like_ssh(self):
        self.assertEqual(short_remote("git@github.com:mojochao/myde.emacs.git"), "github.com/mojochao/myde.emacs")

    def test_https(self):
        self.assertEqual(short_remote("https://github.com/mojochao/repo.git"), "github.com/mojochao/repo")

    def test_https_without_dot_git_suffix(self):
        self.assertEqual(short_remote("https://github.com/mojochao/repo"), "github.com/mojochao/repo")

    def test_ssh_url_with_port(self):
        self.assertEqual(short_remote("ssh://git@github.com:22/mojochao/repo.git"), "github.com/mojochao/repo")

    def test_https_with_embedded_credentials(self):
        self.assertEqual(short_remote("https://user:token@gitlab.com/group/sub/repo.git"), "gitlab.com/group/sub/repo")

    def test_git_protocol(self):
        self.assertEqual(short_remote("git://github.com/mojochao/repo.git"), "github.com/mojochao/repo")

    def test_local_sentinel_passes_through(self):
        self.assertEqual(short_remote("local"), "local")


if __name__ == "__main__":
    unittest.main()
