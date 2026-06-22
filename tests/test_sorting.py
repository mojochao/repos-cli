import unittest

from repos_cli.models import RepoInfo
from repos_cli.sorting import SORT_COLUMNS, sort_repos


def make(name, branch="main", committed_at=1000, author="ada", remote="local", path="/p"):
    return RepoInfo(
        name=name, branch=branch, dirty=False, committed_at=committed_at,
        author=author, remote=remote, path=path,
    )


def names(repos):
    return [r.name for r in repos]


class SortReposTest(unittest.TestCase):
    def test_empty_columns_defaults_to_name_ascending(self):
        repos = [make("zeta"), make("alpha"), make("mike")]
        self.assertEqual(names(sort_repos(repos, [])), ["alpha", "mike", "zeta"])

    def test_name_is_case_insensitive(self):
        repos = [make("Zeta"), make("alpha")]
        self.assertEqual(names(sort_repos(repos, ["name"])), ["alpha", "Zeta"])

    def test_desc_reverses_order(self):
        repos = [make("alpha"), make("zeta"), make("mike")]
        self.assertEqual(names(sort_repos(repos, ["name"], desc=True)), ["zeta", "mike", "alpha"])

    def test_sort_by_author(self):
        repos = [make("a", author="Carol"), make("b", author="Alice"), make("c", author="Bob")]
        self.assertEqual(names(sort_repos(repos, ["author"])), ["b", "c", "a"])

    def test_multi_column_sort_branch_then_name(self):
        repos = [make("b", branch="main"), make("a", branch="main"), make("c", branch="dev")]
        self.assertEqual(names(sort_repos(repos, ["status", "name"])), ["c", "a", "b"])

    def test_sort_by_updated_newest_first(self):
        repos = [make("old", committed_at=1000), make("new", committed_at=2000), make("mid", committed_at=1500)]
        self.assertEqual(names(sort_repos(repos, ["updated"])), ["new", "mid", "old"])

    def test_desc_reverses_updated_to_oldest_first(self):
        repos = [make("old", committed_at=1000), make("new", committed_at=2000), make("mid", committed_at=1500)]
        self.assertEqual(names(sort_repos(repos, ["updated"], desc=True)), ["old", "mid", "new"])

    def test_missing_commit_sorts_last_by_updated(self):
        repos = [make("has", committed_at=1000), make("none", committed_at=None)]
        self.assertEqual(names(sort_repos(repos, ["updated"])), ["has", "none"])

    def test_unknown_column_raises_value_error(self):
        with self.assertRaises(ValueError):
            sort_repos([make("a")], ["bogus"])

    def test_sort_columns_exposes_valid_names(self):
        self.assertIn("name", SORT_COLUMNS)
        self.assertIn("author", SORT_COLUMNS)


if __name__ == "__main__":
    unittest.main()
