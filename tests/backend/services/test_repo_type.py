from api.services.repo_type import parse_hosts, resolve_repo_type


# --------------------------------------------------------------------------- #
# parse_hosts
# --------------------------------------------------------------------------- #
def test_parse_hosts_splits_and_normalizes():
    assert parse_hosts("git.company.com, gitlab.corp.net") == [
        "git.company.com",
        "gitlab.corp.net",
    ]
    assert parse_hosts("  A.COM \n B.com ") == ["a.com", "b.com"]
    assert parse_hosts(None) == []
    assert parse_hosts("") == []


# --------------------------------------------------------------------------- #
# public-host heuristics (no on-prem config)
# --------------------------------------------------------------------------- #
def test_public_hosts():
    assert resolve_repo_type("https://github.com/o/r") == "github"
    assert resolve_repo_type("https://gitlab.com/g/s/r") == "gitlab"
    assert resolve_repo_type("https://bitbucket.org/o/r") == "bitbucket"
    # GitHub Enterprise style hostname (vendor name in host)
    assert resolve_repo_type("https://github.corp.io/o/r") == "github"


def test_unknown_host_is_web():
    assert resolve_repo_type("https://git.company.com/o/r") == "web"
    assert resolve_repo_type("") == "web"
    assert resolve_repo_type(None) == "web"


def test_hostname_normalization():
    # bare host, userinfo, port, and path variants all classify by host only
    assert resolve_repo_type("gitlab.com/g/r") == "gitlab"
    assert resolve_repo_type("git@github.com:o/r.git") == "github"
    assert resolve_repo_type("https://user:tok@bitbucket.org:443/o/r") == "bitbucket"


# --------------------------------------------------------------------------- #
# on-prem overrides win over the heuristic
# --------------------------------------------------------------------------- #
def test_onprem_overrides():
    hosts = {
        "gitlab_hosts": ["git.company.com"],
        "bitbucket_hosts": ["stash.company.com"],
        "github_hosts": ["ghe.company.com"],
    }
    assert resolve_repo_type("https://git.company.com/o/r", **hosts) == "gitlab"
    assert resolve_repo_type("https://stash.company.com/o/r", **hosts) == "bitbucket"
    assert resolve_repo_type("https://ghe.company.com/o/r", **hosts) == "github"
    # subdomains of a configured host also match
    assert resolve_repo_type("https://vcs.git.company.com/o/r", **hosts) == "gitlab"


def test_onprem_takes_precedence_over_vendor_substring():
    # host literally contains 'github' but is configured as an on-prem GitLab
    assert (
        resolve_repo_type(
            "https://github-mirror.corp.net/o/r",
            gitlab_hosts=["github-mirror.corp.net"],
        )
        == "gitlab"
    )
