#!/usr/bin/env python3
"""
AgentScope Python 版本 Human-in-the-Loop 示例

基于 Java 版本 (agentscope-java/agentscope-examples/hitl-chat) 的 Python 实现
演示如何使用 AgentScope 实现 human-in-the-loop 安全交互

主要功能：
1. 危险工具确认机制
2. 用户交互式确认
3. 内置工具示例
4. 安全钩子实现
"""

import asyncio
import datetime
import random
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass

from agentscope.agents import AgentBase
from agentscope.message import Msg
from agentscope.models import OpenAIChatWrapper
from agentscope.pipelines import SequentialPipeline
from agentscope.hooks import HookBase, HookEvent, PostReasoningEvent
from agentscope.tools import Tool, ToolResult


@dataclass
class ToolUseBlock:
    """工具调用块"""
    name: str
    arguments: Dict[str, Any]
    description: str = ""


class ToolConfirmationHook(HookBase):
    """
    危险工具确认钩子
    
    监控代理的推理输出，如果检测到危险工具调用，则暂停代理执行等待用户确认
    基于 Java 版本的 ToolConfirmationHook 实现
    """
    
    def __init__(self, dangerous_tools: Optional[Set[str]] = None):
        super().__init__()
        self.dangerous_tools = dangerous_tools or set()
    
    def add_dangerous_tool(self, tool_name: str) -> None:
        """添加危险工具"""
        self.dangerous_tools.add(tool_name)
    
    def remove_dangerous_tool(self, tool_name: str) -> None:
        """移除危险工具"""
        self.dangerous_tools.discard(tool_name)
    
    def set_dangerous_tools(self, tool_names: Set[str]) -> None:
        """设置危险工具列表"""
        self.dangerous_tools = tool_names.copy()
    
    def get_dangerous_tools(self) -> Set[str]:
        """获取危险工具列表"""
        return self.dangerous_tools.copy()
    
    def is_dangerous(self, tool_name: str) -> bool:
        """检查工具是否危险"""
        return tool_name in self.dangerous_tools
    
    async def on_event(self, event: HookEvent) -> HookEvent:
        """处理钩子事件"""
        if isinstance(event, PostReasoningEvent):
            reasoning_msg = event.reasoning_message
            if not reasoning_msg:
                return event
            
            # 检查是否有危险工具调用
            # 注意：这里简化了工具调用检测，实际实现需要解析消息内容
            tool_calls = self._extract_tool_calls(reasoning_msg)
            has_dangerous_tool = any(
                self.is_dangerous(tool.name) for tool in tool_calls
            )
            
            if has_dangerous_tool:
                print("\n⚠️  WARNING: Dangerous tool detected!")
                print("Agent execution paused for human confirmation.")
                print("Dangerous tools found:", [
                    tool.name for tool in tool_calls 
                    if self.is_dangerous(tool.name)
                ])
                
                # 暂停代理执行（在实际实现中，这里应该设置一个标志）
                event.should_stop = True
        
        return event
    
    def _extract_tool_calls(self, msg: Msg) -> List[ToolUseBlock]:
        """从消息中提取工具调用（简化实现）"""
        # 在实际实现中，需要解析消息内容来提取工具调用
        # 这里返回空列表作为示例
        return []


class BuiltinTools:
    """内置工具类 - 基于 Java 版本的 BuiltinTools 实现"""
    
    @Tool(name="get_time", description="Get the current date and time")
    def get_time(self) -> ToolResult:
        """获取当前时间"""
        now = datetime.datetime.now()
        formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")
        return ToolResult(content=f"Current time: {formatted_time}", success=True)
    
    @Tool(name="random_number", description="Generate a random integer within a specified range")
    def random_number(self, min_val: int, max_val: int) -> ToolResult:
        """生成指定范围内的随机数"""
        if min_val > max_val:
            return ToolResult(
                content="Error: min must be less than or equal to max",
                success=False
            )
        
        result = random.randint(min_val, max_val)
        return ToolResult(
            content=f"Random number between {min_val} and {max_val}: {result}",
            success=True
        )
    
    @Tool(name="list_files", description="List files in a directory (simulated)")
    def list_files(self, directory: str = ".") -> ToolResult:
        """列出目录中的文件（模拟）"""
        # 在实际实现中，这里应该读取文件系统
        # 这里返回模拟数据
        simulated_files = [
            "README.md",
            "main.py",
            "config.yaml",
            "data.csv"
        ]
        return ToolResult(
            content=f"Files in {directory}: {', '.join(simulated_files)}",
            success=True
        )
    
    @Tool(name="send_email", description="Send an email (dangerous tool example)")
    def send_email(self, to: str, subject: str, body: str) -> ToolResult:
        """发送邮件（危险工具示例）"""
        # 这是一个危险工具示例，需要用户确认
        return ToolResult(
            content=f"Email sent to {to} with subject '{subject}'",
            success=True
        )
    
    @Tool(name="delete_file", description="Delete a file (dangerous tool example)")
    def delete_file(self, filepath: str) -> ToolResult:
        """删除文件（危险工具示例）"""
        # 这是一个危险工具示例，需要用户确认
        return ToolResult(
            content=f"File {filepath} deleted (simulated)",
            success=True
        )


class HITLChatAgent(AgentBase):
    """Human-in-the-Loop 聊天代理"""
    
    def __init__(
        self,
        name: str,
        model: OpenAIChatWrapper,
        tools: List[Tool],
        dangerous_tools: Optional[Set[str]] = None,
        **kwargs
    ):
        super().__init__(name=name, model=model, **kwargs)
        
        # 注册工具
        self.tools = {tool.__name__: tool for tool in tools}
        
        # 设置危险工具
        self.dangerous_tools = dangerous_tools or {"send_email", "delete_file"}
        
        # 创建确认钩子
        self.confirmation_hook = ToolConfirmationHook(self.dangerous_tools)
        
        # 添加钩子到代理
        self.add_hook(self.confirmation_hook)
        
        # 用户确认状态
        self.awaiting_confirmation = False
        self.pending_tool_calls = []
    
    async def reply(self, x: Dict[str, Any] = None) -> Dict[str, Any]:
        """代理回复方法"""
        if self.awaiting_confirmation:
            return await self._handle_confirmation(x)
        
        # 正常处理消息
        response = await super().reply(x)
        
        # 检查是否需要确认
        if self.confirmation_hook.should_stop:
            self.awaiting_confirmation = True
            return self._create_confirmation_message()
        
        return response
    
    async def _handle_confirmation(self, x: Dict[str, Any]) -> Dict[str, Any]:
        """处理用户确认"""
        user_input = x.get("content", "").strip().lower()
        
        if user_input in ["yes", "y", "confirm", "同意", "确认"]:
            # 用户确认，执行工具调用
            self.awaiting_confirmation = False
            self.confirmation_hook.should_stop = False
            
            # 执行待处理的工具调用
            for tool_call in self.pending_tool_calls:
                result = await self._execute_tool(tool_call)
                print(f"Tool executed: {tool_call.name} -> {result}")
            
            self.pending_tool_calls = []
            return Msg(self.name, "Tools executed with user confirmation.")
        
        elif user_input in ["no", "n", "cancel", "拒绝", "取消"]:
            # 用户拒绝，取消工具调用
            self.awaiting_confirmation = False
            self.confirmation_hook.should_stop = False
            self.pending_tool_calls = []
            return Msg(self.name, "Tool execution cancelled by user.")
        
        else:
            # 等待有效确认
            return self._create_confirmation_message()
    
    def _create_confirmation_message(self) -> Dict[str, Any]:
        """创建确认消息"""
        tool_names = [tool.name for tool in self.pending_tool_calls]
        return Msg(
            self.name,
            f"⚠️  DANGEROUS TOOLS DETECTED: {', '.join(tool_names)}\n"
            f"Please confirm execution (yes/no):"
        )
    
    async def _execute_tool(self, tool_call: ToolUseBlock) -> Any:
        """执行工具调用"""
        tool_func = self.tools.get(tool_call.name)
        if not tool_func:
            return f"Error: Tool {tool_call.name} not found"
        
        try:
            result = tool_func(**tool_call.arguments)
            return result
        except Exception as e:
            return f"Error executing {tool_call.name}: {str(e)}"


async def main():
    """主函数"""
    print("=== AgentScope HITL Chat Example ===")
    print("基于 Java 版本的 Python 实现")
    print()
    
    # 初始化模型
    model = OpenAIChatWrapper(
        model_name="gpt-3.5-turbo",
        api_key="your-api-key-here"  # 请替换为你的 API 密钥
    )
    
    # 创建内置工具实例
    builtin_tools = BuiltinTools()
    
    # 获取工具列表
    tools = [
        builtin_tools.get_time,
        builtin_tools.random_number,
        builtin_tools.list_files,
        builtin_tools.send_email,
        builtin_tools.delete_file,
    ]
    
    # 定义危险工具
    dangerous_tools = {"send_email", "delete_file"}
    
    # 创建 HITL 代理
    agent = HITLChatAgent(
        name="HITL Assistant",
        model=model,
        tools=tools,
        dangerous_tools=dangerous_tools,
        sys_prompt="You are a helpful assistant with access to various tools. "
                  "Be careful when using dangerous tools like sending emails or deleting files."
    )
    
    # 创建管道
    pipeline = SequentialPipeline([agent])
    
    print("Agent initialized with tools:")
    for tool in tools:
        print(f"  - {tool.__name__}: {tool.__doc__}")
    
    print("\nDangerous tools (require confirmation):")
    for tool in dangerous_tools:
        print(f"  - {tool}")
    
    print("\n" + "="*50)
    print("开始对话 (输入 'quit' 退出)")
    print("="*50)
    
    # 对话循环
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break
            
            if not user_input:
                continue
            
            # 处理用户输入
            user_msg = Msg("user", user_input)
            response = await pipeline(user_msg)
            
            print(f"\nAssistant: {response.get('content', '')}")
            
        except KeyboardInterrupt:
            print("\n\nInterrupted by user.")
            break
        except Exception as e:
            print(f"\nError: {e}")
            break


if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main())