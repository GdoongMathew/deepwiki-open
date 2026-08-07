"""Repository provider-type detection (backend authority).

Mirrors the frontend pure resolver in ``src/utils/repoType.ts``. Self-hosted
(on-prem) host overrides come from SERVER-ONLY env vars and are read at call
time (so changes need no restart), never shipped to the browser:

    ONPREM_GITHUB_HOSTS=github.company.com
    ONPREM_GITLAB_HOSTS=git.company.com,gitlab.corp.net
    ONPREM_BITBUCKET_HOSTS=stash.company.com
"""

import os
import re
from urllib.parse import urlparse

_SPLIT = re.compile(r"[\s,]+")


def parse_hosts(value: str | None) -> list[str]:
    """Parse a comma / whitespace separated host list from an env var."""
    return [h.strip().lower() for h in _SPLIT.split(value or "") if h.strip()]


def _to_hostname(value: str) -> str:
    """Reduce a bare host, ``proto://host:port``, or a full URL to a lowercase
    hostname (no scheme / userinfo / port / path)."""
    v = value.strip().lower()
    if not v:
        return ""
    if "://" not in v:
        v = "//" + v  # let urlparse treat it as a network location
    return urlparse(v).hostname or ""


def _matches(host: str, configured: str) -> bool:
    return host == configured or host.endswith(f".{configured}")


def resolve_repo_type(
    url: str | None,
    *,
    github_hosts: list[str] | None = None,
    gitlab_hosts: list[str] | None = None,
    bitbucket_hosts: list[str] | None = None,
) -> str:
    """Resolve a repo URL/host to a provider type.

    Configured on-prem host lists win over the built-in public-host heuristics;
    unknown hosts fall back to ``"web"``.
    """
    host = _to_hostname(url or "")
    if not host:
        return "web"

    if any(_matches(host, h) for h in (github_hosts or [])):
        return "github"
    if any(_matches(host, h) for h in (gitlab_hosts or [])):
        return "gitlab"
    if any(_matches(host, h) for h in (bitbucket_hosts or [])):
        return "bitbucket"

    if host == "github.com" or "github" in host:
        return "github"
    if host == "gitlab.com" or "gitlab" in host:
        return "gitlab"
    if host == "bitbucket.org" or "bitbucket" in host:
        return "bitbucket"
    return "web"


def resolve_repo_type_from_env(url: str | None) -> str:
    """Resolve using the ONPREM_* host lists from the current environment.

    Read at call time so updating the env needs no rebuild — only a restart when
    the process caches its environment (Docker/local both see it via os.environ).
    """
    return resolve_repo_type(
        url,
        github_hosts=parse_hosts(os.environ.get("ONPREM_GITHUB_HOSTS")),
        gitlab_hosts=parse_hosts(os.environ.get("ONPREM_GITLAB_HOSTS")),
        bitbucket_hosts=parse_hosts(os.environ.get("ONPREM_BITBUCKET_HOSTS")),
    )
