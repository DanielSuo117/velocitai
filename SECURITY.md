<div align="center">

# 安全策略 · Security Policy

**[中文](#中文) | [English](#english)**

</div>

---

<a id="中文"></a>

## 中文

### 报告漏洞

**请不要通过公开 Issue 报告安全问题** —— 那等于在修复之前先把它公之于众。

请走 GitHub 的私密上报通道：本仓库 **Security** 标签页 → **Report a vulnerability**。
只有维护者可见。

若该入口不可用，请开一个**不含任何技术细节**的 Issue 说明你需要私下联系，
维护者会提供渠道。

上报时请尽量包含：受影响的版本或提交、复现步骤、实际影响、以及你认为的修复方向。

### 响应

本项目由个人在业余时间维护，没有 SLA。一般在 **7 天内**给出首次回应。
问题确认后会在主分支修复，并在提交信息中说明。

若你希望被致谢，请在上报时注明；默认不会公开上报者身份。

### 支持范围

目前尚无发布版本，只维护 `main` 分支的最新提交。请基于最新 `main` 复现后再上报。

### 使用本项目前请知悉

以下行为是设计使然，不是漏洞，但会影响你的安全边界，**请在引入前确认可接受**。

**一、hooks 会在你的机器上执行命令**

作为 Claude Code 插件安装后，`hooks/hooks.json` 声明的命令会在 `Write` / `Edit`
和 `git commit` 时自动执行（落库校验脚本与代码图谱构建）。这是插件机制的正常形态，
但意味着**你信任的是本仓库的代码**。建议安装前通读 `hooks/hooks.json` 与
`scripts/gate_cli.py`，并从固定提交安装而非始终跟随 `main`。

**二、`--self-heal=auto` 会把页面内容发往第三方 API**

该档位在规则无法重建定位符时，会把当前页面的元素快照发送至 `api.anthropic.com` 用于推理：最多 **60 个元素**，
每个含标签、部分属性（`id` / `data-testid` / `data-test` / `data-qa` / `name` /
`type` / `placeholder`）、ARIA 角色与可及名称，以及最长 **60 字符**的文本。

**若被测页面含真实用户数据（姓名、手机号、邮箱、订单号、金额等），这些内容会随之出境。**

`off` / `on` / `strict` 三档**完全不联网**。请勿在未脱敏的生产环境使用 `auto`。

**三、`--self-heal=auto` 会改写工作区源码**

该档位会把修复结果写回 PageObject 源文件，并留下一份 `.heal-bak` 备份
（仅在首次写回时创建）。请在干净的 git 工作区使用，以便随时 `git diff` 复核与回滚。

**四、落库闸门是 fail-open 的**

闸门自身发生任何故障（脚本异常、超时、输入畸形）时一律放行。
它是质量护栏，**不是安全边界**，不要把它当作对抗恶意输入的防线。

### 不属于安全问题的情形

- 闸门未能拦截某条低质量沉淀（质量问题，请开普通 Issue）
- 自愈未能重建某个定位符（设计上就允许放弃，请开普通 Issue）
- 需要本机已有写权限才能触发的问题

---

<a id="english"></a>

## English

### Reporting a Vulnerability

**Please do not report security issues through public Issues** — that discloses
them before a fix exists.

Use GitHub's private channel: the **Security** tab of this repository →
**Report a vulnerability**. Only maintainers can see it.

If that entry point is unavailable, open an Issue containing **no technical
details** stating that you need a private contact, and a maintainer will provide one.

Please include where you can: the affected version or commit, reproduction steps,
the actual impact, and any fix you have in mind.

### Response

This project is maintained by one person in their spare time; there is no SLA.
Expect a first response within **7 days**. Confirmed issues are fixed on the main
branch and noted in the commit message.

Tell us if you would like to be credited — reporters are not named by default.

### Supported Versions

There are no releases yet; only the latest commit on `main` is maintained.
Please reproduce against current `main` before reporting.

### Before You Adopt This Project

The following are by design, not vulnerabilities — but they change your security
boundary, so **confirm they are acceptable before adopting**.

**1. Hooks execute commands on your machine**

Installed as a Claude Code plugin, the commands declared in `hooks/hooks.json` run
automatically on `Write` / `Edit` and on `git commit` (the sediment-gate script and
graph build). That is how the plugin mechanism works, but it means **you are trusting
this repository's code**. Read `hooks/hooks.json` and `scripts/gate_cli.py` before
installing, and pin to a specific commit rather than always tracking `main`.

**2. `--self-heal=auto` sends page content to a third-party API**

When rules cannot rebuild a locator, this mode sends a snapshot of the live page
to `api.anthropic.com` for inference: up to **60 elements**, each with its tag, a
subset of attributes (`id` / `data-testid` / `data-test` / `data-qa` / `name` /
`type` / `placeholder`), ARIA role and accessible name, and up to **60 characters**
of text.

**If the page under test holds real user data — names, phone numbers, emails, order
IDs, amounts — that content leaves your machine with it.**

The `off` / `on` / `strict` modes make **no network calls at all**. Do not run `auto`
against production data that has not been masked.

**3. `--self-heal=auto` rewrites source files in your working tree**

It writes the fix back into the PageObject source and leaves a `.heal-bak` backup
(created only on the first write-back). Use it on a clean git tree so you can always
`git diff` and roll back.

**4. The sediment gate is fail-open**

Any internal failure — script error, timeout, malformed input — lets the write through.
It is a quality guardrail, **not a security boundary**. Do not rely on it to stop
malicious input.

### Out of Scope

- The gate failing to catch a low-quality entry (a quality issue — open a normal Issue)
- Self-healing failing to rebuild a locator (giving up is by design — open a normal Issue)
- Anything that requires pre-existing local write access to trigger
