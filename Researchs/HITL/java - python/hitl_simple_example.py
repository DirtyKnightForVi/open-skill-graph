#!/usr/bin/env python3
"""
AgentScope Python 版本 Human-in-the-Loop 简化示例

基于 Java 版本的简化实现，演示核心概念：
1. 危险工具检测和确认
2. 用户交互式审批
3. 工具执行控制
"""

import datetime
import random
from typing import Dict, Any, List, Optional
from enum import Enum


class ToolStatus(Enum):
    """工具状态枚举"""
    PENDING = "pending"      # 等待确认
    APPROVED = "approved"    # 已批准
    REJECTED = "rejected"    # 已拒绝
    EXECUTED = "executed"    # 已执行


class ToolCall:
    """工具调用类"""
    
    def __init__(self, name: str, arguments: Dict[str, Any], description: str = ""):
        self.name = name
        self.arguments = arguments
        self.description = description
        self.status = ToolStatus.PENDING
        self.result = None
    
    def __str__(self) -> str:
        args_str = ", ".join(f"{k}={v}" for k, v in self.arguments.items())
        return f"{self.name}({args_str}) - {self.status.value}"


class ToolConfirmationSystem:
    """工具确认系统 - 核心安全机制"""
    
    def __init__(self, dangerous_tools: Optional[List[str]] = None):
        self.dangerous_tools = set(dangerous_tools or [])
        self.pending_tool_calls: List[ToolCall] = []
        self.execution_history: List[ToolCall] = []
    
    def add_dangerous_tool(self, tool_name: str) -> None:
        """添加危险工具"""
        self.dangerous_tools.add(tool_name)
        print(f"⚠️  Added dangerous tool: {tool_name}")
    
    def remove_dangerous_tool(self, tool_name: str) -> None:
        """移除危险工具"""
        self.dangerous_tools.discard(tool_name)
        print(f"✅  Removed dangerous tool: {tool_name}")
    
    def check_tool_call(self, tool_call: ToolCall) -> bool:
        """检查工具调用是否需要确认"""
        return tool_call.name in self.dangerous_tools
    
    def request_confirmation(self, tool_call: ToolCall) -> ToolCall:
        """请求用户确认"""
        print(f"\n🔒 SECURITY ALERT: Dangerous tool detected!")
        print(f"   Tool: {tool_call.name}")
        print(f"   Arguments: {tool_call.arguments}")
        print(f"   Description: {tool_call.description}")
        
        while True:
            response = input("\nDo you approve this tool execution? (yes/no/modify): ").strip().lower()
            
            if response in ["yes", "y", "approve", "确认"]:
                tool_call.status = ToolStatus.APPROVED
                print("✅ Tool approved for execution.")
                return tool_call
            
            elif response in ["no", "n", "reject", "拒绝"]:
                tool_call.status = ToolStatus.REJECTED
                print("❌ Tool execution rejected.")
                return tool_call
            
            elif response in ["modify", "m", "edit", "修改"]:
                modified_args = self._modify_arguments(tool_call)
                tool_call.arguments = modified_args
                print("📝 Arguments modified. Re-checking...")
                # 重新检查修改后的工具调用
                return self.request_confirmation(tool_call)
            
            else:
                print("Please enter 'yes', 'no', or 'modify'.")
    
    def _modify_arguments(self, tool_call: ToolCall) -> Dict[str, Any]:
        """修改工具参数"""
        print(f"\nCurrent arguments: {tool_call.arguments}")
        modified_args = tool_call.arguments.copy()
        
        for key, value in list(modified_args.items()):
            new_value = input(f"Modify {key} (current: {value}) [Enter to keep]: ").strip()
            if new_value:
                # 简单类型转换
                if isinstance(value, int):
                    try:
                        modified_args[key] = int(new_value)
                    except ValueError:
                        print(f"Invalid integer, keeping original value: {value}")
                elif isinstance(value, float):
                    try:
                        modified_args[key] = float(new_value)
                    except ValueError:
                        print(f"Invalid float, keeping original value: {value}")
                else:
                    modified_args[key] = new_value
        
        return modified_args
    
    def execute_tool(self, tool_call: ToolCall) -> Any:
        """执行工具调用"""
        if tool_call.status != ToolStatus.APPROVED:
            return f"Cannot execute {tool_call.name}: Status is {tool_call.status.value}"
        
        # 模拟工具执行
        if tool_call.name == "get_time":
            now = datetime.datetime.now()
            result = now.strftime("%Y-%m-%d %H:%M:%S")
        
        elif tool_call.name == "random_number":
            min_val = tool_call.arguments.get("min", 1)
            max_val = tool_call.arguments.get("max", 100)
            result = random.randint(min_val, max_val)
        
        elif tool_call.name == "send_email":
            to = tool_call.arguments.get("to", "unknown@example.com")
            subject = tool_call.arguments.get("subject", "No Subject")
            result = f"Email sent to {to}: '{subject}'"
        
        elif tool_call.name == "delete_file":
            filepath = tool_call.arguments.get("filepath", "unknown.txt")
            result = f"File '{filepath}' deleted (simulated)"
        
        else:
            result = f"Unknown tool: {tool_call.name}"
        
        tool_call.result = result
        tool_call.status = ToolStatus.EXECUTED
        self.execution_history.append(tool_call)
        
        return result


class HITLAgent:
    """Human-in-the-Loop 代理"""
    
    def __init__(self, name: str = "HITL Assistant"):
        self.name = name
        self.confirmation_system = ToolConfirmationSystem()
        
        # 默认危险工具
        self.confirmation_system.add_dangerous_tool("send_email")
        self.confirmation_system.add_dangerous_tool("delete_file")
        self.confirmation_system.add_dangerous_tool("execute_command")
    
    def process_request(self, user_request: str) -> str:
        """处理用户请求"""
        print(f"\n{'='*60}")
        print(f"Processing request: {user_request}")
        print(f"{'='*60}")
        
        # 模拟 AI 推理，生成工具调用
        tool_calls = self._simulate_ai_reasoning(user_request)
        
        results = []
        for tool_call in tool_calls:
            print(f"\n🔧 Tool call generated: {tool_call}")
            
            # 检查是否需要确认
            if self.confirmation_system.check_tool_call(tool_call):
                print("🔒 This tool requires human confirmation.")
                confirmed_call = self.confirmation_system.request_confirmation(tool_call)
                
                if confirmed_call.status == ToolStatus.APPROVED:
                    result = self.confirmation_system.execute_tool(confirmed_call)
                    results.append(f"{tool_call.name}: {result}")
                else:
                    results.append(f"{tool_call.name}: {confirmed_call.status.value}")
            else:
                # 安全工具直接执行
                result = self.confirmation_system.execute_tool(tool_call)
                results.append(f"{tool_call.name}: {result}")
        
        # 生成最终回复
        if results:
            response = f"I've processed your request. Results:\n" + "\n".join(f"  • {r}" for r in results)
        else:
            response = "I understand your request, but no tools were needed."
        
        return response
    
    def _simulate_ai_reasoning(self, request: str) -> List[ToolCall]:
        """模拟 AI 推理生成工具调用"""
        request_lower = request.lower()
        tool_calls = []
        
        if "time" in request_lower or "current" in request_lower:
            tool_calls.append(ToolCall("get_time", {}, "Get current time"))
        
        if "random" in request_lower or "number" in request_lower:
            tool_calls.append(ToolCall("random_number", {"min": 1, "max": 100}, "Generate random number"))
        
        if "email" in request_lower or "send" in request_lower:
            tool_calls.append(ToolCall(
                "send_email",
                {"to": "user@example.com", "subject": "AI Generated Email", "body": "Hello from AI!"},
                "Send an email"
            ))
        
        if "delete" in request_lower or "remove" in request_lower:
            tool_calls.append(ToolCall(
                "delete_file",
                {"filepath": "/tmp/important.txt"},
                "Delete a file"
            ))
        
        return tool_calls
    
    def show_security_log(self):
        """显示安全日志"""
        print(f"\n{'='*60}")
        print("SECURITY LOG - Tool Execution History")
        print(f"{'='*60}")
        
        if not self.confirmation_system.execution_history:
            print("No tools executed yet.")
            return
        
        for i, tool_call in enumerate(self.confirmation_system.execution_history, 1):
            print(f"{i}. {tool_call}")
            if tool_call.result:
                print(f"   Result: {tool_call.result}")
            print()


def main():
    """主函数 - 演示 HITL 功能"""
    print("=== AgentScope Python HITL Demo ===")
    print("基于 Java 版本的简化 Python 实现")
    print()
    
    # 创建代理
    agent = HITLAgent("Security Assistant")
    
    # 演示用例
    demo_requests = [
        "What time is it?",
        "Generate a random number for me",
        "Send an email to my boss",
        "Delete the temporary file",
        "Tell me a joke (no tools needed)"
    ]
    
    print("Demo scenarios:")
    for i, request in enumerate(demo_requests, 1):
        print(f"  {i}. {request}")
    
    print("\n" + "="*60)
    
    # 运行演示
    for request in demo_requests:
        response = agent.process_request(request)
        print(f"\n🤖 Assistant: {response}")
        print(f"{'-'*60}")
    
    # 显示安全日志
    agent.show_security_log()
    
    # 交互模式
    print("\n" + "="*60)
    print("Interactive Mode (type 'quit' to exit)")
    print("="*60)
    
    while True:
        user_input = input("\nYour request: ").strip()
        
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        
        if not user_input:
            continue
        
        response = agent.process_request(user_input)
        print(f"\n🤖 Assistant: {response}")
        
        # 可选：显示日志
        show_log = input("\nShow security log? (y/n): ").strip().lower()
        if show_log in ["y", "yes"]:
            agent.show_security_log()


if __name__ == "__main__":
    main()