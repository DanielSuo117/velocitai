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


if __name__ == "__main__":
    unittest.main()
