# 测试失败分类与处理对照表

> 由 [test-runner](../SKILL.md) 按需加载。拿到失败输出后再查对应症状。

运行失败后，按以下分类诊断：

#### 类型 A: 定位符失效

**特征：**
```
TimeoutError: Timeout 10000ms exceeded.
  waiting for locator("text=<功能名>")
```

**处理：** 触发 `locator-replacer` skill，使用 agent-browser 访问真实页面重新抽取定位符（工具选型遵循 [agent-behavior P0.4](../../../rules/agent-behavior/agent-behavior.md)）。

#### 类型 B: 页面加载超时

**特征：**
```
TimeoutError: page.wait_for_load_state: Timeout 30000ms exceeded.
  waiting for "networkidle"
```

**处理：**
1. 检查网络连通性（hosts 配置、VPN）
2. 检查 token 是否过期
3. 增大 `DEFAULT_TIMEOUT`（临时措施）

#### 类型 C: 断言失败

**特征：**
```
AssertionError: <页面中文名>加载失败
assert False
```

**处理：**
1. 页面是否正确导航到目标 URL
2. `PAGE_IDENTIFIER` 定位符是否仍然有效
3. 页面内容是否因版本更新发生变化

#### 类型 D: 认证失败

**特征：**
```
AssertionError: Token 登录失败
```

**处理：**
1. 检查 `config/settings.py` 中的 token 是否有效
2. 检查 `--env` 参数是否选对
3. 检查本地 hosts 是否指向正确的服务器 IP

#### 💡 快速排查建议

当失败需要深入排查时（定位符失效、页面结构变化等），建议进入 [quick-debug](../../quick-debug/SKILL.md) 模式：通过 token 免登直接跳转到问题页面，避免从登录重走完整流程。
