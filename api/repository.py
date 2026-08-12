import os
import subprocess
from functools import wraps
from collections.abc import Callable
from urllib.parse import quote, urlparse, urlunparse

from git import Repo as GitRepo, GIT_OK, GitCommandError

from api.logger import get_logger
from api.utils import deepwiki_root

logger = get_logger(__name__)


CLONE_REPO_ROOT = os.path.join(deepwiki_root(), "repo")


def _exception_cleanup(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (subprocess.CalledProcessError, GitCommandError) as e:
            err_msg: str | bytes = e.stderr
            if isinstance(err_msg, bytes):
                err_msg = err_msg.decode("utf-8")
            token = kwargs.get("access_token", None)
            if token:
                token_mask = "***TOKEN***"
                err_msg = err_msg.replace(token, token_mask)
                encoded_token = quote(token, safe="")
                err_msg = err_msg.replace(encoded_token, token_mask)
            raise ValueError(err_msg)

    return wrapper


def _embed_gitlab_token(
    remote_url: str,
    access_token: str,
) -> str:
    parsed = urlparse(remote_url)
    access_token = quote(access_token, safe="")

    return urlunparse(
        (
            parsed.scheme,
            f"oauth2:{access_token}@{parsed.netloc}",
            parsed.path,
            "",
            "",
            "",
        )
    )


def _embed_github_token(
    remote_url: str,
    access_token: str,
) -> str:
    parsed = urlparse(remote_url)
    return urlunparse(
        (
            parsed.scheme,
            f"{access_token}@{parsed.netloc}",
            parsed.path,
            "",
            "",
            "",
        )
    )


def _embed_bitbucket_token(
    remote_url: str,
    access_token: str,
) -> str:
    parsed = urlparse(remote_url)
    # Bitbucket has two token formats with different auth schemes:
    #   - HTTP access tokens (prefix "ATCTT") use x-bitbucket-api-token-auth
    #   - App passwords (deprecated, EOL June 2026) use x-token-auth
    # Detect by token prefix so existing app password users keep working.
    auth_scheme = (
        "x-bitbucket-api-token-auth"
        if access_token.startswith("ATCTT")
        else "x-token-auth"
    )
    access_token = quote(access_token, safe="")

    return urlunparse(
        (
            parsed.scheme,
            f"{auth_scheme}:{access_token}@{parsed.netloc}",
            parsed.path,
            "",
            "",
            "",
        )
    )


def _get_remote_url_func(repo_type: str) -> Callable[[str, str], str] | None:
    return {
        "github": _embed_github_token,
        "gitlab": _embed_gitlab_token,
        "bitbucket": _embed_bitbucket_token,
    }.get(repo_type, None)


@_exception_cleanup
def _clone_from_remote(
    remote_url: str,
    local_path: str,
    repo_type: str,
    *,
    access_token: str | None = None,
    **kwargs,
) -> GitRepo:
    if access_token:
        func = _get_remote_url_func(repo_type=repo_type)
        if not func:
            raise NotImplementedError(f"Unknown repo type: {repo_type}")
        remote_url = func(remote_url, access_token)
    return GitRepo.clone_from(url=remote_url, to_path=local_path, **kwargs)


@_exception_cleanup
def _pull_latest(
    repo: GitRepo,
    branch_name: str,
    repo_type: str,
    *,
    access_token: str | None = None,
    remote_url: str | None = None,
    origin: str = "origin",
) -> bool:
    """If a local clone's HEAD is different from origin/branch_name, pull the latest.

    Parameters
    ----------
    repo: GitRepo
        The repository to pull from.
    branch_name: str
        The branch to pull.
    access_token: str
    origin: str, default="origin"

    Returns
    -------
    bool
        True if the local clone was updated, False otherwise.
    """
    remote = repo.git.ls_remote(origin, branch_name)
    if not remote.strip():
        raise ValueError(f"Branch {branch_name} not found on remote origin")

    remote_sha = remote.split()[0]

    if repo.head.commit.hexsha == remote_sha:
        return False

    if access_token:
        if not remote_url:
            raise ValueError("No remote url provided.")
        new_url = _get_remote_url_func(repo_type=repo_type)(remote_url, access_token)
        repo.remote(origin).set_url(new_url)
    repo.remote("origin").pull(branch_name)
    return True


def _path_is_url(path: str) -> bool:
    """Check if the given path is a URL, or local path string.

    Parameters
    ----------
    path: str
        The path to be checked

    Returns
    -------
    bool. True if is a URL, False otherwise
    """
    try:
        result = urlparse(path)
        return result.scheme in {"http", "https", "ftp"} and bool(result.netloc)
    except Exception:
        return False


class Repo:
    def __init__(
        self,
        repo_url: str,
        repo_type: str | None,
        root_path: str = CLONE_REPO_ROOT,
        access_token: str | None = None,
    ):
        """

        Parameters
        ----------
        repo_url
        repo_type
        root_path
        access_token : str, optional
            The access token to use when cloning repository from a private git service.
        """
        self.repo_url = repo_url
        self.repo_type = repo_type

        os.makedirs(root_path, exist_ok=True)
        self.root_path = root_path
        self.access_token = access_token

    @property
    def name(self):
        return self._extract_repo_name(self.repo_url, repo_type=self.repo_type)

    @property
    def is_local(self) -> bool:
        return not _path_is_url(self.repo_url)

    @staticmethod
    def _extract_repo_name(repo_url: str, repo_type: str | None) -> str:
        if _path_is_url(repo_url):
            url_parts = repo_url.rstrip("/").split("/")
            if repo_type in ["github", "gitlab", "bitbucket"] and len(url_parts) >= 5:
                # GitHub URL format: https://github.com/owner/repo
                # GitLab URL format: https://gitlab.com/owner/repo or https://gitlab.com/group/subgroup/repo
                # Bitbucket URL format: https://bitbucket.org/owner/repo
                owner = url_parts[-2]
                repo = url_parts[-1].replace(".git", "")
                repo_name = f"{owner}_{repo}"
            else:
                repo_name = url_parts[-1].replace(".git", "")
        else:
            # This is a local repository
            repo_name = os.path.basename(repo_url)
        return repo_name

    def download(self, force: bool = False) -> None:
        if force or (not self.downloaded and not self.is_local):
            os.makedirs(self.save_path, exist_ok=True)

            if not GIT_OK:
                raise RuntimeError("Missing `git` in current environment")

            kwargs = {
                "remote_url": self.repo_url,
                "local_path": self.save_path,
                "access_token": self.access_token,
                "multi_options": ["--depth=1", "--single-branch"],
            }

            _clone_from_remote(repo_type=self.repo_type, **kwargs)
            logger.info("Repository %s cloned successfully", self.name)

    @property
    def save_path(self) -> str:
        if self.is_local:
            return self.repo_url
        return os.path.join(self.root_path, self.name)

    @property
    def downloaded(self) -> bool:
        return os.path.exists(self.save_path) and bool(os.listdir(self.save_path))

    def __repr__(self) -> str:
        return f"{self.repo_type}: {self.name}"

    def update(self) -> bool:
        """Fetch the latest version of the repository."""
        if self.is_local or not self.downloaded:
            return False

        if not GIT_OK:
            raise RuntimeError("Missing `git` in current environment")

        repo = GitRepo(path=self.save_path)
        if repo.is_dirty():
            logger.warning("Git tree is dirty, skipping updating repo %s", self.name)
            return False

        try:
            branch_name = repo.active_branch.name
        except (TypeError, ValueError):
            logger.exception("Failed to get active branch for %s", self.name)
            return False

        logger.info("Trying to pull latest version of %s", self.name)
        try:
            updated = _pull_latest(
                repo,
                branch_name,
                repo_type=self.repo_type,
                access_token=self.access_token,
                remote_url=self.repo_url,
            )
        except Exception:
            logger.exception("Failed to pull latest version of %s", self.name)
            return False

        info = (
            "Repository %s updated to latest."
            if updated
            else "Repository %s is already up to date."
        )
        logger.info(info, self.name)
        return True
