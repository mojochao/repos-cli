import unittest

from repos_cli.forges import FORGES, filter_by_forge, forge_of
from repos_cli.models import RepoInfo


def make(name, remote):
    return RepoInfo(name=name, branch="main", dirty=False, committed_at=1, author="a", remote=remote, path="/p")


class ForgeOfTest(unittest.TestCase):
    def test_github(self):
        self.assertEqual(forge_of("github.com/acme/widgets"), "github")

    def test_gitlab(self):
        self.assertEqual(forge_of("gitlab.com/acme/widgets"), "gitlab")

    def test_bitbucket(self):
        self.assertEqual(forge_of("bitbucket.org/acme/widgets"), "bitbucket")

    def test_codeberg(self):
        self.assertEqual(forge_of("codeberg.org/acme/widgets"), "codeberg")

    def test_azure_devops_dev_azure_host(self):
        self.assertEqual(forge_of("dev.azure.com/org/proj/_git/repo"), "ado")

    def test_azure_devops_visualstudio_host(self):
        self.assertEqual(forge_of("myorg.visualstudio.com/proj/_git/repo"), "ado")

    def test_enterprise_host_matches_by_name(self):
        self.assertEqual(forge_of("github.acme.com/team/repo"), "github")

    def test_is_case_insensitive(self):
        self.assertEqual(forge_of("GitHub.com/acme/widgets"), "github")

    def test_local_returns_local(self):
        self.assertEqual(forge_of("local"), "local")

    def test_unknown_host_is_none(self):
        self.assertIsNone(forge_of("example.com/acme/widgets"))


class FilterByForgeTest(unittest.TestCase):
    def test_no_forges_returns_all(self):
        repos = [make("a", "github.com/x/y"), make("b", "local")]
        self.assertEqual(len(filter_by_forge(repos, [])), 2)

    def test_filters_to_single_forge(self):
        repos = [make("gh", "github.com/x/y"), make("gl", "gitlab.com/x/y"), make("loc", "local")]
        self.assertEqual([r.name for r in filter_by_forge(repos, ["github"])], ["gh"])

    def test_union_of_multiple_forges(self):
        repos = [make("gh", "github.com/x/y"), make("gl", "gitlab.com/x/y"), make("bb", "bitbucket.org/x/y")]
        self.assertEqual({r.name for r in filter_by_forge(repos, ["github", "gitlab"])}, {"gh", "gl"})

    def test_excludes_local_and_unknown(self):
        repos = [make("gh", "github.com/x/y"), make("loc", "local"), make("unk", "example.com/x/y")]
        self.assertEqual([r.name for r in filter_by_forge(repos, ["github"])], ["gh"])

    def test_filter_local_shows_only_local(self):
        repos = [make("gh", "github.com/x/y"), make("loc", "local"), make("loc2", "local")]
        self.assertEqual({r.name for r in filter_by_forge(repos, ["local"])}, {"loc", "loc2"})

    def test_forge_names_are_case_insensitive(self):
        repos = [make("gh", "github.com/x/y")]
        self.assertEqual(len(filter_by_forge(repos, ["GitHub"])), 1)


class ForgesConstantTest(unittest.TestCase):
    def test_includes_named_forges(self):
        for forge in ("github", "gitlab", "bitbucket", "ado", "codeberg", "local"):
            self.assertIn(forge, FORGES)


if __name__ == "__main__":
    unittest.main()
