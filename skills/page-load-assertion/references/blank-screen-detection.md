# 模式 E：白屏检测 + 空数据 vs 有数据 三态判断

> 由 [page-load-assertion](../SKILL.md) 按需加载。
> 仅当页面是 SPA、且容器可见不代表内容已挂载时才需要读本文。

SPA 应用中，容器 div 可能存在于 DOM 且 `is_visible` 返回 true，但内部组件未挂载（白屏）。此时模式 A/B 的 `is_visible(容器)` 会误判为正常。

**页面内容区有三种状态，必须分别处理**：

```
页面内容区状态
│
├─ 白屏（渲染失败）
│  内容区子元素数 = 0，组件未挂载
│  → 判定：❌ 测试失败，报"内容区域未渲染，疑似白屏"
│
├─ 空数据（无业务数据但渲染正常）
│  内容区子元素数 > 0，但无业务数据项
│  通常有空状态提示（图片 + "暂无数据"/"还没有收藏题哦"等文案）
│  → 判定：✅ 渲染正常，页面确实没有业务数据
│
└─ 有数据（正常渲染）
   内容区子元素数 > 0，且有业务数据项
   → 判定：✅ 渲染正常
```

**实现模板**：

```python
# 定位符
CONTENT_CONTAINER = "css=<内容主容器>"                 # 页面骨架容器
EMPTY_STATE = "css=<空状态提示元素>"                    # 空状态组件（图片+文案）
DATA_ITEM = "css=<业务数据项>"                          # 单个数据条目

def get_content_render_state(self) -> str:
    """返回内容区渲染状态：'blank' / 'empty' / 'loaded'。"""
    return self.page.evaluate("""() => {
        const container = document.querySelector('<内容主容器选择器>');
        if (!container) return 'blank';
        const contentArea = container.querySelector('<内容区域选择器>');
        if (!contentArea || contentArea.children.length === 0) return 'blank';
        return 'loaded';
    }""")

def is_content_rendered(self) -> bool:
    """白屏检测：容器存在但内容区无子元素 → False。
    空数据和有数据都算渲染成功 → True。"""
    return self.get_content_render_state() != 'blank'

def has_data_items(self) -> bool:
    """是否有业务数据（排除空状态）。"""
    return self.get_element_count(self.DATA_ITEM) > 0
```

**用例中的三态断言**：

```python
# 第一层：渲染检测（白屏 vs 已渲染）
is_rendered = page_obj.is_content_rendered()
if not is_rendered:
    assert False, "内容区域未渲染，疑似白屏"

# 第二层（可选）：空数据 vs 有数据
# 根据业务预期决定是否需要进一步区分
if page_obj.has_data_items():
    # 有数据 → 可以进一步验证数据内容
    pass
else:
    # 空数据 → 记录到报告，不视为失败
    allure.attach("该Tab当前无业务数据（空状态）", ...)
```

**⚠️ 陷阱**：

| 错误做法 | 问题 | 正确做法 |
|---------|------|---------|
| `innerText.length > N` 判断白屏 | 空状态提示文案可能很短，被误判为白屏 | `children.length > 0` |
| 空数据等同于失败 | 无收藏/无错题是合理的业务状态 | 白屏才失败，空数据只记录 |
| 只检查容器 `is_visible` | 容器 div 可能存在但子组件未挂载 | JS evaluate 检查子元素 |

**适用场景**：
- 同一容器内切换多个子 Tab，部分 Tab 可能无业务数据
- 异步加载组件可能因接口超时未渲染
- 页面骨架先渲染、内容延迟加载的 SPA 路由
