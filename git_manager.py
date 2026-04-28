import os
import subprocess
from typing import List, Dict, Any, TypedDict, Optional


class GitStatus(TypedDict):
    is_repo: bool
    branch: Optional[str]
    is_dirty: bool
    staged_files: List[str]
    unstaged_files: List[str]
    untracked_files: List[str]
    error: Optional[str]


class GitManager:
    """
    A manager class to handle Git operations for a given directory using subprocess.
    """

    def __init__(self, directory_path: str):
        self.directory_path = os.path.abspath(directory_path)
        self._is_repo = False

    def _run_git(self, args: List[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git"] + args,
            cwd=self.directory_path,
            capture_output=True,
            text=True
        )

    def scan_directory(self) -> GitStatus:
        status: GitStatus = {
            "is_repo": False,
            "branch": None,
            "is_dirty": False,
            "staged_files": [],
            "unstaged_files": [],
            "untracked_files": [],
            "error": None
        }

        if not os.path.exists(self.directory_path):
            status["error"] = f"Directory does not exist: {self.directory_path}"
            return status

        check_repo = self._run_git(["rev-parse", "--is-inside-work-tree"])
        if check_repo.returncode != 0:
            status["is_repo"] = False
            return status

        status["is_repo"] = True
        self._is_repo = True

        try:
            branch_res = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])
            status["branch"] = branch_res.stdout.strip()

            status_res = self._run_git(["status", "--porcelain"])
            lines = status_res.stdout.splitlines()

            for line in lines:
                if len(line) < 2:
                    continue
                index_status = line[0]
                work_tree_status = line[1]
                file_path = line[2:].strip()

                if index_status == ' ' and work_tree_status == ' ':
                    continue

                if index_status in ['M', 'A', 'D', 'R', 'C']:
                    status["staged_files"].append(file_path)

                if work_tree_status in ['M', 'D']:
                    status["unstaged_files"].append(file_path)

                if index_status == '?':
                    status["untracked_files"].append(file_path)

            status["is_dirty"] = (
                len(status["staged_files"]) > 0 or
                len(status["unstaged_files"]) > 0 or
                len(status["untracked_files"]) > 0
            )

        except Exception as e:
            status["error"] = str(e)

        return status

    def initialize_repo(self) -> str:
        try:
            if not os.path.exists(self.directory_path):
                os.makedirs(self.directory_path)
            res = self._run_git(["init"])
            if res.returncode == 0:
                self._is_repo = True
                return "Repository initialized successfully."
            else:
                return f"Error initializing repository: {res.stderr}"
        except Exception as e:
            return f"Error initializing repository: {str(e)}"

    def add_all(self) -> str:
        if not self._is_repo:
            return "Error: Not a Git repository."
        res = self._run_git(["add", "."])
        return "All files added to staging." if res.returncode == 0 else f"Error adding files: {res.stderr}"

    def commit(self, message: str) -> str:
        if not self._is_repo:
            return "Error: Not a Git repository."
        if not message.strip():
            return "Error: Commit message cannot be empty."
        res = self._run_git(["commit", "-m", message])
        if res.returncode == 0:
            return f"Committed: {message}"
        else:
            error_msg = res.stderr if res.stderr.strip() else res.stdout
            return f"Error committing: {error_msg}"

    def pull(self) -> str:
        if not self._is_repo:
            return "Error: Not a Git repository."
        res = self._run_git(["pull"])
        return f"Pull successful:\n{res.stdout}" if res.returncode == 0 else f"Pull failed:\n{res.stderr}"

    def push(self) -> str:
        if not self._is_repo:
            return "Error: Not a Git repository."
        res = self._run_git(["push"])
        return f"Push successful:\n{res.stdout}" if res.returncode == 0 else f"Push failed:\n{res.stderr}"

    def push_set_upstream(self, branch: str) -> str:
        if not self._is_repo:
            return "Error: Not a Git repository."
        res = self._run_git(["push", "--set-upstream", "origin", branch])
        return f"Push successful:\n{res.stdout}" if res.returncode == 0 else f"Push failed:\n{res.stderr}"

    def add_file(self, file_path: str) -> str:
        if not self._is_repo:
            return "Error: Not a Git repository."
        res = self._run_git(["add", file_path])
        return f"Staged: {file_path}" if res.returncode == 0 else f"Error adding file: {res.stderr}"

    def unstage_file(self, file_path: str) -> str:
        if not self._is_repo:
            return "Error: Not a Git repository."
        res = self._run_git(["restore", "--staged", file_path])
        return f"Unstaged: {file_path}" if res.returncode == 0 else f"Error unstaging file: {res.stderr}"

    def discard_changes(self, file_path: str) -> str:
        if not self._is_repo:
            return "Error: Not a Git repository."
        res = self._run_git(["restore", file_path])
        return f"Discarded changes: {file_path}" if res.returncode == 0 else f"Error discarding: {res.stderr}"

    def get_history(self, n: int = 30) -> List[Dict[str, Any]]:
        if not self._is_repo:
            return []
        res = self._run_git(["log", f"-n", str(n), "--pretty=format:%h|%an|%ad|%s", "--date=short"])
        if res.returncode != 0:
            return []
        history = []
        for line in res.stdout.splitlines():
            parts = line.split('|', 3)
            if len(parts) == 4:
                history.append({
                    "hash": parts[0],
                    "author": parts[1],
                    "date": parts[2],
                    "subject": parts[3]
                })
        return history

    def get_diff(self, file_path: str = None, staged: bool = False) -> str:
        if not self._is_repo:
            return ""
        args = ["diff"]
        if staged:
            args.append("--cached")
        if file_path:
            args += ["--", file_path]
        res = self._run_git(args)
        return res.stdout if res.returncode == 0 else ""

    def get_branches(self) -> Dict[str, List[str]]:
        if not self._is_repo:
            return {"local": [], "remote": []}
        local_res = self._run_git(["branch"])
        remote_res = self._run_git(["branch", "-r"])
        local = [b.strip().lstrip("* ") for b in local_res.stdout.splitlines() if b.strip()]
        remote = [b.strip() for b in remote_res.stdout.splitlines() if b.strip() and "->" not in b]
        return {"local": local, "remote": remote}

    def checkout_branch(self, branch_name: str) -> str:
        if not self._is_repo:
            return "Error: Not a Git repository."
        res = self._run_git(["checkout", branch_name])
        return f"Switched to branch '{branch_name}'" if res.returncode == 0 else f"Error: {res.stderr}"

    def checkout_commit(self, commit_hash: str) -> str:
        if not self._is_repo:
            return "Error: Not a Git repository."
        res = self._run_git(["checkout", commit_hash])
        return f"Checked out: {commit_hash}" if res.returncode == 0 else f"Error: {res.stderr}"

    def create_branch(self, branch_name: str) -> str:
        if not self._is_repo:
            return "Error: Not a Git repository."
        if not branch_name.strip():
            return "Error: Branch name cannot be empty."
        res = self._run_git(["branch", branch_name])
        return f"Branch '{branch_name}' created." if res.returncode == 0 else f"Error: {res.stderr}"

    def create_and_checkout_branch(self, branch_name: str) -> str:
        if not self._is_repo:
            return "Error: Not a Git repository."
        if not branch_name.strip():
            return "Error: Branch name cannot be empty."
        res = self._run_git(["checkout", "-b", branch_name])
        return f"Created and switched to '{branch_name}'" if res.returncode == 0 else f"Error: {res.stderr}"

    def delete_branch(self, branch_name: str) -> str:
        if not self._is_repo:
            return "Error: Not a Git repository."
        res = self._run_git(["branch", "-d", branch_name])
        return f"Branch '{branch_name}' deleted." if res.returncode == 0 else f"Error: {res.stderr}"

    def merge_branch(self, branch_name: str) -> str:
        if not self._is_repo:
            return "Error: Not a Git repository."
        res = self._run_git(["merge", branch_name])
        return f"Merged '{branch_name}':\n{res.stdout}" if res.returncode == 0 else f"Merge failed:\n{res.stderr}"

    def stash(self, message: str = "") -> str:
        if not self._is_repo:
            return "Error: Not a Git repository."
        args = ["stash", "push"]
        if message:
            args += ["-m", message]
        res = self._run_git(args)
        return res.stdout.strip() if res.returncode == 0 else f"Stash failed: {res.stderr}"

    def stash_pop(self) -> str:
        if not self._is_repo:
            return "Error: Not a Git repository."
        res = self._run_git(["stash", "pop"])
        return res.stdout.strip() if res.returncode == 0 else f"Stash pop failed: {res.stderr}"

    def stash_list(self) -> List[Dict[str, str]]:
        if not self._is_repo:
            return []
        res = self._run_git(["stash", "list", "--pretty=format:%gd|%s"])
        entries = []
        for line in res.stdout.splitlines():
            parts = line.split("|", 1)
            if len(parts) == 2:
                entries.append({"ref": parts[0], "message": parts[1]})
        return entries

    def get_remotes(self) -> List[Dict[str, str]]:
        if not self._is_repo:
            return []
        res = self._run_git(["remote", "-v"])
        seen = set()
        remotes = []
        for line in res.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                url = parts[1]
                if name not in seen:
                    seen.add(name)
                    remotes.append({"name": name, "url": url})
        return remotes

    def add_remote(self, name: str, url: str) -> str:
        if not self._is_repo:
            return "Error: Not a Git repository."
        res = self._run_git(["remote", "add", name, url])
        return f"Remote '{name}' added." if res.returncode == 0 else f"Error: {res.stderr}"

    def fetch(self) -> str:
        if not self._is_repo:
            return "Error: Not a Git repository."
        res = self._run_git(["fetch", "--all"])
        return f"Fetch complete:\n{res.stdout}" if res.returncode == 0 else f"Fetch failed:\n{res.stderr}"

    def get_tags(self) -> List[str]:
        if not self._is_repo:
            return []
        res = self._run_git(["tag", "--sort=-creatordate"])
        return [t.strip() for t in res.stdout.splitlines() if t.strip()]

    def create_tag(self, tag_name: str, message: str = "") -> str:
        if not self._is_repo:
            return "Error: Not a Git repository."
        if message:
            res = self._run_git(["tag", "-a", tag_name, "-m", message])
        else:
            res = self._run_git(["tag", tag_name])
        return f"Tag '{tag_name}' created." if res.returncode == 0 else f"Error: {res.stderr}"

    def get_stats(self) -> Dict[str, Any]:
        """Return repo statistics."""
        if not self._is_repo:
            return {}
        stats = {}
        # Total commits
        count_res = self._run_git(["rev-list", "--count", "HEAD"])
        stats["total_commits"] = count_res.stdout.strip() if count_res.returncode == 0 else "0"
        # Contributors
        contrib_res = self._run_git(["shortlog", "-s", "-n", "HEAD"])
        contributors = []
        for line in contrib_res.stdout.splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                contributors.append({"count": parts[0], "name": parts[1]})
        stats["contributors"] = contributors[:5]
        # Remotes
        stats["remotes"] = self.get_remotes()
        return stats