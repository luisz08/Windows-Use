# Running Windows-Use on Windows 7

> **Status: community-supported.** Windows 7 has never been tested by the maintainers.
> This guide documents a known-viable path based on a code-level compatibility audit
> (`docs/win7-compatibility-analysis.md`). Expect rough edges, and always run the agent
> inside a virtual machine — see [Security](../SECURITY.md).

## What works, what doesn't

| Capability | Status on Win7 |
|---|---|
| UI tree reading (UIA3), click/type/scroll/move, shortcuts, shell, file/memory tools, screenshots | ✅ Works — these use APIs that ship with Win7 |
| Virtual desktops (`desktop_tool`) | ❌ Not available — the feature requires Windows 10 build 17763+. The tool returns a clear error; everything else keeps working |
| System prompt DPI info | ✅ Works — falls back to `GetDeviceCaps` automatically |

## Prerequisites

1. **Windows 7 SP1** (64-bit strongly recommended) with:
   - **UCRT**: [KB2999226](https://www.microsoft.com/en-us/download/details.aspx?id=49077) — required by modern Python and MSVC-built wheels
   - **TLS 1.2**: [KB3140245](https://support.microsoft.com/en-us/help/3140245) — only needed for `pip`/`git` over HTTPS; the agent's own HTTPS calls use Python's bundled OpenSSL and are unaffected
2. **Python 3.10 or 3.11** — official CPython stopped at 3.8 on Win7, and this project
   requires 3.10+ syntax (`match` statements). Use a community build of CPython 3.10/3.11
   for Windows 7 (search "python 3.10 windows 7 build"). These are unofficial and untested
   by the CPython team — use at your own risk.
3. **pip** bundled with that Python (or bootstrapped via `ensurepip`).

## Install

From this fork (the Win7 changes are on the `win7-support` branch):

```powershell
git clone -b win7-support https://github.com/luisz08/Windows-Use.git
cd Windows-Use
pip install .
```

The dependency constraints in `pyproject.toml` already hold the Win7-compatible line:
`cryptography <45` (44.0.x is the last with Win7 wheels) and `psutil <8`
(8.0.0 dropped Win7). If you install dependencies manually instead:

```powershell
pip install "cryptography>=44.0.0,<45" "psutil>=7.0.0,<8"
```

Everything else (pywin32, Pillow, comtypes, pynacl, python-levenshtein) never dropped
Win7 wheels and installs as pinned.

If `pip` cannot reach PyPI even after KB3140245, download wheels on another machine and
install offline: `pip install --no-index --find-links <wheel-dir> .`

## Known limitations

- **Virtual desktop tools are unavailable.** `desktop_tool` (create/remove/rename/switch)
  returns a clear "not supported on this Windows version" error. The desktop state shows
  a single "Default Desktop" placeholder.
- **Unofficial Python.** You are outside official support for CPython and for every wheel
  you install. If something misbehaves, first reproduce with a trivial `import` +
  `print` script before blaming the agent.
- **Untested matrix.** The compatibility claims come from static analysis of every Win32
  API call in the codebase plus dependency changelogs, not from a QA pass on real Win7
  hardware. Bug reports (and especially confirmed-working reports) are welcome on the
  fork's issue tracker.

## Why not just use the PyPI release?

The published `windows-use` releases do not carry the Win7 fixes (DPI fallback, VDM
degradation, dependency caps). Install from this fork's `win7-support` branch until the
changes are merged upstream.
