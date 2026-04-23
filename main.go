// Copyright (c) 2026 Allen Gooch. All rights reserved.
// Use of this source code is governed by the MIT License
// that can be found in the LICENSE file.

package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	git "github.com/go-git/go-git/v5"
	cli "github.com/urfave/cli/v3"
)

// AppName is the app name of the executable
const AppName = "repos"

// App Version is the app version passed in at build time with linker flags.
var AppVersion string

// DefaultReposRoot is the directory in which repositories are cloned if not
// provided by environment variable or command option.
const DefaultReposRoot = "$HOME/devel/repos" // my tool, my rules!

// ReposRootEnvVar repositories are cloned in a 'forge/user/repo' hierarchy
// under a root directory which may be configured by environment variable.
const ReposRootEnvVar = "REPOS_ROOT"

// getDefaultReposRoot returns the default repo root to use.
func getDefaultReposRoot() string {
	// Use default repos root if not provided in environment variable
	reposRoot := os.Getenv(ReposRootEnvVar)
	if reposRoot == "" {
		reposRoot = DefaultReposRoot
	}
	// Expand user home directory and any other environment variables.
	if strings.HasPrefix(reposRoot, "~/") {
		reposRoot = strings.Replace(reposRoot, "~/", "$HOME/", -1)
	}
	return os.ExpandEnv(reposRoot)
}

// main constructs and runs the application.
func main() {
	// Define app global flags, subcommands and their args and flags.
	app := &cli.Command{
		Name:  "repos",
		Usage: "Manage git repos structured under a root directory",
		Flags: []cli.Flag{
			&cli.StringFlag{
				Name:    "root",
				Usage:   "root directory of your repos",
				Aliases: []string{"r"},
				Value:   getDefaultReposRoot(),
			},
		},
		Commands: []*cli.Command{
			{
				Name:  "version",
				Usage: "Shows app version",
				Action: func(ctx context.Context, cmd *cli.Command) error {
					fmt.Printf("%s-%s", AppName, AppVersion)
					return nil
				},
			},
			{
				Name:  "add",
				Usage: "Adds a new repo",
				Arguments: []cli.Argument{
					&cli.StringArg{
						Name: "URL",
					},
				},
				Flags: []cli.Flag{
					&cli.BoolFlag{
						Name:  "dry-run",
						Usage: "dry run",
						Value: false,
					},
					&cli.IntFlag{
						Name:    "depth",
						Aliases: []string{"d"},
						Usage:   "git clone depth",
						Value:   0,
					},
				},
				Action: func(ctx context.Context, cmd *cli.Command) error {
					// Get our repo descriptor from url arg
					repoURL := cmd.Args().First()
					repoDesc, err := parseURL(repoURL)
					if err != nil {
						return err
					}
					// Ensure that the repo parent directory exists
					reposRoot := cmd.String("root")
					repoPath := repoDesc.Path(reposRoot)
					if err := os.MkdirAll(filepath.Dir(reposRoot), 0o755); err != nil {
						return err
					}
					// Build the git clone command line
					gitExe := "git"
					gitArgs := fmt.Sprintf("clone %s -C %s", repoURL, repoPath)
					depth := cmd.Int("depth")
					if depth == 0 {
						gitArgs = fmt.Sprintf("%s --depth=%d", gitArgs, depth)
					}
					// Print the command and exit if dry run configured
					if cmd.Bool("dry-run") {
						fmt.Printf("%s %s", gitExe, gitArgs)
						return nil
					}
					// Otherwise execute the git clone command in a subprocess
					goCmd := exec.Command(gitExe, gitArgs)
					goCmd.Stdout = os.Stdout
					goCmd.Stderr = os.Stderr
					return goCmd.Run()
				},
			},
			{
				Name:  "list",
				Usage: "Lists added repos",
				Arguments: []cli.Argument{
					&cli.StringArg{
						Name: "query",
						UsageText: `query

   The query argument is a slash-separated path containing 0–3 components:
   - ""                -> all repos
   - "forge"           -> all repos for forge (github.com, gitlab.com, etc.,)
   - "forge/user"      -> all repos for forge user or organization
   - "forge/user/repo" -> a named repo for forge user or organization`,
					},
				},
				Flags: []cli.Flag{
					&cli.BoolFlag{
						Name:    "status",
						Aliases: []string{"s"},
						Usage:   "include repo status (branch, dirty)",
						Value:   false,
					},
					&cli.BoolFlag{
						Name:  "json",
						Usage: "output json",
						Value: false,
					},
				},

				Action: func(ctx context.Context, cmd *cli.Command) error {
					// Get query path from the command arg
					query := cmd.Args().First()
					// Walk the repos root directory to find matching repos
					reposRoot := cmd.String("root")
					repoInfos, err := fetchRepoInfos(reposRoot, query)
					if err != nil {
						return err
					}
					// Enrich the repo info with git status if requested
					addStatus := cmd.Bool("status")
					if addStatus {
						for _, repoInfo := range repoInfos {
							populateStatus(reposRoot, &repoInfo)
						}
					}
					// Output the repo info in the requested format
					if !cmd.Bool("json") {
						return outputHuman(repoInfos)
					}
					return outputJSON(repoInfos)
				},
			},
		},
	}
	// Run the app.
	if err := app.Run(context.Background(), os.Args); err != nil {
		log.Fatal(err)
	}
}

// RepoDesc describes a repository's forge, owner, and name.
type RepoDesc struct {
	Forge string
	User  string
	Repo  string
}

// Path returns a repository's file path in repos root directory.
func (r *RepoDesc) Path(repoRoot string) string {
	return filepath.Join(repoRoot, r.Forge, r.User, r.Repo)
}

// parseURL parses a git clone URL (https or SCP-style SSH) into forge/user/repo components.
func parseURL(rawURL string) (RepoDesc, error) {
	if strings.HasPrefix(rawURL, "git@") {
		return parseSCP(rawURL)
	}
	return parseHTTPS(rawURL)
}

// parseHTTPS parses an HTTP(S) clone URL into a RepoDesc.
func parseHTTPS(rawURL string) (RepoDesc, error) {
	u, err := url.Parse(rawURL)
	if err != nil || u.Host == "" {
		return RepoDesc{}, fmt.Errorf("invalid URL %q: expected https://forge/user/repo", rawURL)
	}
	parts := strings.Split(strings.Trim(u.Path, "/"), "/")
	if len(parts) < 2 || parts[0] == "" || parts[1] == "" {
		return RepoDesc{}, fmt.Errorf("URL %q must contain forge, user, and repo path components", rawURL)
	}
	return RepoDesc{
		Forge: u.Host,
		User:  parts[0],
		Repo:  strings.TrimSuffix(parts[1], ".git"),
	}, nil
}

// parseSCP parses an SCP-style SSH clone URL into a RepoDesc.
func parseSCP(rawURL string) (RepoDesc, error) {
	// git@github.com:user/repo.git
	s := strings.TrimPrefix(rawURL, "git@")
	idx := strings.Index(s, ":")
	if idx < 0 {
		return RepoDesc{}, fmt.Errorf("invalid SCP URL %q: expected git@host:user/repo", rawURL)
	}
	forge := s[:idx]
	parts := strings.SplitN(s[idx+1:], "/", 2)
	if len(parts) < 2 || parts[0] == "" || parts[1] == "" {
		return RepoDesc{}, fmt.Errorf("invalid SCP URL %q: expected git@host:user/repo", rawURL)
	}
	return RepoDesc{
		Forge: forge,
		User:  parts[0],
		Repo:  strings.TrimSuffix(parts[1], ".git"),
	}, nil
}

// RepoInfo holds information about an added repository.
type RepoInfo struct {
	Path   string `json:"path"`
	Branch string `json:"branch,omitempty"`
	Dirty  bool   `json:"dirty,omitempty"`
}

// fetchRepoInfos returns info for git repos under root matching a query path.
func fetchRepoInfos(reposRoot, queryPath string) ([]RepoInfo, error) {
	var fp [3]string
	if queryPath != "" {
		parts := strings.SplitN(queryPath, "/", 3)
		copy(fp[:], parts)
	}

	forges, err := subdirs(reposRoot)
	if err != nil {
		return nil, fmt.Errorf("cannot read repo root %s: %w", reposRoot, err)
	}

	var repos []RepoInfo
	for _, forge := range forges {
		if fp[0] != "" && forge != fp[0] {
			continue
		}
		users, _ := subdirs(filepath.Join(reposRoot, forge))
		for _, user := range users {
			if fp[1] != "" && user != fp[1] {
				continue
			}
			names, _ := subdirs(filepath.Join(reposRoot, forge, user))
			for _, name := range names {
				if fp[2] != "" && name != fp[2] {
					continue
				}
				repos = append(repos, RepoInfo{Path: filepath.Join(reposRoot, forge, user, name)})
			}
		}
	}
	return repos, nil
}

// subdirs returns the names of direct child directories in dir.
func subdirs(dir string) ([]string, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}
	var names []string
	for _, e := range entries {
		if e.IsDir() {
			names = append(names, e.Name())
		}
	}
	return names, nil
}

// populateStatus fills branch and dirty metadata for an added git repository.
func populateStatus(reposRoot string, info *RepoInfo) {
	r, err := git.PlainOpen(filepath.Join(reposRoot, info.Path))
	if err != nil {
		return
	}
	if head, err := r.Head(); err == nil {
		info.Branch = head.Name().Short()
	}
	if wt, err := r.Worktree(); err == nil {
		if st, err := wt.Status(); err == nil {
			info.Dirty = !st.IsClean()
		}
	}
}

// outputHuman writes repositories to stdout in a human-friendly format.
func outputHuman(repoInfos []RepoInfo) error {
	for _, repoInfo := range repoInfos {
		fmt.Println(repoInfo.Path)
	}
	return nil
}

// outputJSON writes repositories to stdout as formatted JSON.
func outputJSON(repoInfos []RepoInfo) error {
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	return enc.Encode(repoInfos)
}
