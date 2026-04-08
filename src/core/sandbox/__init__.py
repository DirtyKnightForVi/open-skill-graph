# -*- coding: utf-8 -*-
"""
沙箱环境相关模块
"""
import importlib
import pkgutil

from agentscope_runtime.sandbox import BaseSandbox


def register_custom_sandbox():
    """ 注册自定义沙箱 """
    subclasses = []
    # 遍历当前包中的所有模块
    package_name = __name__  # 当前包名
    for _, module_name, _ in pkgutil.walk_packages(__path__, package_name + '.'):
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            import traceback
            print(traceback.format_exc())
            continue
        # 遍历模块中的所有属性，寻找 BaseSandbox 的子类
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, BaseSandbox) and attr is not BaseSandbox:
                subclasses.append(attr)

    return subclasses
