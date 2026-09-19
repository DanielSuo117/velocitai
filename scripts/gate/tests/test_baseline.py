"""零误报回归基线。

设计阶段对现有 harness 全量实测得出的豁免规则，在此固化为可执行断言：
  - skills/SKILL.md 的 name 与目录名不符（路由 skill，STR002 豁免）
  - rules-index.md / playwright-overview.md 无正反例（索引文件，STR003 豁免）
  - locator-replacer 中 8 处哈希类名全为反例教学（GEN003 豁免）
  - skill-authoring.md 用文件级触发行覆盖 3 个条款（EVI002 文件级判定）
  - CLAUDE.md → CLAUDE.local.md 为 gitignore 的可选文件（STR004/REG002 豁免）
  - docs/superpowers/** 为长篇流程文档（全量 STR 豁免）

任何 checker 改动导致本仓库出现 BLOCK，即为引入了误报。
"""
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from gate import runner
from gate.violation import Severity

REPO = pathlib.Path(__file__).resolve().parents[3]


class TestBaseline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.violations = runner.run_audit(REPO)

    def test_no_block_violations(self):
        blocks = [v for v in self.violations if v.severity == Severity.BLOCK]
        self.assertEqual(
            blocks, [],
            "现有 harness 出现 BLOCK 违规，说明 checker 引入了误报：\n"
            + "\n".join(v.render() for v in blocks),
        )

    def test_no_ask_violations_in_audit(self):
        # audit 模式不判定新建，不应产生 ASK
        asks = [v for v in self.violations if v.severity == Severity.ASK]
        self.assertEqual(asks, [], "audit 模式不应产生 ASK")

    def test_audit_actually_scanned_files(self):
        # 防止 glob 写错导致「零违规」其实是「零扫描」。
        # 断言必须落在 audit 自身的产物上 —— 检查磁盘文件存在、或在测试里另跑一次
        # glob，都只能证明文件系统没问题，证明不了 run_audit 走到过那些文件。
        evi003 = [
            v for v in self.violations
            if v.code == "EVI003" and v.path.endswith("skill-authoring.md")
        ]
        self.assertGreaterEqual(
            len(evi003), 3,
            "audit 未产出 skill-authoring.md 的 EVI003 —— 说明它很可能根本没扫到 rules/，"
            "此时其他断言的「零 BLOCK」是假绿。实际产出：\n"
            + "\n".join(v.render() for v in self.violations),
        )


class TestAuditCoverage(unittest.TestCase):
    """audit 必须真的走到三个 glob 根，每根各有锚点。

    「零 BLOCK」有两种成因：都合规，或者 glob 写错、一个文件都没扫到。后者会把
    上面所有断言变成假绿。这里对 **audit 自己喂给 checker 的路径集合**取证 ——
    在测试里另跑一遍 glob 只能证明文件系统没问题，证明不了 run_audit 走到过。

    锚点选的是 CLAUDE.md 路由表点名的结构性文件，不是文件总数：总数对任何无关的
    内容增删都会变红，而结构性文件的消失本来就该让人来改这个测试。
    """

    @classmethod
    def setUpClass(cls):
        seen = []
        real = runner._content_checks

        def spy(rel, text, root, is_new=False):
            seen.append(str(rel))
            return real(rel, text, root, is_new=is_new)

        with mock.patch.object(runner, "_content_checks", spy):
            runner.run_audit(REPO)
        cls.scanned = set(seen)

    def test_skills_glob_reached_router_and_nested(self):
        # skills/SKILL.md 验证根层，skills/<name>/SKILL.md 验证 ** 递归那一层
        self.assertIn("skills/SKILL.md", self.scanned, self._hint())
        self.assertIn("skills/quick-debug/SKILL.md", self.scanned, self._hint())

    def test_rules_glob_reached_root_and_nested(self):
        self.assertIn("rules/rules-index.md", self.scanned, self._hint())
        self.assertIn("rules/agent-behavior/evolution-gate.md", self.scanned, self._hint())

    def test_docs_glob_reached(self):
        self.assertIn("docs/architecture.md", self.scanned, self._hint())
        self.assertIn("docs/setup.md", self.scanned, self._hint())

    def test_superpowers_never_scanned(self):
        # docs/*.md 是非递归的，且 classify 另有豁免 —— 两道防线都不该让 spec/plan 进来
        leaked = [p for p in self.scanned if p.startswith("docs/superpowers/")]
        self.assertEqual(leaked, [], f"docs/superpowers/ 不应被扫描：{leaked}")

    @classmethod
    def _hint(cls):
        return ("audit 没扫到该文件 —— 对应的 glob 很可能坏了，此时「零 BLOCK」是假绿。"
                f"实际扫到 {len(cls.scanned)} 个文件：" + ", ".join(sorted(cls.scanned)))


if __name__ == "__main__":
    unittest.main()
