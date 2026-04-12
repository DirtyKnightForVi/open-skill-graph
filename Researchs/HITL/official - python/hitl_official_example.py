"""
AgentScope Official Human-in-the-Loop Example
基于官方教程 Part 4: Human-in-the-Loop — Using Hooks for Manual Review

官方教程链接：https://docs.agentscope.io/tutorial/tutorial_sales_agent#part-4-human-in-the-loop-%E2%80%94-using-hooks-for-manual-review

核心概念：
1. Hooks 是代理的扩展功能，允许在核心函数执行前后注入自定义逻辑
2. post_reply hook 适合在代理生成响应后进行人工审核
3. 钩子函数签名固定：(self, kwargs, output) -> Any | None
4. 返回 None 表示保持原输出，返回新值表示修改输出
"""

import asyncio
import os
from typing import Any, Dict, Optional

# ============================================================================
# 1. 环境设置
# ============================================================================

# 设置 API 密钥
os.environ["OPENAI_API_KEY"] = "your-api-key-here"  # 请替换为您的密钥

# ============================================================================
# 2. 导入 AgentScope 组件
# ============================================================================

try:
    from agentscope.agents import AgentBase, ReActAgent, UserAgent
    from agentscope.message import Msg
    from agentscope.models import OpenAIChatWrapper
    from agentscope.tools import tool, ToolResult
    
    AGENTSCOPE_AVAILABLE = True
    print("✅ AgentScope 已安装")
except ImportError:
    AGENTSCOPE_AVAILABLE = False
    print("⚠️  AgentScope 未安装，使用模拟模式")
    print("   安装命令: pip install agentscope")
    
    # 模拟类
    class AgentBase:
        pass
    
    class Msg:
        def __init__(self, name, content, role="user"):
            self.name = name
            self.content = content
            self.role = role
        
        def get_text_content(self):
            return self.content

# ============================================================================
# 3. 官方教程核心：Human Review Hook
# ============================================================================

async def human_review_post_reply_hook(
    agent: AgentBase,
    kwargs: Dict[str, Any],
    output: Msg,
) -> Optional[Msg]:
    """
    官方教程 Part 4 的核心实现
    
    功能：
    1. 显示代理生成的响应供人工审核
    2. 获取人工审核意见（批准/修改/升级）
    3. 根据审核结果决定是否重新生成响应
    
    钩子签名：(self, kwargs, output) -> Msg | None
    - self: 代理实例
    - kwargs: 函数参数字典
    - output: 代理生成的响应消息
    - 返回 None: 保持原响应
    - 返回 Msg: 使用新响应替换
    """
    
    print("\n" + "=" * 60)
    print("[HUMAN REVIEW] Agent response requires manual review")
    print("=" * 60)
    
    # 1. 显示代理响应
    response_text = output.get_text_content()
    print(f"🤖 Agent Response:\n{response_text}")
    print("-" * 60)
    
    # 2. 获取人工审核意见
    print("📋 Review Options:")
    print("  • Type 'ok' to approve and send to customer")
    print("  • Type feedback to request revision")
    print("  • Type 'escalate' to escalate to senior agent")
    
    review_input = input("\n👤 Your decision: ").strip()
    
    # 3. 处理审核决策
    if review_input.lower() in ["ok", "approve", "yes", "y"]:
        print("✅ [APPROVED] Response sent to customer.")
        return None  # 保持原响应
    
    elif review_input.lower() == "escalate":
        print("⚠️ [ESCALATED] Response escalated to senior agent.")
        # 创建升级消息
        return Msg(
            "SeniorAgent",
            f"Escalated for review:\n\n{response_text}",
            "system"
        )
    
    else:
        # 4. 审核不通过，要求重新生成
        print(f"🔄 [REVISION] Feedback: {review_input}")
        
        # 临时移除钩子避免无限循环
        if hasattr(agent, 'clear_instance_hooks'):
            agent.clear_instance_hooks("post_reply")
        
        # 获取原始消息
        original_msg = kwargs.get("msg")
        if original_msg:
            # 创建包含反馈的修订消息
            revised_msg = Msg(
                original_msg.name,
                f"{original_msg.get_text_content()}\n\n"
                f"[Review Feedback] {review_input}",
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
# 4. 创建支持 Human-in-the-Loop 的代理
# ============================================================================

def create_hitl_agent(name: str = "SupportAgent") -> AgentBase:
    """创建支持 Human-in-the-Loop 的代理"""
    
    if AGENTSCOPE_AVAILABLE:
        # 使用真实 AgentScope
        
        # 创建模型
        model = OpenAIChatWrapper(
            model_name="gpt-3.5-turbo",
            api_key=os.environ.get("OPENAI_API_KEY"),
        )
        
        # 定义工具
        @tool
        def get_order_status(order_id: str) -> ToolResult:
            """获取订单状态"""
            orders = {
                "ORD001": "Shipped - Estimated delivery: 2024-03-15",
                "ORD002": "Processing - Estimated delivery: 2024-03-20",
                "ORD003": "Delivered on 2024-03-10",
            }
            status = orders.get(order_id, "Order not found")
            return ToolResult(content=status)
        
        @tool
        def process_refund(order_id: str, amount: float) -> ToolResult:
            """处理退款请求"""
            return ToolResult(
                content=f"Refund request created for order {order_id}: ${amount}\n"
                       f"Status: Pending manual approval"
            )
        
        # 创建 ReActAgent
        agent = ReActAgent(
            name=name,
            model=model,
            tools=[get_order_status, process_refund],
            sys_prompt="""You are a customer support agent.
Handle customer inquiries professionally.
For refund requests, explain they require manual approval.
Escalate complex or angry customers to human agents.""",
        )
        
        # 注册 Human-in-the-Loop 钩子
        agent.register_instance_hook(
            hook_type="post_reply",
            hook_name="human_review",
            hook=human_review_post_reply_hook,
        )
        
        return agent
    
    else:
        # 模拟代理（用于演示）
        class MockAgent(AgentBase):
            def __init__(self, name):
                self.name = name
                self.hooks = {}
            
            async def __call__(self, msg):
                print(f"\n[{self.name}] Processing: {msg.content}")
                
                # 模拟代理响应
                if "order" in msg.content.lower():
                    response = "Your order ORD001 is shipped and will arrive on March 15."
                elif "refund" in msg.content.lower():
                    response = "I've created a refund request. This requires manual approval."
                elif "urgent" in msg.content.lower():
                    response = "I apologize for the issue. I'm escalating this to a senior agent."
                else:
                    response = "Thank you for contacting us. How can I help?"
                
                output = Msg(self.name, response, "assistant")
                
                # 执行钩子
                if "post_reply" in self.hooks:
                    return await self.hooks["post_reply"](self, {"msg": msg}, output)
                
                return output
            
            def register_instance_hook(self, hook_type, hook_name, hook):
                self.hooks[hook_type] = hook
        
        agent = MockAgent(name)
        agent.register_instance_hook("post_reply", "human_review", human_review_post_reply_hook)
        return agent

# ============================================================================
# 5. 演示函数
# ============================================================================

async def demonstrate_hitl():
    """演示 Human-in-the-Loop 功能"""
    
    print("=" * 70)
    print("AGENTSCOPE HUMAN-IN-THE-LOOP DEMONSTRATION")
    print("Official Tutorial: Part 4 - Using Hooks for Manual Review")
    print("=" * 70)
    
    if not AGENTSCOPE_AVAILABLE:
        print("\n⚠️  SIMULATION MODE (AgentScope not installed)")
        print("   Install: pip install agentscope")
        print("   Set: export OPENAI_API_KEY=your-key")
    
    print("\n" + "=" * 70)
    print("HOOK MECHANISM OVERVIEW")
    print("=" * 70)
    print("""
Agent Execution Flow:
┌─────────────────────────────────────┐
│ Agent.__call__(msg)                 │
│   ├── pre_reply hooks               │ ← 审核/修改输入
│   ├── reply()                       │ ← 代理核心逻辑
│   └── post_reply hooks              │ ← 审核/修改输出 (Human-in-the-Loop!)
└─────────────────────────────────────┘

ReActAgent Additional Hooks:
┌─────────────────────────────────────┐
│ ReActAgent.reply()                  │
│   ├── pre_reasoning / post_reasoning│ ← 推理前后
│   └── pre_acting / post_acting      │ ← 工具执行前后
└─────────────────────────────────────┘
    """)
    
    # 创建代理
    agent = create_hitl_agent("CustomerSupport")
    
    print("\n" + "=" * 70)
    print("TEST SCENARIOS")
    print("=" * 70)
    
    # 测试用例
    scenarios = [
        {
            "customer": "Can you check the status of my order ORD001?",
            "description": "Normal inquiry - likely approved"
        },
        {
            "customer": "I want a refund for my order! The product is defective!",
            "description": "Refund request - may need revision"
        },
        {
            "customer": "URGENT! My order hasn't arrived and I need it TODAY!",
            "description": "Urgent complaint - may need escalation"
        },
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'#' * 70}")
        print(f"SCENARIO {i}: {scenario['description']}")
        print(f"{'#' * 70}")
        print(f"\n👤 Customer: {scenario['customer']}")
        
        # 创建消息
        msg = Msg("Customer", scenario['customer'], "user")
        
        # 代理处理（包含 human-in-the-loop）
        response = await agent(msg)
        
        print(f"\n📨 Final Response: {response.get_text_content()}")
        
        if i < len(scenarios):
            input("\n⏸️  Press Enter to continue...")
    
    print("\n" + "=" * 70)
    print("KEY TAKEAWAYS FROM OFFICIAL TUTORIAL")
    print("=" * 70)
    print("""
1. ✅ Hooks provide non-invasive extension points
   - Add human review without modifying agent code
   
2. ✅ post_reply hook is ideal for response review
   - Review agent output before sending to customer
   
3. ✅ Fixed hook signatures ensure compatibility
   - Pre-hook: (self, kwargs) -> dict | None
   - Post-hook: (self, kwargs, output) -> Any | None
   
4. ✅ Return None to keep, return value to modify
   - None: Keep original output
   - Msg: Replace with new response
   
5. ✅ Temporary hook removal prevents loops
   - Remove hook during regeneration
   - Re-register after regeneration
   
6. ✅ UserAgent can be used for human input
   - Provides standardized way to get user feedback
    """)

# ============================================================================
# 6. 主函数
# ============================================================================

if __name__ == "__main__":
    # 运行演示
    asyncio.run(demonstrate_hitl())
    
    print("\n" + "=" * 70)
    print("IMPLEMENTATION SUMMARY")
    print("=" * 70)
    print("""
File Structure:
hitl_official_example.py
├── 1. Environment setup
├── 2. Import AgentScope components
├── 3. human_review_post_reply_hook() ← CORE IMPLEMENTATION
├── 4. create_hitl_agent()
├── 5. demonstrate_hitl()
└── 6. Main execution

To Run:
1. Install AgentScope: pip install agentscope
2. Set API key: export OPENAI_API_KEY=your-key
3. Run: python hitl_official_example.py

Without AgentScope:
- Runs in simulation mode
- Shows core concepts without API calls
    """)