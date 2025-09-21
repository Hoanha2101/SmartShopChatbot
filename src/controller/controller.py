from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import ToolNode
from langchain.tools import tool
from typing import TypedDict, List, Annotated
import operator
from IPython.display import Image, display
from langgraph.graph import StateGraph
import os
from ..models import llm
from ..Prompts import system_prompt

PROJECT_DIR = os.path.abspath(os.path.join(__file__, "..", "..", ".."))

class State(TypedDict):
    messages: Annotated[list, operator.add]

class ChatController:
    def __init__(self, llm, safe_tools, sensitive_tools, system_prompt):
        self.safe_tools = safe_tools
        self.safe_tools_node = ToolNode(tools=self.safe_tools)
        self.safe_tool_names = {tool.name for tool in self.safe_tools}
        
        self.sensitive_tools = sensitive_tools
        self.sensitive_tools_node = ToolNode(tools=self.sensitive_tools)
        self.sensitive_tool_names = {tool.name for tool in self.sensitive_tools}
        
        self.all_tools = self.safe_tools + self.sensitive_tools
        self.llm_with_tools = llm.bind_tools(self.all_tools)
        
        self.system_prompt = system_prompt
        
        self.app = self.build_graph()
        
        self.state = {"messages": [SystemMessage(content=system_prompt)]}

    def llm_node(self, state: State):
        messages = state["messages"]
    
        # Nếu chưa có system message, thêm vào
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=self.system_prompt)] + messages
        
        response = self.llm_with_tools.invoke(messages)
        return {"messages": [response]}
    
    def route_from_llm(self, state: State):
        last_message = state["messages"][-1]
        # Nếu không có tool calls, kết thúc
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return "end"
        # Lấy tool call đầu tiên
        first_tool_call = last_message.tool_calls[0]
        tool_name = first_tool_call["name"]
        
        print(f"Tool được gọi: {tool_name}")
        
        if tool_name in self.sensitive_tool_names:
            return "sensitive"
        elif tool_name in self.safe_tool_names:
            return "safe"
        else:
            return "end"
        
    def build_graph(self):
        workflow = StateGraph(State)
        
        # Add nodes
        workflow.add_node("llm", self.llm_node)
        workflow.add_node("safe_tools", self.safe_tools_node)
        workflow.add_node("sensitive_tools", self.sensitive_tools_node)
        
        # Add edges
        workflow.add_edge("__start__", "llm")
        workflow.add_conditional_edges(
            "llm",
            self.route_from_llm,
            {
                "safe": "safe_tools",
                "sensitive": "sensitive_tools", 
                "end": "__end__"
            }
        )
        
        workflow.add_edge("safe_tools", "llm")
        workflow.add_edge("sensitive_tools", "llm")
        
        return workflow.compile(interrupt_before=["sensitive_tools"])
    
    def get_figure(self, path_plot = os.path.join(PROJECT_DIR, "illustration", "workflow.png")):
        graph = self.build_graph().get_graph()
        graph_image = graph.draw_mermaid_png() 
        with open(path_plot, "wb") as f:
            f.write(graph_image)
        print(f"✅ Workflow đã được lưu tại {path_plot}")
        
    def run(self, user_input: str):
        
        # Thêm user message vào state
        self.state["messages"].append(HumanMessage(content=user_input))
        
        # Chạy workflow
        result = self.app.invoke(self.state, {"recursion_limit": 10})  # Giới hạn recursion
        last_message = result["messages"][-1]
        
        if isinstance(last_message, AIMessage):
            bot_response = last_message.content
            self.state = result
            return bot_response
        else:
            return "Xin lỗi, tôi không thể xử lý yêu cầu này."