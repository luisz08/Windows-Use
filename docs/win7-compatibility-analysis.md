# Windows 7 兼容性分析报告

> **分析对象**：Windows-Use v0.8.1（commit `0c24f99`）
> **分析日期**：2026-08-23
> **分析方式**：基于源码逐点核查（文件:行号均来自当前代码库），非官方文档推测

---

## 1. 问题背景

README 第 42 行与徽章声称：

> **Prerequisites:** Python 3.10+, Windows 7/8/10/11
> Platform: Windows 7 to 11

本报告核查该声称是否成立，并回答两个问题：

1. 该项目**当前**真的能用在 Win7 上吗？（Python 版本与依赖是否兼容）
2. 项目使用的**技术栈**本质上有可能支持 Win7 吗？（不考虑工程量）

---

## 2. 核心结论

| 问题 | 结论 |
|---|---|
| 当前能跑在 Win7 上吗 | **不能**。Python 版本、TLS/依赖、代码 API 三重障碍，启动即崩 |
| 技术栈有可能支持 Win7 吗 | **可能**。GUI 自动化核心栈天然来自 Win7 时代，只有局部错误选择，无架构原罪 |
| 实际支持下限 | 核心 **Win10 1607+**；功能完整 **Win10 17763+**（README 自己对 VDM 也是这么写的） |

---

## 3. 第一问：当前实际上不兼容 —— 三层证据

### 3.1 第一层：Python 版本直接锁死（最硬的障碍）

- 本项目 `requires-python = ">=3.10"`（pyproject.toml），`.python-version` 为 **3.13**
- **CPython 自 3.9 起放弃 Windows 7 支持**；Win7 上最后一个官方版本是 **3.8.10**（2021 年发布，2024-10 EOL）
- "Python 3.10+ 与 Windows 7" 在官方支持层面自相矛盾：pip 会因 `requires-python` 元数据直接拒绝在 3.8 上安装
- 社区存在非官方 Win7 版 Python 3.10/3.11 构建，但属无支持路线

### 3.2 第二层：依赖生态的隐性排挤

| 障碍 | 细节 |
|---|---|
| TLS | PyPI 自 2018 年起强制 TLS 1.2+；Win7 RTM 仅支持 TLS 1.0，SP1 需打 KB3140245 + 改注册表才启用 TLS 1.2。**但注意**：Python 自带 OpenSSL（不用系统 SChannel），因此 LLM API 调用不受此限——属运维问题而非栈问题（pip 可配源或离线装 wheel） |
| 二进制依赖 | 锁定的 `pillow>=11.2.1`、`pywin32>=311`、`cryptography>=44`、`python-levenshtein>=0.27.1` 均为近年构建，官方只在 Win8.1/Win10 时代运行时上构建测试，Win7 上无人保证 |

### 3.3 第三层：代码中的 Win10+ API 审计（逐点查证）

| 代码位置 | API | 最低系统要求 | Win7 上的后果 |
|---|---|---|---|
| `agent/desktop/service.py:677` | `GetDpiForSystem()` | **Win10 1607+** | **硬崩溃**。无 try/except，且在构建系统提示词时被调用（`context/service.py:80`），Agent 第一步即抛 `AttributeError` |
| `vdm/core.py` 整个模块 | `IVirtualDesktopManager` 等 COM 接口 | **Win10 17763+**（虚拟桌面为 Win10 特性） | COM 类未注册；`Desktop.get_state()` 有 `except RuntimeError` 兜底降级为 "Default Desktop"，但 `desktop_tool` 完全不可用 |
| `uia/core.py:1617` | `SetProcessDpiAwarenessContext` | Win10 1703+ | ✅ 安全。有完整降级链，注释明确写有 "Fallback for Windows 7 / older"，最终落到 Win7 存在的 `SetProcessDPIAware()` |

**关键发现**：作者显然考虑过 Win7——DPI 初始化有降级链、VDM 失败有兜底、UIA3 本身 Vista/7 时代就有、`SetWinEventHook`/`SendInput` 均为 Win7 兼容 API。**唯独 `GetDpiForSystem` 一处漏防，足以让 Agent 在 Win7/8 上启动即崩。**

---

## 4. 第二问：技术栈有可能支持 Win7 —— 逐层评估

### 4.1 核心栈天然来自 Win7 时代

| 层 | 技术 | Win7 可行性 |
|---|---|---|
| UI 感知 | UIA3（`UIAutomationCore.dll`） | ✅ Vista 引入、Win7 原生自带，比老 MSAA 更现代 |
| COM 绑定 | comtypes | ✅ 纯 Python 动态封装，不依赖新运行时 |
| 输入模拟 | `SendInput` / `GetCursorPos` / mouse_event | ✅ Win2000/XP 时代 API |
| 系统事件 | `SetWinEventHook`（Watchdog） | ✅ XP+ |
| 截图 | PIL `ImageGrab`（虚拟屏幕 API） | ✅ Win2000+ |
| DPI | `SetProcessDPIAware` 降级路径 | ✅ 代码已写好 Win7 fallback |
| COM 自动化 | pywin32 | ✅ 旧版本完整支持 Win7 |

**血统证据**：README 致谢的两个项目——[Python-UIAutomation](https://github.com/yinkaisheng/Python-UIAutomation-for-Windows) 与 PyAutoGUI——即同一 API 家族，在 Win7 + Python 3.6/3.8 时代是实际跑通的成熟方案。本项目的感知/操作核心继承自该血统，**架构层面没有 Win7 原罪**。

### 4.2 三个真正障碍的性质分类

| # | 障碍 | 性质 | 可解性 |
|---|---|---|---|
| 1 | VDM 模块 | **OS 特性缺失**，软件无法补 | 永远不可能；但它是隔离良好的可选模块，`get_state()` 已有降级路径，砍掉不伤主干 |
| 2 | `GetDpiForSystem` | **API 选错**，用在了不需要它的地方 | 同族等价替代 `GetDeviceCaps(hdc, LOGPIXELSX)` 为 Win95 时代 API，局部替换即可 |
| 3 | Python 3.10 语法绑定 | **唯一栈级硬约束** | 全项目 **89 处 `match/case`，分布于 8 个核心文件**（`agent/tools/service.py` 24 处、`agent/desktop/service.py` 20 处、`agent/tree/service.py` 14 处等）。结构化模式匹配无法向后移植，3.8 连解析都过不了 → 唯一路线是非官方 Win7 版 Python 3.10/3.11 构建 |

### 4.3 通向 Win7 的路径（不考虑工程量）

1. **运行时**：非官方 Win7 版 Python 3.10/3.11 构建（社区存在，无官方支持）
2. **API 替换**：`get_dpi_scaling()` 改用 `GetDeviceCaps(hdc, LOGPIXELSX)`（Win95+）
3. **模块裁剪**：禁用/移除 VDM（`desktop_tool`），依赖已有的 `RuntimeError` 降级路径
4. **依赖降级**：重锁 `pillow`、`pywin32`、`cryptography`、`python-levenshtein` 等到仍发布 Win7 wheel 的旧版本
5. **运维前提**：Win7 SP1 + TLS 1.2 补丁（KB3140245）或离线安装依赖

---

## 5. 实际支持矩阵（诚实版）

| 操作系统 | 状态 | 决定因素 |
|---|---|---|
| Windows 11（全部版本） | ✅ 完整支持 | — |
| Windows 10 ≥ 17763 | ✅ 完整支持 | VDM 接口底线（README 亦如此声明） |
| Windows 10 1607–17762 | ⚠️ 核心可用，`desktop_tool` 不可用 | VDM 内部接口版本组 |
| Windows 8 / 8.1 | ❌ 启动即崩 | `GetDpiForSystem`（Win10 1607+）；Python 3.10/3.11 官方仅支持到 Win8.1 |
| Windows 7 | ❌ 三重不可用 | Python 官方止于 3.8.10（包拒绝安装）+ 启动崩溃 + 依赖/TLS 问题 |

---

## 6. 附录：关键证据索引

| 证据 | 位置 |
|---|---|
| 平台声称 | `README.md:42`、徽章 "Windows 7–11" |
| Python 下限 | `pyproject.toml` → `requires-python = ">=3.10"`；`.python-version` = 3.13 |
| match/case 语法绑定 | grep 统计 89 处 / 8 文件（无法向后移植到 3.8） |
| DPI 崩溃点 | `windows_use/agent/desktop/service.py:677`（无保护）→ 被 `windows_use/agent/context/service.py:80` 调用 |
| DPI 降级链示例（做对了的地方） | `windows_use/uia/core.py:1617-1618`（PerMonitorV2 → shcore → `SetProcessDPIAware`） |
| VDM 版本组判定 | `windows_use/vdm/core.py:195-231`（BUILD < 22000 归为 WIN10 组，无更低分组） |
| VDM 降级路径 | `windows_use/agent/desktop/service.py:79-87`（`except RuntimeError` → "Default Desktop"） |
| VDM 官方支持声明 | README："Supported on Windows 10 (build 17763+) and all Windows 11 versions" |

---

*本报告基于 2026-08-23 的代码状态生成。若上游修复了 `GetDpiForSystem` 或调整 `requires-python`，第 3、5 节结论需复核。*
