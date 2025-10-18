import subprocess
import os
import re
import shutil

from airfold_apps.logger import create_logger
from github import Github, GithubException
from github.AuthenticatedUser import AuthenticatedUser
from typing import Dict, Any

logger = create_logger("git")


class CustomGitAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def run_git_command(self, command: list, cwd: str | None = None) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                command, cwd=cwd, capture_output=True, text=True, check=False
            )

            success = result.returncode == 0

            if success:
                logger.info(f"Command succeeded: {' '.join(command)}")
                if result.stdout:
                    logger.debug(f"stdout: {result.stdout.strip()}")
            else:
                logger.error(f"Command failed: {' '.join(command)}")
                logger.error(f"returncode: {result.returncode}")
                if result.stderr:
                    logger.error(f"stderr: {result.stderr.strip()}")

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "success": success,
                "command": " ".join(command),
            }
        except Exception as e:
            logger.error(f"Exception running command {' '.join(command)}: {e}")
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "success": False,
                "command": " ".join(command),
                "error": e,
            }

    def ensure_github_repo(self, repo_url: str) -> Dict[str, Any]:
        """
        Ensure a GitHub repository exists, creating it if necessary.

        Args:
            repo_url: GitHub repository URL (e.g., https://github.com/owner/repo.git or git@github.com:owner/repo.git)
            github_token: GitHub Personal Access Token (or uses GITHUB_TOKEN env var)

        Returns:
            Dict with 'success', 'exists', 'created', and 'message' keys
        """
        try:
            # Parse GitHub URL to extract owner and repo name
            # Supports both HTTPS and SSH formats
            match = re.search(r"github\.com[:/](.+?)/(.+?)(\.git)?$", repo_url)
            if not match:
                logger.warning(
                    f"Not a GitHub URL, skipping repository check: {repo_url}"
                )
                return {
                    "success": False,
                    "exists": None,
                    "created": False,
                    "message": "Not a GitHub URL",
                }

            owner, repo_name = match.groups()[:2]
            repo_name = repo_name.replace(".git", "")

            # Get GitHub token from parameter or environment
            if not self.api_key:
                logger.warning("No GitHub token provided, skipping repository check")
                return {
                    "success": False,
                    "exists": None,
                    "created": False,
                    "message": "No GitHub token available",
                }

            # Initialize GitHub API client
            g = Github(self.api_key)

            try:
                # Check if repository exists
                repo = g.get_repo(f"{owner}/{repo_name}")
                logger.info(f"[GitHub] Repository {owner}/{repo_name} exists")
                return {
                    "success": True,
                    "exists": True,
                    "created": False,
                    "message": f"Repository {owner}/{repo_name} exists",
                    "repo": repo,
                }

            except GithubException as e:
                if e.status == 404:
                    # Repository doesn't exist, create it
                    logger.info(f"[GitHub] Creating repository {owner}/{repo_name}...")

                    try:
                        user = g.get_user()
                        if isinstance(user, AuthenticatedUser):
                            new_repo = user.create_repo(
                                name=repo_name,
                                private=False,
                                auto_init=False,  # Don't auto-create README
                            )
                        else:
                            new_repo = user.get_repo(name=repo_name)
                        logger.info(
                            f"✓ [GitHub] Created repository {owner}/{repo_name}"
                        )
                        return {
                            "success": True,
                            "exists": True,
                            "created": True,
                            "message": f"Created repository {owner}/{repo_name}",
                            "repo": new_repo,
                        }

                    except GithubException as create_error:
                        logger.error(
                            f"[GitHub] Failed to create repository: {create_error}"
                        )
                        return {
                            "success": False,
                            "exists": False,
                            "created": False,
                            "message": f"Failed to create repository: {create_error}",
                        }
                else:
                    # Some other error
                    logger.error(f"[GitHub] Error checking repository: {e}")
                    return {
                        "success": False,
                        "exists": None,
                        "created": False,
                        "message": f"GitHub API error: {e}",
                    }

        except Exception as e:
            logger.error(f"[GitHub] Repository check failed: {e}")
            return {
                "success": False,
                "exists": None,
                "created": False,
                "message": f"Exception: {e}",
            }

    def clone(self, repo: str, destination: str = "tmp") -> Dict[str, Any]:
        """Clone a git repository."""
        logger.info(f"Cloning repository: {repo} to {destination}")
        command = ["git", "clone", repo, destination]
        result = self.run_git_command(command)

        # move env vars
        if result["success"]:
            src = "env_vars"
            if os.path.exists(src):
                shutil.copytree(
                    src, os.path.join(destination, "env_vars"), dirs_exist_ok=True
                )

        if result["success"]:
            logger.debug(f"✓ Successfully cloned {repo} to {destination}")
        else:
            logger.debug(f"✗ Failed to clone {repo}")
            logger.debug(f"  Error: {result['stderr']}")

        return result

    # def push(self, branch: str = "main", cwd: str = "tmp", force: bool = False) -> Dict[str, Any]:
    #     """Push changes to remote repository."""
    #     logger.info(f"Pushing to origin/{branch}")
    #     command = ["git", "push", "origin", branch]
    #     if force:
    #         command.insert(2, "--force")

    #     result = self.run_git_command(command, cwd=cwd)

    #     if result["success"]:
    #         logger.debug(f"✓ Successfully pushed to origin/{branch}")
    #     else:
    #         logger.debug(f"✗ Failed to push to origin/{branch}")
    #         logger.debug(f"  Error: {result['stderr']}")

    #     return result

    def status(self, cwd: str = "tmp") -> Dict[str, Any]:
        """Get git status."""
        logger.info("Getting git status")
        result = self.run_git_command(["git", "status"], cwd=cwd)

        if result["success"]:
            logger.debug("Git Status:")
            logger.debug(result["stdout"])
        else:
            logger.debug(f"✗ Failed to get status: {result['stderr']}")

        return result

    # def add(self, files: str = ".", cwd: str = "tmp") -> Dict[str, Any]:
    #     """Stage files for commit."""
    #     logger.info(f"Staging files: {files}")
    #     result = self.run_git_command(["git", "add", files], cwd=cwd)

    #     if result["success"]:
    #         logger.debug(f"✓ Staged files: {files}")
    #     else:
    #         logger.debug(f"✗ Failed to stage files: {result['stderr']}")

    #     return result

    # def commit(self, message: str, cwd: str = "tmp") -> Dict[str, Any]:
    #     """Commit staged changes."""
    #     logger.info(f"Committing with message: {message}")
    #     result = self.run_git_command(["git", "commit", "-m", message], cwd=cwd)

    #     if result["success"]:
    #         logger.debug(f"✓ Committed: {message}")
    #     else:
    #         logger.debug(f"✗ Failed to commit: {result['stderr']}")

    #     return result

    # def pull(self, branch: str = "main", cwd: str = "tmp") -> Dict[str, Any]:
    #     """Pull changes from remote."""
    #     logger.info(f"Pulling from origin/{branch}")
    #     result = self.run_git_command(["git", "pull", "origin", branch], cwd=cwd)

    #     if result["success"]:
    #         logger.debug(f"✓ Pulled from origin/{branch}")
    #     else:
    #         logger.debug(f"✗ Failed to pull: {result['stderr']}")

    #     return result

    # def graph(self, cwd: str = "tmp") -> Dict[str, Any]:
    #     """Get the graph of the repo."""
    #     logger.info("Getting git graph")
    #     result = self.run_git_command(["git", "log", "--graph", "--oneline", "--all"], cwd=cwd)

    #     if result["success"]:
    #         logger.info("Git Graph:")
    #         # Print each line to preserve graph formatting
    #         for line in result["stdout"].split("\n"):
    #             if line:  # Only log non-empty lines
    #                 logger.info(line)
    #     else:
    #         logger.error(f"✗ Failed to get graph: {result['stderr']}")

    #     return result


if __name__ == "__main__":
    logger.debug("=== Git Module Test ===\n")

    git = CustomGitAPI(os.getenv("GITHUB_TOKEN", ""))

    dir = "tmp"
    os.makedirs(dir, exist_ok=True)

    # Test clone
    repo = "git@github.com:shnkreddy98/claude-code-test.git"
    git.ensure_github_repo(repo)
    result = git.clone(repo, destination=dir)
    logger.debug(f"\nClone result: {result['success']}")

    # Test status
    logger.debug("\n" + "=" * 50)
    status_result = git.status(cwd=dir)

    # Test add, commit, push workflow
    logger.debug("\n" + "=" * 50)
    logger.debug("\nTesting add/commit/push workflow...")

    # Uncomment to test these operations:
    # add_result = add(".", cwd="tmp")
    # commit_result = commit("Test commit from git.py", cwd="tmp")
    # push_result = push("main", cwd="tmp")

    logger.debug("\n=== Test Complete ===")
