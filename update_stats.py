import json, os, urllib.request, io
from pathlib import Path
from datetime import date
from html import escape

USER = "tyler-le"
TOKEN = os.environ.get("GH_TOKEN", "")
STATS_TOKENS = list(dict.fromkeys(t for t in (os.environ.get("STATS_TOKEN"), os.environ.get("STATS_TOKEN_2"), os.environ.get("STATS_TOKEN_3")) if t))
def get(url, auth=False, token=None):
    headers = {"User-Agent": "profile-readme-generator"}
    if auth and (token or TOKEN):
        headers["Authorization"] = "Bearer " + (token or TOKEN)
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return r.read()
profile = json.loads(get("https://api.github.com/users/" + USER, True))
# Approved cat avatar ASCII artwork; background excluded.
portrait = [
    "",
    "        &#MH",
    "       &G5553",
    "       G3hhh3h                        G3hB",
    "      S3MGHMMMh                     S3AsiH",
    "      3355hHMHhM                   Gh352Xh",
    "     G3525hhMHMMS                 Ghh33353",
    "     S52AA5MHHS99#SGGGGS#SS#### #Gh33335A2&",
    "     #h2Xrirh###GGHMHGhMGHhMHHhMHHMHh32Xr2@",
    "     GhAXA533SSGMhhhh323232252A2h33355s;ih",
    "     BHiXMS#SGGGMMhHhXhG22A25XA2XAAXAAsrXS",
    "    &&GX2G#####9#SMMG23M33hGSM55r2552AAAA#",
    "    @&B9999#GMMMHh2XXA3M23GB@GssXM33h52rX#",
    "    @&B#GHhAXA5Hr,,,,,;9#H#&#h22i;;;X2552#",
    "    &#Hhh5XX533HHX;::i;A#@@@9GH;,,,,,iiX5G@",
    "   @9Hh3AX5h32AAA53hH#GHB@B#GMhAsr;;A2sis29",
    "   &Sh2sX5MHHh2AXX2h#&@@&3XXri;2h2Xsi;irisG",
    "   @#hAX2hh35AAAA5M9@@@&&Mr,,,,Ah2i;;iirrrM",
    "   @&Gh3h3Ar;:;s5hG&&9##GM2,,:sXAAX;:;isXXG",
    "    @9M352Xrrrss2hMSSM52X:,,,,,;iXA;,,,i2S&",
    "    @&9GM32XsrrsX22A2As;,,,,,,,:rs;,,,:sH&",
    "     @9#SGM32AXsXAAXXAAAXsr;;;,:;::;iiAG&",
    "      #SHGSGMh32AXssXsXAXsirri:,,,,rAG9",
    "     9SGHMGSGMh52XXXssrii;;::,,:;rs3S",
    "     BSS9999#GM32Xrrr;:,:;:::;;irX3#",
    "    9#9B&&@&9#Hh52Xi;;;:::,::;;;rXH&@",
    "   GSS#B&&&&B#SHh32Asrriiii;iiiiir5#@",
    "   HHGS#9BBBBB#GMM325522AAXXXsrrrrs3B@",
    "  HHGS#S#9B&B&&9SSGHhhh55552AAAXsssXM&@",
    "  GHGS##SS#9###9SGGGGGGGHMMHMh2Xrirr29@@",
    "  #SSS#999#9999#99##9#SGGSGGM32XsrrrXG@@",
    "  h3MGSSS9#9BBBB99SGS###HMHM32XXXXsssAS&@",
    "  GHHGGSSSSS99999GMMHSSSGHM32AXXXsrsssAG&",
    "  9##9#GGGGS#999#SGSSHMh5535555XsriiirsA#@",
    "      hh533hhMMhMHS##GSH2AAAAAXXsrirssrrs",
    "              sXA5hhhhh32Aiirii;;::"
]
# Blink frames replace only the eye rows; everything else stays still.
blink_rows = {
    13: "    @&B#GHhAXA5Hr2AAXXr9#H#&#h22XAXrX2552#",
    14: "    &#Hhh5XX533HHX-----A#@@@9GH-------iX5G@",
    15: "   @9Hh3AX5h32AAA53hH#GHB@B#GMhAsX2AA2sis29",
}
blink_style = """<style>
.cat-open { animation: cat-open 6s steps(1,end) infinite; }
.cat-closed { opacity: 0; animation: cat-closed 6s steps(1,end) infinite; }
@keyframes cat-open { 0%, 94%, 100% { opacity: 1; } 90% { opacity: 0; } }
@keyframes cat-closed { 0%, 94%, 100% { opacity: 0; } 90% { opacity: 1; } }
@media (prefers-reduced-motion: reduce) {
  .cat-open, .cat-closed { animation: none; }
}
</style>"""
# Only aggregate counts are published. Never print repository identifiers or tokens.
# Optional credentials must be explicitly approved for each private repository.
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote
import time

def graphql(query, variables, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "application/json",
                 "User-Agent": "profile-readme-generator"})
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise ValueError("GitHub GraphQL query failed")
    return result["data"]["user"]

tokens = [TOKEN] + [t for t in STATS_TOKENS if t != TOKEN]
discovered = {}
contributed_names = set()
commit_names = set()
private_names = set()
discovery_partial = False

def remember(r, token, contributed=True, commits=False):
    name = r["nameWithOwner"]
    private = r["isPrivate"]
    # Public workflow token is not used to collect private repository statistics.
    if private and token not in STATS_TOKENS:
        return
    key = name.lower()
    entry = discovered.setdefault(key, {"name": name, "private": private, "tokens": []})
    if token not in entry["tokens"]:
        entry["tokens"].append(token)
    if contributed:
        contributed_names.add(key)
    if commits:
        commit_names.add(key)
    if private:
        private_names.add(key)

now = datetime.now(timezone.utc)
created = datetime.fromisoformat(profile["created_at"].replace("Z", "+00:00"))
total = "Unavailable"
restricted = None
# The anonymous public calendar already includes shared private contributions.
# Never sum overlapping totals from different credentials.
calendar_query = """query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { totalContributions }
      restrictedContributionsCount
    }
  }
}"""
repo_query = """query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      commitContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner isPrivate }
      }
      pullRequestContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner isPrivate }
      }
      issueContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner isPrivate }
      }
      pullRequestReviewContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner isPrivate }
      }
    }
  }
}"""
ranges = [
    {"login": USER,
     "from": max(created, datetime(year, 1, 1, tzinfo=timezone.utc)).isoformat(),
     "to": min(now, datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)).isoformat()}
    for year in range(created.year, now.year + 1)
]
# Use the largest complete calendar result, without double-counting activity.
totals = []
for token in tokens:
    if not token:
        continue
    try:
        count = hidden = 0
        for args in ranges:
            c = graphql(calendar_query, args, token)["contributionsCollection"]
            count += c["contributionCalendar"]["totalContributions"]
            hidden += c["restrictedContributionsCount"]
        totals.append((count, hidden))
    except (OSError, KeyError, TypeError, ValueError):
        print("One contribution calendar could not be retrieved.")
    for args in ranges:
        try:
            c = graphql(repo_query, args, token)["contributionsCollection"]
            for kind, entries in c.items():
                if len(entries) >= 100:
                    discovery_partial = True
                for entry in entries:
                    remember(entry["repository"], token, commits=kind == "commitContributionsByRepository")
        except (OSError, KeyError, TypeError, ValueError):
            discovery_partial = True
if totals:
    total = f"{max(n for n, _ in totals):,}"
    restricted = min(h for _, h in totals)

# Also preserve public owned-repository coverage and include all approved
# repositories returned by the recent-contribution connection.
recent_query = """query($login: String!, $cursor: String) {
  user(login: $login) {
    repositoriesContributedTo(first: 100, after: $cursor, includeUserRepositories: true,
      contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY, PULL_REQUEST_REVIEW]) {
      nodes { nameWithOwner isPrivate }
      pageInfo { hasNextPage endCursor }
    }
  }
}"""
for token in tokens:
    if not token:
        continue
    try:
        cursor = None
        while True:
            c = graphql(recent_query, {"login": USER, "cursor": cursor}, token)["repositoriesContributedTo"]
            for r in c["nodes"]:
                if r:
                    remember(r, token)
            if not c["pageInfo"]["hasNextPage"]:
                break
            cursor = c["pageInfo"]["endCursor"]
    except (OSError, KeyError, TypeError, ValueError):
        discovery_partial = True
try:
    for page in range(1, 101):
        batch = json.loads(get(f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}", True))
        for r in batch:
            if not r.get("private") and not r.get("fork") and r.get("size"):
                remember({"nameWithOwner": r["full_name"], "isPrivate": False}, TOKEN, contributed=False)
        if len(batch) < 100:
            break
except (OSError, KeyError, TypeError, ValueError):
    discovery_partial = True

# The contributor endpoint exposes aggregate weekly line counts, not source code.
# Large repositories can return zeroed diffs; missing values are not counted as zero.
def repo_diff(item):
    key, r = item
    if key == f"{USER}/{USER}":
        return (key, 0, 0, False)
    url = "https://api.github.com/repos/" + quote(r["name"], safe="/") + "/stats/contributors"
    auth_tokens = [t for t in r["tokens"] if t] if r["private"] else list(dict.fromkeys([TOKEN] + r["tokens"]))
    for token in auth_tokens:
        for delay in (0, 2, 5):
            if delay:
                time.sleep(delay)
            try:
                raw = get(url, True, token=token)
                if not raw:
                    continue
                data = json.loads(raw)
                if not isinstance(data, list):
                    continue
                for contributor in data:
                    if (contributor.get("author") or {}).get("login", "").lower() == USER.lower():
                        a = sum(w["a"] for w in contributor["weeks"])
                        d = sum(w["d"] for w in contributor["weeks"])
                        if contributor["total"] and a == 0 and d == 0:
                            break
                        return (key, a, d, contributor["total"] > 0)
                else:
                    # An attributed commit in the contribution graph may be
                    # absent from contributor stats, so do not assume zero.
                    if key not in commit_names:
                        return (key, 0, 0, False)
            except (OSError, ValueError, KeyError, TypeError):
                continue
    return None

with ThreadPoolExecutor(max_workers=4) as pool:
    diffs = list(pool.map(repo_diff, discovered.items()))
known = [v for v in diffs if v is not None]
contributed_names.update(k for k, _, _, has_commits in known if has_commits)
added = sum(v[1] for v in known)
deleted = sum(v[2] for v in known)
private_diff = any(k in private_names and has_commits for k, _, _, has_commits in known)
partial_diff = (discovery_partial or len(known) != len(discovered)
                or restricted is None or restricted > 0)
diff_available = bool(known) and (added > 0 or deleted > 0)
contributed = f"{len(contributed_names):,}" if contributed_names else None
if contributed and (discovery_partial or restricted is None or restricted > 0):
    contributed += "+"
website_display = "github.com/tyler-le"
joined = date.today() >= date(2026,12,14)
rows = [
("Company", "Google"),
("Role", "Software Engineer"),
("Education", "UC San Diego | B.S. Computer Science"),
("",""),
("Languages", "Kotlin, Java, Python"),
("Backend", "Spring Boot"),
("Infrastructure", "AWS"),
("Frontend", "React, Next.js"),
("Interests", "Data pipelines"),
("Personal", "Smart home automation, aquariums"),
("",""),
("- Contact",""),
("LinkedIn","linkedin.com/in/le-tyler"),
("Website", website_display),
("",""),
("- GitHub Stats",""),
("Contributions",total),
] + ([("Repos contributed",contributed)] if contributed else []) + ([("Code diff","__diff__")] if diff_available else []) + [
]
for theme, bg, fg, key, val, dim in [
    ("dark","#161b22","#c9d1d9","#ffa657","#a5d6ff","#616e7f"),
    ("light","#f6f8fa","#24292f","#953800","#0550ae","#6e7781")]:
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="680" viewBox="0 0 1080 680"><rect width="1080" height="680" rx="15" fill="{bg}"/><g font-family="Consolas, Menlo, monospace" font-size="15" xml:space="preserve">']
    def line(x,y,s,c):
        out.append(f'<text x="{x}" y="{y}" fill="{c}">{escape(s)}</text>')
    out.append(blink_style)
    for i,s in enumerate(portrait):
        y = 38+i*17.5
        if i in blink_rows:
            out.append(f'<text class="cat-open" x="26" y="{y}" fill="{fg}">{escape(s)}</text>')
            out.append(f'<text class="cat-closed" opacity="0" x="26" y="{y}" fill="{fg}">{escape(blink_rows[i])}</text>')
        else:
            line(26, y, s, fg)
    line(470,45,"tyler@le",fg)
    out.append(f'<path d="M 570 40 H 1050" stroke="{dim}"/>')
    for i,(k,v) in enumerate(rows):
        y=80+i*30
        if k.startswith("-"):
            line(470,y,k,fg)
            out.append(f'<path d="M {485+len(k)*9} {y-5} H 1050" stroke="{dim}"/>')
        elif k:
            line(470,y,". ",dim)
            line(488,y,k+":",key)
            line(488+(len(k)+2)*9,y,"."*(18-len(k)),dim)
            if v == "__diff__":
                green, red = ("#3fb950", "#f85149") if theme == "dark" else ("#1a7f37", "#cf222e")
                plus, minus = f"+{added:,}", f"-{deleted:,}"
                line(675,y,plus,green)
                line(675+9*(len(plus)+2),y,minus,red)
            else:
                line(675,y,v,val)
    out.append("</g></svg>")
    Path(theme+"_mode.svg").write_text("\n".join(out)+"\n")

from hashlib import sha256

def asset_url(theme):
    path = Path(theme + "_mode.svg")
    version = sha256(path.read_bytes()).hexdigest()[:12]
    return f"https://raw.githubusercontent.com/tyler-le/tyler-le/master/{path.name}?v={version}"

Path("README.md").write_text(f"""<picture>
  <source media="(prefers-color-scheme: dark)" srcset="{asset_url('dark')}">
  <img alt="Tyler Le | Software Engineer | Terminal-style profile" src="{asset_url('light')}">
</picture>


<!-- Terminal-style design inspired by Andrew6rant. Generated by update_stats.py. -->
""")
