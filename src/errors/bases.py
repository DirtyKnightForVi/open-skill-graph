class SkillScopeError(Exception):
    pass


class ServiceError(SkillScopeError):
    """ 服务内部报错, 报错内容不应返回到前端 """
    pass