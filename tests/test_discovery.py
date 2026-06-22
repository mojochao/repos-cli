import os
import tempfile
import unittest

from repos_cli.discovery import find_repos


def mkrepo(*parts):
    """Create a directory tree and mark the leaf as a git repo."""
    path = os.path.join(*parts)
    os.makedirs(os.path.join(path, ".git"), exist_ok=True)
    return os.path.realpath(path)


def mkdir(*parts):
    path = os.path.join(*parts)
    os.makedirs(path, exist_ok=True)
    return os.path.realpath(path)


class DiscoveryTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def test_finds_repo_in_immediate_child(self):
        repo = mkrepo(self.root, "a")
        self.assertEqual(find_repos([self.root]), [repo])

    def test_finds_repo_nested_several_levels_deep(self):
        repo = mkrepo(self.root, "x", "y", "z")
        self.assertEqual(find_repos([self.root]), [repo])

    def test_finds_multiple_sibling_repos(self):
        a = mkrepo(self.root, "a")
        b = mkrepo(self.root, "b")
        self.assertEqual(set(find_repos([self.root])), {a, b})

    def test_does_not_descend_into_a_repo(self):
        outer = mkrepo(self.root, "outer")
        mkrepo(self.root, "outer", "inner")  # nested repo must be pruned
        self.assertEqual(find_repos([self.root]), [outer])

    def test_includes_root_when_root_is_a_repo(self):
        repo = mkrepo(self.root)
        self.assertEqual(find_repos([self.root]), [repo])

    def test_ignores_directories_without_git(self):
        mkdir(self.root, "plain", "nested")
        self.assertEqual(find_repos([self.root]), [])

    def test_dedupes_across_overlapping_roots(self):
        repo = mkrepo(self.root, "a")
        result = find_repos([self.root, os.path.join(self.root, "a")])
        self.assertEqual(result, [repo])

    def test_missing_path_is_skipped_without_error(self):
        self.assertEqual(find_repos([os.path.join(self.root, "nope")]), [])


if __name__ == "__main__":
    unittest.main()
