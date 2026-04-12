# AgentScope Human-in-the-Loop 官方教程实现

基于 AgentScope 官方教程 **Part 4: Human-in-the-Loop — Using Hooks for Manual Review** 的完整 Python 实现。

## 📚 官方教程参考

- **教程标题**: Multi-Agent Customer Support System
- **Part 4**: Human-in-the-Loop — Using Hooks for Manual Review  
- **官方链接**: https://docs.agentscope.io/tutorial/tutorial_sales_agent#part-4-human-in-the-loop-%E2%80%94-using-hooks-for-manual-review

## 🎯 核心概念

### Hook 机制
AgentScope 的 Hook 机制允许在代理执行的关键节点注入自定义逻辑，实现非侵入式扩展：

```
Agent Execution Flow:
┌─────────────────────────────────────┐
│ Agent.__call__(msg)                 │
│   ├── pre_reply hooks               │ ← 审核/修改输入
│   ├── reply()                       │ ← 代理核心逻辑
│   └── post_reply hooks              │ ← 审核/修改输出 (Human-in-the-Loop!)
└─────────────────────────────────────┘
```

### Hook 函数签名
```python
# Pre-hook: 在执行前调用
(self, kwargs) -> dict | None

# Post-hook: 在执行后调用  
(self, kwargs, output) -> Any | None
```

- **返回 None**: 保持原输出
- **返回新值**: 替换输出

## 📁 文件说明

### 1. `hitl_official_example.py` - 核心实现
```python
# 官方教程核心：Human Review Hook
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
    """
```

### 2. `agentscope_hitl_tutorial.py` - 完整教程
包含更多工具定义和完整演示场景。

## 🚀 快速开始

### 安装依赖
```bash
# 安装 AgentScope
pip install agentscope

# 设置 API 密钥
export OPENAI_API_KEY=your-api-key-here
```

### 运行示例
```bash
# 运行核心示例
python hitl_official_example.py

# 运行完整教程
python agentscope_hitl_tutorial.py
```

### 无依赖运行（模拟模式）
如果未安装 AgentScope，代码会自动进入模拟模式：
```bash
# 无需安装，直接运行
python hitl_official_example.py
```

## 🔧 核心功能

### 1. 人工审核流程
```
1. 代理生成响应
2. Hook 触发人工审核
3. 显示响应供审核
4. 用户选择：
   - 'ok': 批准并发送
   - 反馈文本: 要求重新生成
   - 'escalate': 升级到高级代理
5. 根据选择执行相应操作
```

### 2. 避免无限循环
```python
# 临时移除钩子
agent.clear_instance_hooks("post_reply")

# 重新生成响应
revised_output = await agent.reply(revised_msg)

# 重新注册钩子
agent.register_instance_hook(...)
```

### 3. 工具定义
```python
@tool
def get_order_status(order_id: str) -> ToolResult:
    """获取订单状态"""
    return ToolResult(content=status)

@tool  
def process_refund(order_id: str, amount: float) -> ToolResult:
    """处理退款请求"""
    return ToolResult(content=refund_info)
```

## 📋 测试场景

### 场景 1: 订单状态查询
```
Customer: Can you check the status of my order ORD001?
→ Agent: Your order ORD001 is shipped...
→ Human Review: [ok] 批准发送
```

### 场景 2: 退款请求  
```
Customer: I want a refund for my order!
→ Agent: I've created a refund request...
→ Human Review: [修改] "请提供更详细的退款政策说明"
→ Agent: [重新生成] 根据反馈生成新响应
```

### 场景 3: 紧急投诉
```
Customer: URGENT! My order hasn't arrived!
→ Agent: I apologize for the issue...
→ Human Review: [escalate] 升级到高级代理
→ Senior Agent: 处理升级请求
```

## 🏗️ 代码结构

### 核心组件
```python
# 1. Hook 实现
human_review_post_reply_hook()

# 2. 代理创建
create_hitl_agent()

# 3. 工具定义
@tool 装饰的函数

# 4. 演示函数
demonstrate_hitl()
```

### 注册 Hook
```python
agent.register_instance_hook(
    hook_type="post_reply",      # 钩子类型
    hook_name="human_review",    # 钩子名称  
    hook=human_review_post_reply_hook,  # 钩子函数
)
```

## 📖 官方教程要点总结

### 1. Hook 的优势
- **非侵入式**: 不修改代理核心代码
- **标准化**: 固定函数签名，易于集成
- **可继承**: 通过 metaclass 自动继承
- **细粒度**: 支持多个执行节点

### 2. 常见 Human-in-the-Loop 场景
- **响应审核**: 审核代理生成的响应
- **工具确认**: 确认高风险工具调用
- **参数验证**: 验证工具参数合理性
- **结果检查**: 检查工具执行结果

### 3. 最佳实践
- **明确审核标准**: 定义清晰的审核规则
- **提供修改选项**: 支持 approve/reject/modify
- **避免无限循环**: 临时移除钩子
- **记录审核历史**: 保存审核决策记录

## 🔄 与自定义实现的比较

| 特性 | 官方实现 | 自定义实现 |
|------|----------|------------|
| **集成方式** | Hook 机制 | 自定义确认系统 |
| **审核时机** | post_reply (响应后) | pre_acting (工具执行前) |
| **审核对象** | 代理响应 | 工具调用 |
| **修改方式** | 提供反馈让代理重写 | 直接修改参数 |
| **框架支持** | 原生支持 | 需要额外集成 |

## 🎨 扩展建议

### 1. 多级审核
```python
# 初级代理 → 人工审核 → 高级代理 → 经理审核
```

### 2. 自动化审核规则
```python
# 基于规则的自动审核
def auto_review_hook(agent, kwargs, output):
    if contains_sensitive_info(output):
        return "自动拒绝：包含敏感信息"
    elif meets_quality_standards(output):
        return None  # 自动批准
    else:
        return "需要人工审核"
```

### 3. 审核仪表板
```python
# 提供 Web 界面进行批量审核
class ReviewDashboard:
    def show_pending_reviews(self):
        # 显示待审核的响应
        pass
    
    def batch_approve(self, review_ids):
        # 批量批准
        pass
```

## 📞 支持与参考

### 官方文档
- [AgentScope 教程](https://docs.agentscope.io/tutorial/tutorial_sales_agent)
- [Hook 机制文档](https://docs.agentscope.io/building-blocks/hooking-functions)
- [API 参考](https://docs.agentscope.io/api-reference)

### 相关资源
- [GitHub 仓库](https://github.com/modelscope/agentscope)
- [示例代码](https://github.com/modelscope/agentscope/tree/main/examples)
- [社区讨论](https://github.com/modelscope/agentscope/discussions)

## 📄 许可证

基于 Apache 2.0 许可证，与 AgentScope 项目保持一致。

---

**注意**: 运行真实 AgentScope 需要有效的 OpenAI API 密钥。模拟模式可用于学习和演示目的。