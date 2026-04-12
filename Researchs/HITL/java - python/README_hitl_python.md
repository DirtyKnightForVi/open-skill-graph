# AgentScope Python Human-in-the-Loop 示例

基于 Java 版本 `agentscope-java/agentscope-examples/hitl-chat` 的 Python 实现。

## 📋 概述

这个示例演示了如何在 AgentScope Python 版本中实现 human-in-the-loop 安全交互，基于 Java 版本的核心概念：

- **危险工具检测和确认**：监控代理的工具调用，对危险操作请求用户确认
- **用户交互式审批**：提供 approve/reject/modify 选项
- **审计日志**：记录所有工具调用和用户决策
- **参数修改**：允许用户在批准前修改工具参数

## 🏗️ 架构设计

### 核心组件

1. **ToolConfirmationHook** - 安全钩子
   - 基于 Java 版本的 `ToolConfirmationHook.java`
   - 监控工具调用，对危险工具暂停执行
   - 请求用户确认

2. **ToolCall** - 工具调用对象
   - 封装工具名称、参数、状态
   - 支持 PENDING/APPROVED/REJECTED/EXECUTED 状态

3. **HITLAgent** - 人机交互代理
   - 集成安全钩子
   - 处理用户请求
   - 管理工具执行流程

### 与 Java 版本的对应关系

| Java 组件 | Python 组件 | 功能 |
|-----------|-------------|------|
| `ToolConfirmationHook.java` | `ToolConfirmationHook` | 危险工具检测和确认 |
| `BuiltinTools.java` | 工具函数 (`get_time`, `random_number`, etc.) | 内置工具实现 |
| `HitlChatApplication.java` | `main()` 函数 | 应用入口和演示 |
| Spring Boot 配置 | 交互式命令行界面 | 用户交互方式 |

## 🚀 快速开始

### 运行示例

```bash
# 直接运行 Python 脚本
python hitl_python_example.py
```

### 示例交互

```
AGENTSCOPE HITL EXAMPLE - Python Version
Based on Java implementation
======================================================================

🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️
AVAILABLE TOOLS
🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️🛠️
✅ get_time
✅ random_number
🔒 send_email
🔒 delete_file
✅ list_files

======================================================================
Try these commands:
  • What time is it?
  • Generate a random number
  • Send an email to my boss
  • Delete the temporary file
  • List files in current directory
  • Type 'log' to show audit log
  • Type 'quit' to exit
======================================================================

You: Send an email to my boss

======================================================================
User: Send an email to my boss
======================================================================

🔧 Proposed tool: send_email(to='recipient@example.com', subject='AI Generated', body='Hello!')
⚠️  This tool requires human confirmation.

🔒🔒🔒🔒🔒🔒🔒🔒🔒🔒🔒🔒🔒🔒🔒🔒🔒🔒🔒🔒
SECURITY CHECK REQUIRED
🔒🔒🔒🔒🔒🔒🔒🔒🔒🔒🔒🔒🔒🔒🔒🔒🔒🔒🔒🔒
Tool: send_email
Arguments: {'to': 'recipient@example.com', 'subject': 'AI Generated', 'body': 'Hello!'}
Purpose: Send an email
Risk Level: 🟡 MEDIUM - Can affect system

Options:
  [y] Yes - Approve and execute
  [n] No - Reject execution
  [m] Modify - Change arguments

Your choice (y/n/m): y
✅ Tool approved.

🤖 Security Assistant: I've processed your request:
• send_email: Email sent to recipient@example.com: 'AI Generated'
```

## 🔧 工具定义

### 安全工具（无需确认）
- `get_time()` - 获取当前时间
- `random_number(min_val, max_val)` - 生成随机数
- `list_files(directory)` - 列出文件

### 危险工具（需要确认）
- `send_email(to, subject, body)` - 发送邮件
- `delete_file(filepath)` - 删除文件

## 🛡️ 安全特性

### 1. 风险等级评估
```python
def _assess_risk(self, tool_call: ToolCall) -> str:
    high_risk = {"delete_file", "execute_command", "format_disk"}
    medium_risk = {"send_email", "modify_file", "restart_service"}
    
    if tool_call.name in high_risk:
        return "🔴 HIGH - Can cause data loss"
    elif tool_call.name in medium_risk:
        return "🟡 MEDIUM - Can affect system"
    else:
        return "🟢 LOW - Read-only operations"
```

### 2. 参数修改
用户可以在批准前修改工具参数：
```
Modifying arguments for send_email:

Current to: 'recipient@example.com'
New value (press Enter to keep): boss@company.com

Current subject: 'AI Generated'
New value (press Enter to keep): Important Update

Current body: 'Hello!'
New value (press Enter to keep): 
```

### 3. 审计日志
所有工具调用和用户决策都被记录：
```
📋📋📋📋📋📋📋📋📋📋📋📋📋📋📋📋📋📋📋📋
AUDIT LOG
📋📋📋📋📋📋📋📋📋📋📋📋📋📋📋📋📋📋📋📋
  [14:30:15] Added dangerous tool: send_email
  [14:30:15] Added dangerous tool: delete_file
  [14:30:22] Tool approved: send_email(to='boss@company.com', subject='Important Update', body='Hello!')
```

## 📁 文件说明

- `hitl_python_example.py` - 主示例文件
- `agentscope_hitl_example.py` - 完整 AgentScope 集成版本
- `hitl_simple_example.py` - 简化演示版本
- `README_hitl_python.md` - 本文档

## 🔄 与 Java 版本的差异

| 特性 | Java 版本 | Python 版本 |
|------|-----------|-------------|
| 框架 | Spring Boot + AgentScope Java | 纯 Python + 交互式 CLI |
| 用户界面 | Web 界面 (HTTP API) | 命令行界面 |
| 钩子机制 | `Hook` 接口 + `PostReasoningEvent` | 自定义 `ToolConfirmationHook` |
| 工具定义 | `@Tool` 注解 | Python 函数 + 装饰器 |
| 配置方式 | YAML/Properties 文件 | Python 代码配置 |

## 🎯 核心实现要点

### 1. 工具确认流程
```python
def request_confirmation(self, tool_call: ToolCall) -> ToolCall:
    # 显示安全警告
    print("SECURITY CHECK REQUIRED")
    
    # 显示工具信息
    print(f"Tool: {tool_call.name}")
    print(f"Arguments: {tool_call.arguments}")
    
    # 用户选择
    choice = input("Your choice (y/n/m): ")
    
    if choice == "y":
        tool_call.status = ToolStatus.APPROVED
    elif choice == "n":
        tool_call.status = ToolStatus.REJECTED
    elif choice == "m":
        tool_call = self._modify_arguments(tool_call)
    
    return tool_call
```

### 2. 与 AgentScope 集成
```python
# 在实际 AgentScope 中使用
from agentscope.hooks import HookBase, HookEvent

class ToolConfirmationHook(HookBase):
    async def on_event(self, event: HookEvent) -> HookEvent:
        if isinstance(event, PostReasoningEvent):
            # 检查危险工具
            if self._has_dangerous_tools(event):
                event.should_stop = True  # 暂停代理
        return event
```

## 📚 扩展建议

### 1. 集成真实 AgentScope
```python
from agentscope.agents import AgentBase
from agentscope.models import OpenAIChatWrapper
from agentscope.tools import tool

@tool
def get_time() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class HITLAgent(AgentBase):
    def __init__(self, name, model):
        super().__init__(name=name, model=model)
        self.confirmation_hook = ToolConfirmationHook()
```

### 2. 添加更多工具类型
- 文件操作工具
- 网络请求工具
- 数据库操作工具
- 系统命令工具

### 3. 增强安全特性
- 基于角色的权限控制
- 时间限制的工具执行
- 操作回滚机制
- 多因素认证

## 🎨 设计模式

这个示例展示了以下设计模式：

1. **Hook Pattern** - 工具确认钩子
2. **Command Pattern** - 工具调用封装
3. **Observer Pattern** - 审计日志记录
4. **Strategy Pattern** - 风险评估策略

## 📞 支持

如需将示例集成到实际 AgentScope 项目中，请参考：
- [AgentScope Python 文档](https://github.com/modelscope/agentscope)
- [AgentScope Java 示例](https://github.com/agentscope-ai/agentscope-java/tree/main/agentscope-examples/hitl-chat)

## 📄 许可证

基于 Apache 2.0 许可证，与 AgentScope 项目保持一致。