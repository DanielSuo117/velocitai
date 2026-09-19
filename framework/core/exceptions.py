"""框架异常。

单独定义 ElementLocationError 的理由：拦截器需要回答「这次失败到底是不是
元素定位失败」。只靠捕获 Exception 无法区分「按钮找不到」和「断言不通过」，
而自愈只允许介入前者 —— 介入后者就等于替业务掩盖真实缺陷。
"""


class VelocitaiError(Exception):
    """框架异常基类，便于调用方一次性捕获本框架抛出的所有异常。"""


class ElementLocationError(VelocitaiError):
    """元素定位失败 —— 选择器没能在页面上命中任何元素。

    这是自愈唯一允许介入的失败类型。
    """

    def __init__(self, selector: str, page_object: str = "", constant: str = ""):
        self.selector = selector
        self.page_object = page_object
        self.constant = constant
        where = f"{page_object}.{constant}" if page_object and constant else (page_object or "")
        super().__init__(f"元素定位失败：{selector}" + (f"（{where}）" if where else ""))


class HealingError(VelocitaiError):
    """自愈过程自身出错。

    注意：框架内部一律不向上抛这个异常 —— 自愈是辅助机制，它坏了不该让
    用例失败。定义它只为日志与测试断言时能明确指代这一类问题。
    """
