import logging
from typing import Any

from agentscope.agent import AgentBase, ReActAgentBase

def pre_acting_log(self: AgentBase | ReActAgentBase, kwargs: dict[str, Any]):
    if kwargs.get("tool_call", {}).get("type", '') == "tool_use":
        tool_call_info = kwargs.get("tool_call")
        logging.info(f'开始调用工具: {tool_call_info["name"]}, input: {tool_call_info["input"]}')


def post_acting_log(self: AgentBase | ReActAgentBase, kwargs: dict[str, Any], output: Any):
    if kwargs.get("tool_call", {}).get("type", '') == "tool_use":
        tool_call_info = kwargs.get("tool_call")
        logging.info(f'工具执行完毕: {tool_call_info["name"]}, input: {tool_call_info["input"]}')
    return output


def post_print_log(self: AgentBase | ReActAgentBase, kwargs: dict[str, Any], output: Any):
    logging.info(f'输出信息: {kwargs}')
    return output
