from .bases import ServiceError


class SandboxError(ServiceError):
    """ 沙箱异常 """
    pass


class SandBoxRunCommendError(SandboxError):
    """ 沙箱执行命令异常 """
    pass