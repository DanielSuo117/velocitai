"""业务页面对象层。

这里只放具体页面的 PageObject，一律继承 core.base.BasePage：

    from core.base.base_page import BasePage

    class LoginPage(BasePage):
        USERNAME = "#username"   # P0: 用户名输入框
        ...

跨页面复用的导航栏、弹窗、表格放 components/，继承 BaseComponent，页面对象
通过组合持有它们。

框架能力（基类、自愈、日志、异常）在 core/ —— 写登录页的人不该在这个目录
里读到自愈引擎。
"""
