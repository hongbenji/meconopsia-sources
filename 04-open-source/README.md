# 第四期：这可能是互联网史上最严重的危机

- [sources.md](sources.md)：片中用到的数据与来源，每一项都有链接。
- [census.py](census.py)：片中查依赖用的小脚本，谁都能拿去查自己的项目。

## 查依赖的脚本

读项目根目录的 `Cargo.lock` 和 `pnpm-lock.yaml`（有哪个读哪个），向 crates.io 和 npm 的公开注册表查询每个包登记的所有者和最近一次发布时间。只用 Python 标准库，Python 3.8 以上就能跑。

```bash
python3 census.py <项目目录> <输出目录>
```

输出两个文件：

- `packages.csv`：每个包一行，含生态、包名、是否直接依赖、登记的所有者数、团队数、最近一次发布时间、距今天数。
- `summary.json`：汇总，包括包的总数、直接依赖数、只有 1 个登记所有者且没有团队的包、一年以上没发布新版本的包、两者都是的包。

`packages.csv` 里是你项目用到的包名。想公开结果的话，先看一眼里面有没有不想让人知道的东西。

crates.io 要求每秒最多一个请求，所以 Rust 依赖多的项目要跑好几分钟。

### 能说什么，不能说什么

- 注册表里的所有者是有发布权限的账号，和实际干活的人对不上：有的单所有者包背后是活跃的团队，有的多所有者包实际没人管。所以结果可以说"只有一个人有权发布新版本"，说不了"只有一个人在维护"。
- 一年没发布不等于没人维护，很多小包本来就写完了，用不着更新。
- 包按名字去重（同一个包的多个版本算一个），dev 依赖和运行时依赖没有区分。
- 目前只读 `Cargo.lock` 和 `pnpm-lock.yaml`；npm 的 `package-lock.json`、yarn 的 `yarn.lock` 还不支持。

### 片中的数字

2026-10-24 用这个脚本查了作者自己项目的依赖：项目自己写明要用的第三方包有 57 个，实际装进来 650 个；其中 295 个（约 45%）在注册表上只登记了一个所有者、没有团队，150 个（约 23%）同时一年以上没发布新版本。包名清单不公开。

公开版和当时用的版本相比只改了三处，统计方法没变：缺少某个 lock 文件时跳过，不报错；参数不对时打印用法；请求里的 User-Agent 改成这个仓库的地址。

---

## Episode 4: sources and dependency census

- [sources.md](sources.md): every source used in the video, with links.
- [census.py](census.py): the small script used in the video to check a project's dependencies. Run it on your own project.

### The script

It reads `Cargo.lock` and `pnpm-lock.yaml` from the project root (whichever exist) and asks the public crates.io and npm registries for each package's registered owners and latest release date. Standard library only; Python 3.8+.

```bash
python3 census.py <project dir> <output dir>
```

It writes `packages.csv` (one row per package) and `summary.json` (counts of packages, direct dependencies, packages with a single registered owner and no team, packages with no release in over a year, and both). `packages.csv` lists your project's package names, so check it before sharing.

crates.io allows at most one request per second, so projects with many Rust dependencies take a few minutes.

### Limits

- Registry owners are accounts allowed to publish. They are not necessarily the people doing the work: some single-owner packages are backed by active teams, and some multi-owner packages are abandoned. The result supports "only one person can publish a new version", not "only one person maintains it".
- No release in a year does not mean unmaintained; many small packages are simply finished.
- Packages are counted once by name. Dev and runtime dependencies are not separated.
- Only `Cargo.lock` and `pnpm-lock.yaml` are supported for now (no `package-lock.json` or `yarn.lock`).

### Numbers in the video

On 2026-10-24 the author ran this script on their own project: 57 third-party packages declared directly, 650 actually installed; 295 of them (about 45%) have a single registered owner and no team, and 150 (about 23%) also have had no release in over a year. The package list is not published.

The public version differs from the one used for the video in three ways, none of which change the counting: a missing lock file is skipped, wrong arguments print the usage, and the User-Agent points to this repository.
