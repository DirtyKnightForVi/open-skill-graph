"""
AgentScope Human-in-the-Loop Tutorial Example
基于 AgentScope 官方教程：Multi-Agent Customer Support System
重点实现 Part 4: Human-in-the-Loop — Using Hooks for Manual Review

官方教程链接：https://docs.agentscope.io/tutorial/tutorial_sales_agent
"""

import asyncio
import os
from typing import Any, Dict, List, Optional
from datetime import datetime

# ============================================================================
# Part 1: 环境设置和导入
# ============================================================================

# 设置 OpenAI API 密钥（请替换为您的密钥）
os.environ["OPENAI_API_KEY"] = "your-openai-api-key-here"

# 尝试导入 AgentScope 组件
try:
    from agentscope.agents import AgentBase, ReActAgent, UserAgent
    from agentscope.message import Msg
    from agentscope.models import OpenAIChatWrapper
    from agentscope.hooks import HookBase
    from agentscope.tools import tool, ToolResult
    AGENTSCOPE_AVAILABLE = True
    print("✅ AgentScope is available")
except ImportError:
    AGENTSCOPE_AVAILABLE = False
    print("⚠️  AgentScope not installed. Running in simulation mode.")
    print("   Install with: pip install agentscope")
    
    # 模拟类
    class AgentBase:
        def __init__(self, **kwargs):
            pass
    
    class Msg:
        def __init__(self, name, content, role="user"):
            self.name = name
            self.content = content
            self.role = role
        
        def get_text_content(self):
            return self.content
    
    class HookBase:
        pass

# ============================================================================
# Part 2: 工具定义
# ============================================================================

if AGENTSCOPE_AVAILABLE:
    @tool
    def get_current_time() -> ToolResult:
        """获取当前时间"""
        return ToolResult(content=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    @tool
    def get_product_info(product_id: str) -> ToolResult:
        """获取产品信息"""
        products = {
            "P001": {"name": "Smart Watch Pro", "price": 299.99, "stock": 50},
            "P002": {"name": "Wireless Earbuds", "price": 89.99, "stock": 120},
            "P003": {"name": "Laptop Stand", "price": 39.99, "stock": 200},
        }
        product = products.get(product_id, {"error": "Product not found"})
        return ToolResult(content=str(product))
    
    @tool
    def check_order_status(order_id: str) -> ToolResult:
        """检查订单状态"""
        orders = {
            "ORD001": {"status": "shipped", "estimated_delivery": "2024-03-15"},
            "ORD002": {"status": "processing", "estimated_delivery": "2024-03-20"},
            "ORD003": {"status": "delivered", "delivery_date": "2024-03-10"},
        }
        order = orders.get(order_id, {"error": "Order not found"})
        return ToolResult(content=str(order))
    
    @tool
    def process_refund_request(order_id: str, reason: str, amount: float) -> ToolResult:
        """处理退款请求（高风险操作）"""
        result = {
            "order_id": order_id,
            "refund_reason": reason,
            "refund_amount": amount,
            "status": "pending_approval",
            "message": "Refund request created and requires manual approval"
        }
        return ToolResult(content=str(result))
else:
    # 模拟工具函数
    def get_current_time():
        return "2024-03-14 14:30:00"
    
    def get_product_info(product_id):
        return f"Product {product_id}: Smart Watch Pro, $299.99"
    
    def check_order_status(order_id):
        return f"Order {order_id}: Shipped, estimated delivery 2024-03-15"
    
    def process_refund_request(order_id, reason, amount):
        return f"Refund request for order {order_id}: ${amount} - Pending approval"

# ============================================================================
# Part 3: Human-in-the-Loop Hook 实现（官方教程核心）
# ============================================================================

async def human_review_post_reply_hook(
    agent: AgentBase,
    kwargs: Dict[str, Any],
    output: Msg,
) -> Optional[Msg]:
    """
    Post-reply hook: 在代理回复后进行人工审核
    
    基于 AgentScope 官方教程 Part 4 的实现：
    1. 显示代理生成的响应
    2. 获取人工审核意见
    3. 批准或要求重新生成
    
    官方教程原版函数签名：
    async def human_review_post_reply_hook(
        self: AgentBase,
        kwargs: dict[str, Any],
        output: Msg,
    ) -> Msg | None:
    """
    
    print("\n" + "=" * 60)
    print("[Manual Review] Agent response requires human review")
    print("=" * 60)
    
    # 显示代理响应
    response_text = output.get_text_content()
    print(f"Agent Response:\n{response_text}")
    print("-" * 60)
    
    # 获取人工审核意见
    print("Review Options:")
    print("  • Type 'ok' or 'approve' to approve the response")
    print("  • Type feedback text to request revision")
    print("  • Type 'escalate' to escalate to senior agent")
    
    review_input = input("\nYour review decision: ").strip()
    
    # 处理审核决策
    if review_input.lower() in ["ok", "approve", "yes", "y"]:
        print("✅ [Review Approved] Response confirmed and sent to customer.")
        return None  # 保持原响应
    
    elif review_input.lower() == "escalate":
        print("⚠️ [Review Escalated] Response escalated to senior agent.")
        # 创建升级消息
        escalated_msg = Msg(
            "SeniorAgent",
            f"Response escalated for review:\n\n{response_text}\n\n"
            f"Please provide revised response.",
            "system",
        )
        return escalated_msg
    
    else:
        # 审核不通过，要求重新生成
        print(f"🔄 [Review Rejected] Revision requested: {review_input}")
        
        # 临时移除钩子避免无限循环
        if hasattr(agent, 'clear_instance_hooks'):
            agent.clear_instance_hooks("post_reply")
        
        # 创建修订请求消息
        original_msg = kwargs.get("msg")
        if original_msg is not None:
            revised_msg = Msg(
                original_msg.name,
                f"{original_msg.get_text_content()}\n\n"
                f"[Review Feedback] Please revise based on: {review_input}",
                original_msg.role,
            )
            
            # 重新生成响应
            if hasattr(agent, 'reply'):
                revised_output = await agent.reply(revised_msg)
                
                # 重新注册钩子
                if hasattr(agent, 'register_instance_hook'):
                    agent.register_instance_hook(
                        hook_type="post_reply",
                        hook_name="human_review",
                        hook=human_review_post_reply_hook,
                    )
                
                return revised_output
        
        return None

# ============================================================================
# Part 4: 创建客服代理
# ============================================================================

def create_support_agent(name: str = "CustomerSupport") -> AgentBase:
    """创建客服代理"""
    
    if AGENTSCOPE_AVAILABLE:
        # 使用真实的 AgentScope
        model = OpenAIChatWrapper(
            model_name="gpt-3.5-turbo",
            api_key=os.environ.get("OPENAI_API_KEY"),
        )
        
        # 定义代理可用的工具
        tools = [
            get_current_time,
            get_product_info,
            check_order_status,
            process_refund_request,
        ]
        
        # 创建 ReActAgent
        from agentscope.agents import ReActAgent
        agent = ReActAgent(
            name=name,
            model=model,
            tools=tools,
            sys_prompt="""You are a customer support agent for an electronics company.
Your responsibilities:
1. Answer customer inquiries about products and orders
2. Check order status and product information
3. Process refund requests (requires manual approval)
4. Escalate complex issues to human agents

Guidelines:
- Be polite and professional
- Provide accurate information
- For refund requests, explain that they require manual approval
- Escalate angry or complex customers to human agents""",
        )
        
        # 注册 human-in-the-loop 钩子
        agent.register_instance_hook(
            hook_type="post_reply",
            hook_name="human_review",
            hook=human_review_post_reply_hook,
        )
        
        return agent
    
    else:
        # 模拟代理
        class MockAgent(AgentBase):
            def __init__(self, name):
                self.name = name
                self.hooks = {}
            
            async def __call__(self, msg):
                print(f"\n[{self.name}] Processing message: {msg.content[:50]}...")
                
                # 模拟响应
                responses = {
                    "order": "Your order ORD001 has been shipped and will arrive on March 15, 2024.",
                    "refund": "I've created a refund request for $299.99. This requires manual approval.",
                    "urgent": "I apologize for the delay. I'm escalating this to a senior agent.",
                }
                
                # 简单关键词匹配
                content = msg.content.lower()
                if "order" in content:
                    response = responses["order"]
                elif "refund" in content:
                    response = responses["refund"]
                elif "urgent" in content:
                    response = responses["urgent"]
                else:
                    response = "Thank you for your inquiry. How can I help you?"
                
                output = Msg(self.name, response, "assistant")
                
                # 如果有钩子，执行钩子
                if "post_reply" in self.hooks:
                    hook_result = await self.hooks["post_reply"](self, {"msg": msg}, output)
                    if hook_result:
                        return hook_result
                
                return output
            
            def register_instance_hook(self, hook_type, hook_name, hook):
                self.hooks[hook_type] = hook
        
        agent = MockAgent(name)
        return agent

# ============================================================================
# Part 5: 演示函数
# ============================================================================

async def demo_human_in_the_loop():
    """演示 human-in-the-loop 功能"""
    
    print("=" * 70)
    print("AgentScope Human-in-the-Loop Tutorial Demo")
    print("Based on Official Tutorial: Part 4 - Using Hooks for Manual Review")
    print("=" * 70)
    
    if not AGENTSCOPE_AVAILABLE:
        print("\n⚠️  Running in SIMULATION MODE")
        print("   To use real AgentScope, install with: pip install agentscope")
        print("   And set your OPENAI_API_KEY environment variable")
    
    print("\n" + "=" * 70)
    print("Test Scenarios:")
    print("1. Order status inquiry")
    print("2. Refund request (requires manual approval)")
    print("3. Urgent complaint (may require escalation)")
    print("=" * 70)
    
    # 创建代理
    agent = create_support_agent("SupportAgent")
    
    # 测试用例
    test_cases = [
        {
            "name": "Customer",
            "content": "Hi, can you check the status of my order ORD001?",
            "description": "Order status inquiry"
        },
        {
            "name": "Customer",
            "content": "I want to return my Smart Watch Pro and get a refund of $299.99.",
            "description": "Refund request"
        },
        {
            "name": "Customer",
            "content": "URGENT! My order hasn't arrived and I need it today!",
            "description": "Urgent complaint"
        },
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'#' * 70}")
        print(f"Test {i}: {test_case['description']}")
        print(f"{'#' * 70}")
        print(f"\nCustomer: {test_case['content']}")
        
        # 创建消息
        msg = Msg(
            name=test_case["name"],
            content=test_case["content"],
            role="user",
        )
        
        # 代理处理（包含 human-in-the-loop 审核）
        response = await agent(msg)
        
        print(f"\nFinal Response: {response.get_text_content()}")
        
        # 暂停
        if i < len(test_cases):
            input("\nPress Enter to continue to next test case...")
    
    print("\n" + "=" * 70)
    print("Demo Completed!")
    print("=" * 70)
    
    # 总结
    print("\nKey Takeaways from Official Tutorial:")
    print("1. Hooks allow injecting custom logic before/after agent execution")
    print("2. post_reply hooks are ideal for human review of agent responses")
    print("3. Hook signature: (self, kwargs, output) -> Any | None")
    print("4. Return None to keep original output, or return new Msg to modify")
    print("5. Temporary hook removal prevents infinite loops during regeneration")

# ============================================================================
# Part 6: 运行演示
# ============================================================================

if __name__ == "__main__":
    # 运行演示
    asyncio.run(demo_human_in_the_loop())
    
    print("\n" + "=" * 70)
    print("Code Structure Summary:")
    print("=" * 70)
    print("""
1. Tool Definitions (@tool decorator)
   - get_current_time, get_product_info, etc.
   
2. Human Review Hook (core of Part 4)
   - human_review_post_reply_hook()
   - Displays agent response for review
   - Accepts 'ok', feedback, or 'escalate'
   - Can regenerate response with feedback
   
3. Agent Creation
   - create_support_agent()
   - Registers the human review hook
   
4. Demonstration
   - Test cases with different scenarios
   - Shows human-in-the-loop in action
    """)