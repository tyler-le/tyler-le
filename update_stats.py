import json, os, urllib.request, io
from pathlib import Path
from datetime import date
from html import escape
from PIL import Image, ImageOps

USER = "tyler-le"
TOKEN = os.environ.get("GH_TOKEN", "")
def get(url, auth=False):
    headers = {"User-Agent": "profile-readme-generator"}
    if auth and TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return r.read()
profile = json.loads(get("https://api.github.com/users/" + USER, True))
avatar_raw = Image.open(io.BytesIO(get(profile["avatar_url"]))).convert("L")
# Cat-focused crop; normalized coordinates can be refined after visual review.
w, h = avatar_raw.size
cat_box = (int(w * 0.20), int(h * 0.05), int(w * 0.90), int(h * 0.88))
avatar = ImageOps.autocontrast(ImageOps.pad(avatar_raw.crop(cat_box), (42, 27), color=0), cutoff=1)
ramp = " .:-=+*#%@"
portrait = ["".join(ramp[p * (len(ramp)-1)//255] for p in list(avatar.crop((0,y,42,y+1)).getdata())) for y in range(27)]
repos = []
for page in range(1, 101):
    batch = json.loads(get(f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}", True))
    repos.extend(batch)
    if len(batch) < 100: break
# Public default-branch code changes attributed to this GitHub account.
# Do not access or publish private employer repository diff statistics.
from concurrent.futures import ThreadPoolExecutor
import time

def repo_diff(repo):
    if not repo.get("size"):
        return (0, 0)
    url = "https://api.github.com/repos/" + repo["full_name"] + "/stats/contributors"
    for delay in (0, 2, 5):
        if delay:
            time.sleep(delay)
        try:
            raw = get(url, True)
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
                        return None
                    return (a, d)
            return (0, 0)
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return None

eligible = [r for r in repos if not r.get("private") and not r.get("fork")
            and r["full_name"].lower() != f"{USER}/{USER}".lower()]
with ThreadPoolExecutor(max_workers=4) as pool:
    diffs = list(pool.map(repo_diff, eligible))
known = [v for v in diffs if v is not None]
added = sum(v[0] for v in known)
deleted = sum(v[1] for v in known)
partial_diff = len(known) != len(eligible)
diff_available = bool(known) and (added > 0 or deleted > 0)

# GitHub exposes anonymized private contributions when profile sharing is enabled.
# Do not request repository access or publish private repository names.
total = private = "Unavailable"
try:
    query = """query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          restrictedContributionsCount
          contributionCalendar { totalContributions }
        }
      }
    }"""
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": USER}}).encode(),
        headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json", "User-Agent": "profile-readme-generator"})
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.load(response)
    c = result["data"]["user"]["contributionsCollection"]
    total = f'{c["contributionCalendar"]["totalContributions"]:,}'
    private = f'{c["restrictedContributionsCount"]:,}'
except (OSError, KeyError, TypeError, ValueError) as exc:
    print("Contribution totals unavailable:", type(exc).__name__)
# Prefer a separate portfolio URL from the public GitHub profile when present.
website = (profile.get("blog") or "https://github.com/tyler-le").strip()
if not website.startswith(("https://", "http://")):
    website = "https://" + website
website_display = website.removeprefix("https://").removeprefix("http://").rstrip("/")
joined = date.today() >= date(2026,12,14)
rows = [
("Current", "Google" if joined else "Coursera"),
("Occupation", "Software Engineer"),
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
("Contribs (1 yr)",total),
("Private (1 yr)",private),
] + ([("Public code diff","__diff__")] if diff_available else []) + [
]
for theme, bg, fg, key, val, dim in [
    ("dark","#161b22","#c9d1d9","#ffa657","#a5d6ff","#616e7f"),
    ("light","#f6f8fa","#24292f","#953800","#0550ae","#6e7781")]:
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="990" height="620" viewBox="0 0 990 620"><rect width="990" height="620" rx="15" fill="{bg}"/><g font-family="Consolas, Menlo, monospace" font-size="15" xml:space="preserve">']
    def line(x,y,s,c):
        out.append(f'<text x="{x}" y="{y}" fill="{c}">{escape(s)}</text>')
    for i,s in enumerate(portrait):
        line(15, 31+i*19, s, fg)
    line(415,31,"tyler@le",fg)
    out.append(f'<path d="M 500 26 H 965" stroke="{dim}"/>')
    for i,(k,v) in enumerate(rows):
        y=60+i*24
        if k.startswith("-"):
            line(415,y,k,fg)
            out.append(f'<path d="M {425+len(k)*9} {y-5} H 965" stroke="{dim}"/>')
        elif k:
            line(415,y,". ",dim)
            line(433,y,k+":",key)
            line(433+(len(k)+2)*9,y,"."*(18-len(k)),dim)
            if v == "__diff__":
                green, red = ("#3fb950", "#f85149") if theme == "dark" else ("#1a7f37", "#cf222e")
                plus, minus = f"+{added:,}", f"-{deleted:,}"
                line(620,y,plus,green)
                line(620+9*(len(plus)+2),y,minus,red)
                if partial_diff:
                    line(620+9*(len(plus)+len(minus)+4),y,"(partial)",dim)
            else:
                line(620,y,v,val)
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
