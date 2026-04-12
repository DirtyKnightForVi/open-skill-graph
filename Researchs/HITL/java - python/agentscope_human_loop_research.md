# AgentScope Human-in-the-Loop 安全交互实现调研报告

## 概述

AgentScope 是一个生产级的多智能体框架，内置了 **human-in-the-loop (HITL)** 功能，允许在关键决策点引入人类监督和干预，实现安全的人机协作。

---

## 1. 核心实现方式

### 1.1 UserAgent - 基础人机交互组件

AgentScope 提供了内置的 `UserAgent` 类，专门用于处理人机循环交互。

**关键文件：**
- `src/agentscope/agent/_user_agent.py` - 用户代理实现
- `src/agentscope/agent/_user_input.py` - 用户输入处理（415行，支持多种输入模式）

**基本用法：**

```python
from agentscope.agents import UserAgent
from agentscope.msghub import msghub

# 创建用户代理
user = UserAgent(
    name="User",
    require_approval=True,  # 启用审批模式
)

# 在对话循环中使用
with msghub(participants=[agent1, agent2, user]) as hub:
    # 用户可以在关键节点介入
    user_response = user()
```

### 1.2 通过 Hooks 实现工具审批

AgentScope 提供了 hooks 机制，用于在工具执行前后插入安全检查。

**关键文件：**
- `src/agentscope/hooks/_studio_hooks.py` - Studio 环境下的 hook 实现

**设计模式（来自 GitHub Issue #926）：**

```python
# 预处理函数设计
preprocessing_function(tool_call: ToolUseBlock) -> Tuple[
    ToolUseBlock | None,  # 修改后的工具调用（可选）
    bool,                  # 是否执行工具
    ToolResultBlock | None # 自定义返回结果（用于拒绝情况）
]:

# 使用示例
def user_approval_hook(tool_call):
    # 显示工具调用信息给用户
    print(f"Agent 请求执行: {tool_call.name}")
    print(f"参数: {tool_call.arguments}")
    
    # 获取用户确认
    user_input = input("批准执行? (yes/no/modify): ")
    
    if user_input.lower() == "yes":
        return (None, True, None)  # 继续执行
    elif user_input.lower() == "no":
        return (None, False, ToolResultBlock(
            content="用户拒绝了该操作"
        ))
    else:
        # 修改参数
        modified_call = modify_parameters(tool_call)
        return (modified_call, True, None)
```

---

## 2. 安全交互实现方案

### 2.1 方案一：CLI 环境下的确认机制

```python
import agentscope
from agentscope.agents import ReActAgent, UserAgent
from agentscope.tools import Tools

def safe_tool_execution(agent, tools):
    """带用户确认的 ReAct Agent"""
    
    class SafeReActAgent(ReActAgent):
        def _acting(self, *args, **kwargs):
            # 在工具执行前暂停获取用户确认
            tool_calls = self.get_tool_calls()
            
            for tool_call in tool_calls:
                print(f"\n[安全检查] Agent 准备执行:")
                print(f"  工具: {tool_call.name}")
                print(f"  参数: {tool_call.arguments}")
                
                approval = input("批准执行? (y/n/m/M - 修改): ").lower()
                
                if approval == 'n':
                    # 拒绝执行
                    return self.create_refusal_message(tool_call)
                elif approval == 'm':
                    # 修改参数
                    tool_call = self.modify_tool_call(tool_call)
                elif approval == 'M':
                    # 完全修改
                    tool_call = self.manual_tool_call()
            
            return super()._acting(*args, **kwargs)
    
    return SafeReActAgent(agent, tools)
```

### 2.2 方案二：ReAct Agent 的 pre_action_hook

```python
from agentscope.agents import ReActAgent
from agentscope.hooks import PreActionHook

class ApprovalHook(PreActionHook):
    """工具执行前的审批 Hook"""
    
    def __call__(self, action_context):
        tool_name = action_context.tool_name
        tool_args = action_context.arguments
        
        # 高风险工具列表
        high_risk_tools = ['execute_shell', 'delete_file', 'send_email']
        
        if tool_name in high_risk_tools:
            # 强制用户确认
            print(f"\n⚠️  高风险操作请求: {tool_name}")
            print(f"参数: {tool_args}")
            
            confirm = input("确认执行? (yes/no): ")
            if confirm != "yes":
                # 取消执行，返回错误信息给 Agent
                action_context.cancel(
                    reason="用户拒绝了高风险操作"
                )
                return False
        
        return True

# 使用 Hook
agent = ReActAgent(
    name="SafeAgent",
    model=model,
    tools=tools,
    hooks=[ApprovalHook()]  # 注册审批 hook
)
```

### 2.3 方案三：基于 MsgHub 的多 Agent + 人工监督

```python
from agentscope.msghub import msghub
from agentscope.agents import DialogAgent, UserAgent
from agentscope.message import Msg

# 创建监督者代理
supervisor = UserAgent(
    name="Supervisor",
    role="安全监督员",
)

# 创建工作代理
worker = DialogAgent(
    name="Worker",
    model=model,
    tools=tools,
)

# 在消息中心中协作
with msghub(participants=[worker, supervisor]) as hub:
    # 正常对话流程
    msg = Msg("User", "帮我分析这个数据集")
    hub.broadcast(msg)
    
    # 当 Agent 执行敏感操作时，可以在 supervisor 节点暂停
    # 等待人工确认后再继续
```

---

## 3. 高级安全策略

### 3.1 黑名单/白名单机制

```python
class ToolAccessControl:
    """工具访问控制 - 基于 GitHub Issue #926 讨论"""
    
    def __init__(self):
        self.blacklist = ['execute_shell', 'rm', 'eval']
        self.whitelist = ['search', 'calculator', 'read_file']
        self.require_approval = ['write_file', 'send_request']
    
    def check_permission(self, tool_call):
        tool_name = tool_call.name
        
        # 黑名单检查
        if tool_name in self.blacklist:
            return False, "该工具已被禁用"
        
        # 白名单模式（可选）
        # if tool_name not in self.whitelist:
        #     return False, "工具不在白名单中"
        
        # 需要审批的工具
        if tool_name in self.require_approval:
            return self.get_user_approval(tool_call)
        
        return True, None
    
    def get_user_approval(self, tool_call):
        """获取用户明确批准"""
        print(f"\n需要审批的工具调用:")
        print(f"  工具: {tool_call.name}")
        print(f"  参数: {tool_call.arguments}")
        
        response = input("\n[approve/modify/reject]: ").lower()
        
        if response == "approve":
            return True, None
        elif response == "modify":
            # 允许用户修改参数
            new_args = self.modify_interactively(tool_call.arguments)
            tool_call.arguments = new_args
            return True, None
        else:
            return False, "用户拒绝了操作"
```

### 3.2 沙箱执行环境

```python
import subprocess
from agentscope.tools import tool

@tool
def safe_execute(command: str) -> str:
    """
    在沙箱环境中安全执行命令
    带有资源限制和超时控制
    """
    # 1. 命令白名单检查
    allowed_commands = ['ls', 'cat', 'grep', 'wc', 'head', 'tail']
    cmd_base = command.split()[0]
    
    if cmd_base not in allowed_commands:
        return f"错误: 命令 '{cmd_base}' 不在允许列表中"
    
    # 2. 危险模式检查
    dangerous_patterns = [';', '&&', '||', '|', '`', '$', '>', '<']
    if any(p in command for p in dangerous_patterns):
        return "错误: 检测到危险的命令模式"
    
    # 3. 用户确认（高风险命令）
    if cmd_base in ['rm', 'mv', 'cp']:
        confirm = input(f"确认执行: {command}? (yes/no): ")
        if confirm != "yes":
            return "操作被用户取消"
    
    # 4. 在受限环境中执行
    try:
        result = subprocess.run(
            command,
            shell=False,  # 不使用 shell 解析
            timeout=30,   # 超时限制
            capture_output=True,
            text=True,
            cwd="/tmp",   # 限制工作目录
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return "错误: 命令执行超时"
    except Exception as e:
        return f"错误: {str(e)}"
```

---

## 4. Web/Studio 环境实现

### 4.1 Studio 模式下的异步确认

```python
from agentscope.hooks import StudioHooks
import asyncio

class AsyncApprovalManager:
    """
    适用于 Web/Studio 环境的异步批准管理器
    """
    
    def __init__(self):
        self.pending_approvals = {}
    
    async def request_approval(self, tool_call, session_id):
        """发送批准请求到前端"""
        approval_id = generate_id()
        
        # 存储待审批状态
        self.pending_approvals[approval_id] = {
            'tool_call': tool_call,
            'status': 'pending',  # pending/approved/rejected
            'session_id': session_id,
            'event': asyncio.Event()
        }
        
        # 发送 WebSocket 消息到前端
        await self.send_to_frontend({
            'type': 'approval_request',
            'approval_id': approval_id,
            'tool_name': tool_call.name,
            'arguments': tool_call.arguments,
        })
        
        # 等待用户响应（异步）
        await self.pending_approvals[approval_id]['event'].wait()
        
        # 返回结果
        result = self.pending_approvals[approval_id]
        del self.pending_approvals[approval_id]
        
        return result['status'] == 'approved', result.get('modified_args')
    
    async def handle_user_response(self, approval_id, action, modified_args=None):
        """处理前端返回的用户决定"""
        if approval_id in self.pending_approvals:
            pending = self.pending_approvals[approval_id]
            
            if action == 'approve':
                pending['status'] = 'approved'
                pending['modified_args'] = modified_args
            elif action == 'reject':
                pending['status'] = 'rejected'
            
            # 唤醒等待的协程
            pending['event'].set()
```

### 4.2 CoPaw 集成模式（企业级）

AgentScope 的 CoPaw 项目展示了企业级多 Agent 系统中 HITL 的完整实现：

```python
# CoPaw 的高级批准模式
class CoPawApprovalFlow:
    """
    企业级审批流程：
    1. 飞书/钉钉/企微集成
    2. 多级审批
    3. 审计日志
    """
    
    async def execute_with_approval(self, tool_call, context):
        # 1. 创建审批工单
        ticket_id = await self.create_ticket(tool_call, context)
        
        # 2. 发送到 IM 平台
        await self.send_approval_card(
            platform='feishu',
            ticket_id=ticket_id,
            approvers=self.get_approvers(context),
            timeout=3600  # 1小时超时
        )
        
        # 3. 等待审批结果
        result = await self.wait_for_approval(ticket_id)
        
        # 4. 记录审计日志
        await self.log_audit(context, tool_call, result)
        
        return result
```

---

## 5. 最佳实践总结

| 场景 | 推荐方案 | 安全级别 |
|------|---------|---------|
| 本地 CLI 开发 | `UserAgent` + `input()` | ⭐⭐⭐ |
| 个人项目 | `pre_action_hook` 自定义 | ⭐⭐⭐⭐ |
| 共享 Web 应用 | Studio Hooks + 异步确认 | ⭐⭐⭐⭐ |
| 企业生产环境 | CoPaw 多级审批 + 审计 | ⭐⭐⭐⭐⭐ |

### 关键安全原则

1. **最小权限原则**：只给 Agent 访问必要资源的权限
2. **明确确认**：所有不可逆/高风险操作必须用户确认
3. **白名单优先**：默认拒绝未知工具，显式允许可信工具
4. **审计追踪**：记录所有 HITL 交互用于事后审计
5. **超时控制**：避免无限等待用户输入导致系统挂起

---

## 参考资源

- **GitHub Issue #926**: [Feature: human in loop wanted](https://github.com/agentscope-ai/agentscope/issues/926)
  - 详细讨论了 preprocessing_function 设计方案
  
- **GitHub Issue #466**: [Bug: Fail to continue Human-in-the-Loop](https://github.com/agentscope-ai/agentscope/issues/466)
  - 用户确认和 Agent 恢复执行的实现细节
  
- **关键源码文件**:
  - `src/agentscope/agent/_user_agent.py` (128行)
  - `src/agentscope/agent/_user_input.py` (415行)  
  - `src/agentscope/hooks/_studio_hooks.py` (58行)

- **示例代码**:
  - `examples/workflows/multiagent_conversation/`

---

*调研完成时间: 2025年*
