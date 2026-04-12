#!/usr/bin/env python3
"""
AgentScope Python 版本 Human-in-the-Loop 示例

基于 Java 版本 (agentscope-java/agentscope-examples/hitl-chat) 的 Python 实现
演示核心安全交互机制
"""

import datetime
import random
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum


class ToolStatus(Enum):
    """工具状态"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


@dataclass
class ToolCall:
    """工具调用"""
    name: str
    arguments: Dict[str, Any]
    description: str = ""
    status: ToolStatus = ToolStatus.PENDING
    result: Optional[Any] = None
    
    def __str__(self) -> str:
        args_str = ", ".join(f"{k}={repr(v)}" for k, v in self.arguments.items())
        return f"{self.name}({args_str})"


class ToolConfirmationHook:
    """
    工具确认钩子 - 基于 Java 版本的 ToolConfirmationHook
    
    监控代理的工具调用，对危险工具请求用户确认
    """
    
    def __init__(self, dangerous_tools: Optional[Set[str]] = None):
        self.dangerous_tools = dangerous_tools or set()
        self.execution_history: List[ToolCall] = []
        self.audit_log: List[str] = []
    
    def add_dangerous_tool(self, tool_name: str) -> None:
        """添加危险工具"""
        self.dangerous_tools.add(tool_name)
        self._log(f"Added dangerous tool: {tool_name}")
    
    def remove_dangerous_tool(self, tool_name: str) -> None:
        """移除危险工具"""
        self.dangerous_tools.discard(tool_name)
        self._log(f"Removed dangerous tool: {tool_name}")
    
    def check_tool_call(self, tool_call: ToolCall) -> bool:
        """检查工具调用是否需要确认"""
        return tool_call.name in self.dangerous_tools
    
    def request_confirmation(self, tool_call: ToolCall) -> ToolCall:
        """请求用户确认（核心交互）"""
        print(f"\n{'🔒'*20}")
        print("SECURITY CHECK REQUIRED")
        print(f"{'🔒'*20}")
        print(f"Tool: {tool_call.name}")
        print(f"Arguments: {tool_call.arguments}")
        
        if tool_call.description:
            print(f"Purpose: {tool_call.description}")
        
        risk = self._assess_risk(tool_call)
        print(f"Risk Level: {risk}")
        
        while True:
            print("\nOptions:")
            print("  [y] Yes - Approve and execute")
            print("  [n] No - Reject execution")
            print("  [m] Modify - Change arguments")
            
            choice = input("\nYour choice (y/n/m): ").strip().lower()
            
            if choice in ["y", "yes"]:
                tool_call.status = ToolStatus.APPROVED
                self._log(f"Tool approved: {tool_call}")
                print("✅ Tool approved.")
                return tool_call
            
            elif choice in ["n", "no"]:
                tool_call.status = ToolStatus.REJECTED
                self._log(f"Tool rejected: {tool_call}")
                print("❌ Tool rejected.")
                return tool_call
            
            elif choice in ["m", "modify"]:
                tool_call = self._modify_arguments(tool_call)
                return self.request_confirmation(tool_call)
            
            else:
                print("Invalid choice. Please try again.")
    
    def _modify_arguments(self, tool_call: ToolCall) -> ToolCall:
        """修改工具参数"""
        print(f"\nModifying arguments for {tool_call.name}:")
        new_args = {}
        
        for key, value in tool_call.arguments.items():
            print(f"\nCurrent {key}: {repr(value)}")
            new_value = input(f"New value (press Enter to keep): ").strip()
            
            if new_value:
                try:
                    # 类型转换
                    if isinstance(value, int):
                        new_args[key] = int(new_value)
                    elif isinstance(value, float):
                        new_args[key] = float(new_value)
                    elif isinstance(value, bool):
                        if new_value.lower() in ["true", "yes", "1"]:
                            new_args[key] = True
                        elif new_value.lower() in ["false", "no", "0"]:
                            new_args[key] = False
                        else:
                            new_args[key] = bool(new_value)
                    else:
                        new_args[key] = new_value
                except ValueError:
                    print(f"⚠️  Type conversion failed, keeping original.")
                    new_args[key] = value
            else:
                new_args[key] = value
        
        return ToolCall(
            name=tool_call.name,
            arguments=new_args,
            description=tool_call.description
        )
    
    def _assess_risk(self, tool_call: ToolCall) -> str:
        """评估风险等级"""
        high_risk = {"delete_file", "execute_command", "format_disk"}
        medium_risk = {"send_email", "modify_file", "restart_service"}
        
        if tool_call.name in high_risk:
            return "🔴 HIGH - Can cause data loss"
        elif tool_call.name in medium_risk:
            return "🟡 MEDIUM - Can affect system"
        else:
            return "🟢 LOW - Read-only operations"
    
    def _log(self, message: str):
        """记录日志"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.audit_log.append(f"[{timestamp}] {message}")
    
    def show_audit_log(self):
        """显示审计日志"""
        print(f"\n{'📋'*20}")
        print("AUDIT LOG")
        print(f"{'📋'*20}")
        
        if not self.audit_log:
            print("No audit entries yet.")
            return
        
        for entry in self.audit_log[-10:]:
            print(f"  {entry}")


# 工具函数定义
def get_time() -> str:
    """获取当前时间"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def random_number(min_val: int = 1, max_val: int = 100) -> int:
    """生成随机数"""
    if min_val > max_val:
        raise ValueError("min must be <= max")
    return random.randint(min_val, max_val)


def send_email(to: str, subject: str, body: str) -> str:
    """发送邮件（模拟）"""
    return f"Email sent to {to}: '{subject}'"


def delete_file(filepath: str) -> str:
    """删除文件（模拟）"""
    return f"File '{filepath}' deleted (simulated)"


def list_files(directory: str = ".") -> str:
    """列出文件（模拟）"""
    files = ["README.md", "main.py", "config.yaml", "data.csv"]
    return f"Files in {directory}: {', '.join(files)}"


class HITLAgent:
    """Human-in-the-Loop 代理"""
    
    def __init__(self, name: str = "HITL Assistant"):
        self.name = name
        self.confirmation_hook = ToolConfirmationHook()
        
        # 工具映射
        self.tools = {
            "get_time": get_time,
            "random_number": random_number,
            "send_email": send_email,
            "delete_file": delete_file,
            "list_files": list_files,
        }
        
        # 设置危险工具
        self.confirmation_hook.add_dangerous_tool("send_email")
        self.confirmation_hook.add_dangerous_tool("delete_file")
    
    def process_request(self, user_request: str) -> str:
        """处理用户请求"""
        print(f"\n{'='*60}")
        print(f"User: {user_request}")
        print(f"{'='*60}")
        
        # 生成工具调用
        tool_calls = self._generate_tool_calls(user_request)
        
        if not tool_calls:
            return "I understand your request. No tools needed."
        
        results = []
        for tool_call in tool_calls:
            print(f"\n🔧 Proposed tool: {tool_call}")
            
            # 检查是否需要确认
            if self.confirmation_hook.check_tool_call(tool_call):
                print("⚠️  This tool requires human confirmation.")
                confirmed_call = self.confirmation_hook.request_confirmation(tool_call)
                
                if confirmed_call.status == ToolStatus.APPROVED:
                    result = self._execute_tool(confirmed_call)
                    results.append(f"{confirmed_call.name}: {result}")
                    self.confirmation_hook.execution_history.append(confirmed_call)
                else:
                    results.append(f"{confirmed_call.name}: {confirmed_call.status.value}")
            else:
                result = self._execute_tool(tool_call)
                results.append(f"{tool_call.name}: {result}")
                tool_call.status = ToolStatus.EXECUTED
                tool_call.result = result
                self.confirmation_hook.execution_history.append(tool_call)
        
        # 生成回复
        if results:
            response = "I've processed your request:\n" + "\n".join(f"• {r}" for r in results)
        else:
            response = "Request processed successfully."
        
        return response
    
    def _generate_tool_calls(self, request: str) -> List[ToolCall]:
        """根据请求生成工具调用"""
        request_lower = request.lower()
        tool_calls = []
        
        # 规则匹配
        if any(word in request_lower for word in ["time", "current", "now"]):
            tool_calls.append(ToolCall("get_time", {}, "Get current time"))
        
        if any(word in request_lower for word in ["random", "number", "generate"]):
            tool_calls.append(ToolCall(
                "random_number",
                {"min_val": 1, "max_val": 100},
                "Generate random number"
            ))
        
        if any(word in request_lower for word in ["email", "send", "mail"]):
            tool_calls.append(ToolCall(
                "send_email",
                {"to": "recipient@example.com", "subject": "AI Generated", "body": "Hello!"},
                "Send an email"
            ))
        
        if any(word in request_lower for word in ["delete", "remove", "erase"]):
            tool_calls.append(ToolCall(
                "delete_file",
                {"filepath": "/tmp/temp_file.txt"},
                "Delete a file"
            ))
        
        if any(word in request_lower for word in ["list", "files", "directory"]):
            tool_calls.append(ToolCall(
                "list_files",
                {"directory": "."},
                "List directory contents"
            ))
        
        return tool_calls
    
    def _execute_tool(self, tool_call: ToolCall) -> Any:
        """执行工具"""
        tool_func = self.tools.get(tool_call.name)
        if not tool_func:
            return f"Error: Tool '{tool_call.name}' not found"
        
        try:
            result = tool_func(**tool_call.arguments)
            tool_call.result = result
            tool_call.status = ToolStatus.EXECUTED
            return result
        except Exception as e:
            return f"Error: {str(e)}"
    
    def show_tool_info(self):
        """显示工具信息"""
        print(f"\n{'🛠️'*20}")
        print("AVAILABLE TOOLS")
        print(f"{'🛠️'*20}")
        
        for tool_name in self.tools.keys():
            is_dangerous = tool_name in self.confirmation_hook.dangerous_tools
            danger_marker = "🔒" if is_dangerous else "✅"
            print(f"{danger_marker} {tool_name}")


def main():
    """主函数"""
    print("="*70)
    print("AGENTSCOPE HITL EXAMPLE - Python Version")
    print("Based on Java implementation")
    print("="*70)
    
    # 创建代理
    agent = HITLAgent("Security Assistant")
    
    # 显示工具信息
    agent.show_tool_info()
    
    print("\n" + "="*70)
    print("Try these commands:")
    print("  • What time is it?")
    print("  • Generate a random number")
    print("  • Send an email to my boss")
    print("  • Delete the temporary file")
    print("  • List files in current directory")
    print("  • Type 'log' to show audit log")
    print("  • Type 'quit' to exit")
    print("="*70)
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye! 👋")
                break
            
            if user_input.lower() in ["log", "audit"]:
                agent.confirmation_hook.show_audit_log()
                continue
            
            if not user_input:
                continue
            
            # 处理请求
            response = agent.process_request(user_input)
            print(f"\n🤖 {agent.name}: {response}")
            
        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()