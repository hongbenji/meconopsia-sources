"""统计一个项目的第三方依赖由多少人维护（Meconopsia 第四期）。
Count how many people are registered as owners of a project's third-party dependencies.

用法 / Usage：python3 census.py <项目目录 project dir> <输出目录 output dir>
读取项目根目录的 Cargo.lock 和 pnpm-lock.yaml（有哪个读哪个），向 crates.io 和 npm 公开注册表查询每个包的
登记所有者（owners / maintainers）和最近一次发布时间。输出 packages.csv 和 summary.json，只含包名和统计，不含项目路径。

口径限制：注册表里的所有者是"有发布权限的账号"，不等于实际在维护的人；
团队账号（crates.io 的 github:org:team）记为 1 个团队。
"""
import csv, json, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = "meconopsia-dependency-census (+https://github.com/hongbenji/meconopsia-sources)"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:
            if attempt == 3:
                return {"_error": str(e)}
            time.sleep(2 * (attempt + 1))


def cargo_packages(root):
    f = root / "Cargo.lock"
    if not f.exists():
        print("没有 Cargo.lock，跳过 crates.io / no Cargo.lock, skipping crates.io", file=sys.stderr)
        return [], set()
    s = f.read_text()
    out, local, deps = {}, set(), {}
    for b in s.split("[[package]]")[1:]:
        name = re.search(r'name = "([^"]+)"', b).group(1)
        src = re.search(r'source = "([^"]+)"', b)
        d = re.search(r"dependencies = \[(.*?)\]", b, re.S)
        if d:
            deps.setdefault(name, set()).update(x.split()[0] for x in re.findall(r'"([^"]+)"', d.group(1)))
        if not src:
            local.add(name)
        elif src.group(1).startswith("registry+"):
            out[name] = True
    direct = {x for l in local for x in deps.get(l, ())} - local
    return sorted(out), direct


def npm_packages(root):
    f = root / "pnpm-lock.yaml"
    if not f.exists():
        print("没有 pnpm-lock.yaml，跳过 npm / no pnpm-lock.yaml, skipping npm", file=sys.stderr)
        return [], set()
    s = f.read_text()
    i, j = s.find("\npackages:\n"), s.find("\nsnapshots:\n")
    sec = s[i: j if j > 0 else None]
    keys = re.findall(r"^  '?([^\s':]+@[^\s':]+)'?:\s*$", sec, re.M)
    names = sorted({k.rsplit("@", 1)[0] for k in keys})
    direct = set()
    for f in root.rglob("package.json"):
        if "node_modules" in f.parts:
            continue
        d = json.loads(f.read_text())
        for k in ("dependencies", "devDependencies"):
            direct |= set(d.get(k, {}))
    return names, direct


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    root, outdir = Path(sys.argv[1]), Path(sys.argv[2])
    now = datetime.now(timezone.utc)
    rows = []

    crates, cdirect = cargo_packages(root)
    for n in crates:
        own = get(f"https://crates.io/api/v1/crates/{n}/owners")
        meta = get(f"https://crates.io/api/v1/crates/{n}")
        users = [u for u in own.get("users", []) if u.get("kind") == "user"]
        teams = [u for u in own.get("users", []) if u.get("kind") == "team"]
        upd = (meta.get("crate") or {}).get("updated_at")
        rows.append({"ecosystem": "cargo", "name": n, "direct": n in cdirect,
                     "owner_users": len(users), "owner_teams": len(teams),
                     "last_release": upd, "error": own.get("_error") or meta.get("_error") or ""})
        time.sleep(1.0)  # crates.io 爬取政策：每秒至多 1 个请求

    names, ndirect = npm_packages(root)
    for n in names:
        d = get("https://registry.npmjs.org/" + urllib.parse.quote(n, safe="@"))
        m = d.get("maintainers") or []
        modified = (d.get("time") or {}).get("modified")
        latest = (d.get("dist-tags") or {}).get("latest")
        last = (d.get("time") or {}).get(latest) if latest else modified
        rows.append({"ecosystem": "npm", "name": n, "direct": n in ndirect,
                     "owner_users": len(m), "owner_teams": 0,
                     "last_release": last, "error": d.get("_error", "")})
        time.sleep(0.2)

    if not rows:
        sys.exit("没有找到可查询的包 / no packages found")
    outdir.mkdir(parents=True, exist_ok=True)

    for r in rows:
        if r["last_release"]:
            t = datetime.fromisoformat(r["last_release"].replace("Z", "+00:00"))
            r["days_since_release"] = (now - t).days
        else:
            r["days_since_release"] = ""

    with open(outdir / "packages.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def summary(sel):
        ok = [r for r in sel if not r["error"]]
        return {
            "packages": len(sel),
            "lookup_errors": len(sel) - len(ok),
            "direct": sum(r["direct"] for r in sel),
            "single_owner_no_team": sum(1 for r in ok if r["owner_users"] == 1 and r["owner_teams"] == 0),
            "no_release_365d": sum(1 for r in ok if r["days_since_release"] != "" and r["days_since_release"] > 365),
            "single_owner_and_no_release_365d": sum(1 for r in ok if r["owner_users"] == 1 and r["owner_teams"] == 0
                                                     and r["days_since_release"] != "" and r["days_since_release"] > 365),
        }

    out = {"queried_at": now.isoformat(timespec="seconds"),
           "cargo": summary([r for r in rows if r["ecosystem"] == "cargo"]),
           "npm": summary([r for r in rows if r["ecosystem"] == "npm"]),
           "all": summary(rows)}
    (outdir / "summary.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
