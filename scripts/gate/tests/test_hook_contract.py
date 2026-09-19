import contextlib
import io
import json
import pathlib
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from gate.checkers import structure  # noqa: E402

CLI = pathlib.Path(__file__).resolve().parents[2] / "gate_cli.py"

WARN_SIZED_BODY = "行\n" * 320  # > STR005 的 300 行阈值，纯 WARN


def run_cli(mode, payload):
    return subprocess.run(
        [sys.executable, str(CLI), "--mode", mode],
        input=json.dumps(payload), capture_output=True, text=True, timeout=30,
    )


def run_cli_in(cwd, *args, stdin=""):
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(cwd), input=stdin, capture_output=True, text=True, timeout=60,
    )


class TestHookContract(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        (self.root / ".git").mkdir()
        (self.root / "skills" / "demo").mkdir(parents=True)
        (self.root / "rules").mkdir()

    def _payload(self, tool, path, **ti):
        ti["file_path"] = str(self.root / path)
        return {"tool_name": tool, "tool_input": ti, "cwd": str(self.root)}

    def test_clean_write_exits_zero_silently(self):
        p = self._payload("Write", "docs/architecture.md", content="# 架构\n")
        (self.root / "docs").mkdir(exist_ok=True)
        r = run_cli("write", p)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")

    def test_block_exits_two_with_deny(self):
        target = self.root / "skills" / "demo" / "SKILL.md"
        target.write_text("---\nname: demo\ndescription: d\n---\n", encoding="utf-8")
        p = self._payload("Write", "skills/demo/SKILL.md",
                          content='---\nname: wrong\ndescription: d\n---\n')
        r = run_cli("write", p)
        self.assertEqual(r.returncode, 2)
        out = json.loads(r.stdout)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("STR002", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_new_file_exits_zero_with_ask(self):
        p = self._payload("Write", "skills/demo/SKILL.md",
                          content="---\nname: demo\ndescription: d\n---\n")
        r = run_cli("write", p)
        self.assertEqual(r.returncode, 0)
        out = json.loads(r.stdout)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "ask")
        self.assertIn("触发条件", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_garbage_stdin_fails_open(self):
        r = subprocess.run(
            [sys.executable, str(CLI), "--mode", "write"],
            input="not json at all", capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(r.returncode, 0)


class TestWarnVisibility(unittest.TestCase):
    """WARN 必须在 stdout 上看得见。

    STR005 / GEN004 / EVI003 / EVI004 四个码是纯 WARN，全部走退出码 0。而退出码 0
    时宿主是从 **stdout** 组装要展示给用户的 hook 消息的，只写 stderr 等于没写 ——
    spec §13 把这一点列为「实现期首个任务即验证」的遗留问题，此前既没验证也没兜底。
    兜底手段是 stdout 上的 systemMessage（宿主文档中「对所有 hook 展示给用户」的
    通用字段）。
    """

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        (self.root / ".git").mkdir()
        (self.root / "docs").mkdir()
        (self.root / "skills" / "demo").mkdir(parents=True)

    def _payload(self, tool, path, **ti):
        ti["file_path"] = str(self.root / path)
        return {"tool_name": tool, "tool_input": ti, "cwd": str(self.root)}

    def test_warn_only_exits_zero_and_prints_to_stdout(self):
        p = self._payload("Write", "docs/big.md", content=WARN_SIZED_BODY)
        r = run_cli("write", p)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)          # stdout 必须是可解析的单个 JSON 对象
        self.assertIn("STR005", out["systemMessage"])
        self.assertIn("落库校验提示", out["systemMessage"])
        # 不得夹带决策：WARN 不阻塞，也不弹授权框
        self.assertNotIn("hookSpecificOutput", out)
        # stderr 那一份照旧保留
        self.assertIn("STR005", r.stderr)

    def test_mixed_warn_and_block_loses_neither(self):
        target = self.root / "skills" / "demo" / "SKILL.md"
        target.write_text("---\nname: demo\ndescription: d\n---\n", encoding="utf-8")
        p = self._payload(
            "Write", "skills/demo/SKILL.md",
            content="---\nname: wrong\ndescription: d\n---\n" + WARN_SIZED_BODY)
        r = run_cli("write", p)
        self.assertEqual(r.returncode, 2)
        out = json.loads(r.stdout)
        self.assertIn("STR002", out["hookSpecificOutput"]["permissionDecisionReason"])
        self.assertIn("STR005", out["systemMessage"])   # WARN 没被最高档位吞掉
        self.assertIn("STR005", r.stderr)

    def test_mixed_warn_and_ask_loses_neither(self):
        # 新建（ASK）同时体量超标（WARN）：ASK 也走退出码 0，WARN 同样只能靠 stdout
        p = self._payload("Write", "skills/demo/SKILL.md",
                          content="---\nname: demo\ndescription: d\n---\n" + WARN_SIZED_BODY)
        r = run_cli("write", p)
        self.assertEqual(r.returncode, 0)
        out = json.loads(r.stdout)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "ask")
        self.assertIn("STR005", out["systemMessage"])

    def test_clean_write_still_prints_nothing(self):
        p = self._payload("Write", "docs/small.md", content="# 短文档\n")
        r = run_cli("write", p)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")


class TestAuditModeThroughCli(unittest.TestCase):
    """--mode audit 走真实进程，校验退出码与 JSON 契约（而非只调 runner 函数）。"""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        (self.root / ".git").mkdir()
        (self.root / "rules").mkdir()

    def test_clean_repo_exits_zero_silently(self):
        (self.root / "rules" / "ok.md").write_text("❌ 反例\n✅ 正例\n", encoding="utf-8")
        r = run_cli_in(self.root, "--mode", "audit")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "")

    def test_violating_repo_exits_two_with_deny(self):
        (self.root / "rules" / "bad.md").write_text("✅ 只有正例\n", encoding="utf-8")
        r = run_cli_in(self.root, "--mode", "audit")
        self.assertEqual(r.returncode, 2)
        out = json.loads(r.stdout)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("STR003", out["hookSpecificOutput"]["permissionDecisionReason"])


@unittest.skipUnless(shutil.which("git"), "本机未安装 git，跳过 commit 模式进程级测试")
class TestCommitModeThroughCli(unittest.TestCase):
    """--mode commit 走真实进程 + 真实暂存区。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True, capture_output=True)
        (self.root / "rules").mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def _stage(self, *rels):
        subprocess.run(["git", "-C", str(self.root), "add", *rels],
                       check=True, capture_output=True)

    def test_nothing_staged_exits_zero_silently(self):
        r = run_cli_in(self.root, "--mode", "commit")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "")

    def test_staged_violation_exits_two_with_deny(self):
        (self.root / "rules" / "bad.md").write_text("✅ 只有正例\n", encoding="utf-8")
        self._stage("rules/bad.md")
        r = run_cli_in(self.root, "--mode", "commit")
        self.assertEqual(r.returncode, 2)
        out = json.loads(r.stdout)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("STR003", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_staged_clean_file_exits_zero(self):
        (self.root / "rules" / "ok.md").write_text("❌ 反例\n✅ 正例\n", encoding="utf-8")
        self._stage("rules/ok.md")
        r = run_cli_in(self.root, "--mode", "commit")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "")


class TestArgparseFailOpen(unittest.TestCase):
    """参数写错不得变成 deny。

    argparse 用法错误抛 SystemExit(2)，而 PreToolUse 里的退出码 2 意思是「拒绝这次
    工具调用」。不接住的话，一个 typo 会拿 argparse 的 usage 文本当拒绝理由把用户
    的工具调用挡下来 —— fail-open 之外最后一处 fail-closed 缺口。
    """

    def test_unknown_mode_exits_zero(self):
        r = subprocess.run([sys.executable, str(CLI), "--mode", "typo"],
                           input="", capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_missing_mode_exits_zero(self):
        r = subprocess.run([sys.executable, str(CLI)],
                           input="", capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_unknown_flag_exits_zero(self):
        r = subprocess.run([sys.executable, str(CLI), "--mode", "audit", "--bogus"],
                           input="", capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)


class TestFailOpenOnCheckerCrash(unittest.TestCase):
    """§9.4 的头号承诺：任何 checker 抛出的异常都不得逃逸到退出码。

    用 runpy 在进程内执行 gate_cli 的 __main__ 块 —— fail-open 的兜底就写在那里，
    只调 main() 测不到它。
    """

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        (self.root / ".git").mkdir()
        (self.root / "skills" / "demo").mkdir(parents=True)
        self.payload = json.dumps({
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(self.root / "skills" / "demo" / "SKILL.md"),
                "content": "---\nname: demo\ndescription: d\n---\n",
            },
            "cwd": str(self.root),
        })

    def _run_main(self):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "argv", ["gate_cli.py", "--mode", "write"]), \
                mock.patch.object(sys, "stdin", io.StringIO(self.payload)), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                runpy.run_path(str(CLI), run_name="__main__")
        return cm.exception.code, out.getvalue(), err.getvalue()

    def test_checker_exception_exits_zero(self):
        def boom(*a, **k):
            raise RuntimeError("checker 内部炸了")

        with mock.patch.object(structure, "check", boom):
            code, out, err = self._run_main()
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "")       # 绝不能吐出半个决策
        self.assertIn("已放行", err)

    def test_sanity_same_harness_reports_violation_without_the_crash(self):
        # 对照组：不打桩时同一条路径会正常产出 ASK，证明上面的 exit 0 不是
        # 因为这条路径压根没跑到 checker
        code, out, err = self._run_main()
        self.assertEqual(code, 0)
        self.assertEqual(
            json.loads(out)["hookSpecificOutput"]["permissionDecision"], "ask")


if __name__ == "__main__":
    unittest.main()
