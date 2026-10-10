# scripts/stats.py
import json
import logging
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError

API_URL = "https://api.github.com"
REQUEST_TIMEOUT_SECONDS = 30
STATS_RETRY_ATTEMPTS = 6
STATS_RETRY_DELAY_SECONDS = 5
HTTP_ACCEPTED = 202
PAGE_SIZE = 100

logger = logging.getLogger(__name__)


class GitHubApiError(Exception):
    pass


@dataclass(frozen=True)
class Stats:
    repos: int
    contributed: int
    stars: int
    commits: int
    followers: int
    additions: int
    deletions: int


def request(token: str, path: str, payload: dict | None = None) -> tuple[int, object]:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"{API_URL}{path}",
        data=data,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            body = response.read()
            return response.status, json.loads(body) if body else None
    except (HTTPError, URLError) as error:
        raise GitHubApiError(f"GitHub request failed for {path}: {error}") from error


def graphql(token: str, query: str, variables: dict) -> dict:
    _, body = request(token, "/graphql", {"query": query, "variables": variables})
    if not isinstance(body, dict) or "errors" in body:
        raise GitHubApiError(f"GraphQL error: {body.get('errors') if isinstance(body, dict) else body}")
    return body["data"]


PROFILE_QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY]) { totalCount }
  }
}"""

REPOS_QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes { name stargazerCount }
    }
  }
}"""

COMMITS_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) { totalCommitContributions }
  }
}"""


def fetch_stats(token: str, login: str) -> Stats:
    profile = graphql(token, PROFILE_QUERY, {"login": login})["user"]
    repo_count, repos = fetch_repositories(token, login)
    additions, deletions = count_lines(token, login, [repo["name"] for repo in repos])
    return Stats(
        repos=repo_count,
        contributed=profile["repositoriesContributedTo"]["totalCount"],
        stars=sum(repo["stargazerCount"] for repo in repos),
        commits=count_commits(token, login, profile["createdAt"]),
        followers=profile["followers"]["totalCount"],
        additions=additions,
        deletions=deletions,
    )


def fetch_repositories(token: str, login: str) -> tuple[int, list[dict]]:
    repos: list[dict] = []
    cursor = None
    while True:
        page = graphql(token, REPOS_QUERY, {"login": login, "cursor": cursor})["user"]["repositories"]
        repos.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            return page["totalCount"], repos
        cursor = page["pageInfo"]["endCursor"]


def count_commits(token: str, login: str, created_at: str) -> int:
    start_year = datetime.fromisoformat(created_at.replace("Z", "+00:00")).year
    now = datetime.now(timezone.utc)
    total = 0
    for year in range(start_year, now.year + 1):
        window = {"login": login, "from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"}
        collection = graphql(token, COMMITS_QUERY, window)["user"]["contributionsCollection"]
        total += collection["totalCommitContributions"]
    return total


def count_lines(token: str, login: str, repo_names: list[str]) -> tuple[int, int]:
    additions = deletions = 0
    for name in repo_names:
        added, removed = repo_lines(token, login, name)
        additions += added
        deletions += removed
    return additions, deletions


def repo_lines(token: str, login: str, repo: str) -> tuple[int, int]:
    path = f"/repos/{login}/{repo}/stats/contributors"
    for _ in range(STATS_RETRY_ATTEMPTS):
        status, body = request(token, path)
        if status != HTTP_ACCEPTED:
            return sum_author_weeks(body, login)
        time.sleep(STATS_RETRY_DELAY_SECONDS)
    logger.warning("Contributor stats still computing for %s, skipped", repo)
    return 0, 0


def sum_author_weeks(contributors: object, login: str) -> tuple[int, int]:
    if not isinstance(contributors, list):
        return 0, 0
    for contributor in contributors:
        author = contributor.get("author") or {}
        if author.get("login", "").lower() == login.lower():
            weeks = contributor["weeks"]
            return sum(week["a"] for week in weeks), sum(week["d"] for week in weeks)
    return 0, 0
