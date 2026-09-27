"""可复用 UI 组件层 —— 跨页面出现的导航栏、弹窗、表格、分页器放这里。

组件一律继承 ``core.base.base_component.BaseComponent`` 并传入 ``root``
选择器，组件内所有定位自动限制在 root 之内；页面对象通过组合持有组件，
不要把组件方法复制进页面类。

文件命名：``<snake_name>_component.py``，类名 ``<Name>Component``。
"""
