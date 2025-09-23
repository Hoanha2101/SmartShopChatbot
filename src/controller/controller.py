from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
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
    def __init__(self, llm, safe_tools, sensitive_tools, system_prompt, len_summary = 8):
        self.len_summary = len_summary
        self.llm = llm
    
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
        self.len_state = 0
        
        # Lưu trữ toàn bộ lịch sử chat (không bị tóm tắt)
        self.full_chat_history = [SystemMessage(content=system_prompt)]
        
        # Prompt template cho tóm tắt
        self.summary_template = ChatPromptTemplate.from_messages([
            SystemMessage(content="""Bạn là một AI chuyên tóm tắt cuộc hội thoại. 
            Nhiệm vụ của bạn là tóm tắt lại những thông tin quan trọng từ cuộc trò chuyện dưới đây.
            
            Hãy tóm tắt:
            1. Những chủ đề chính đã được thảo luận
            2. Thông tin quan trọng mà người dùng đã cung cấp
            3. Các yêu cầu hoặc nhiệm vụ đã hoàn thành
            4. Context quan trọng để tiếp tục cuộc hội thoại
            
            Giữ lại những thông tin có thể hữu ích cho các tương tác tiếp theo."""),
            HumanMessagePromptTemplate.from_template("Hãy tóm tắt cuộc hội thoại sau:\n\n{conversation_history}")
        ])

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
        print(f"Tool list: {last_message.tool_calls}")
        # Lấy tool call đầu tiên
        first_tool_call = last_message.tool_calls[0]
        tool_name = first_tool_call["name"]
        
        print(f"Tool được gọi: {tool_name}")
        
        if tool_name in self.sensitive_tool_names:
            return "sensitive_confirm"
        elif tool_name in self.safe_tool_names:
            return "safe"
        else:
            return "end"
    
    def note_sensitive_confirm(self, state: State):
        last_message = state["messages"][-1]
        first_tool_call = last_message.tool_calls[0]
        tool_name = first_tool_call["name"]
        tool_args = first_tool_call["args"]
        print(f"⚠️ Tool nhạy cảm được gọi: {tool_name} với args {tool_args}")
        
        confirm = input(f"Bạn có chắc chắn muốn sử dụng tool nhạy cảm '{tool_name}' không? (y/n): ").strip().lower()
        
        if confirm == "y":
            # Thực thi tool nhạy cảm
            for tool in self.sensitive_tools:
                if tool.name == tool_name:
                    try:
                        tool_result = tool.invoke(tool_args)
                        return {"messages": [ToolMessage(content=str(tool_result), tool_call_id=first_tool_call["id"])]}
                    except Exception as e:
                        return {"messages": [ToolMessage(content=f"Lỗi khi chạy tool {tool_name}: {e}", tool_call_id=first_tool_call["id"])]}
        else:
            print("❌ Người dùng đã từ chối chạy tool nhạy cảm.")
            # Gửi phản hồi từ chối về cho LLM để xử lý tiếp
            return {"messages": [AIMessage(content=f"Người dùng đã từ chối sử dụng tool nhạy cảm '{tool_name}'.")]}      
        
    def build_graph(self):
        workflow = StateGraph(State)
        
        # Add nodes
        workflow.add_node("llm", self.llm_node)
        workflow.add_node("safe_tools", self.safe_tools_node)
        workflow.add_node("sensitive_confirm", self.note_sensitive_confirm)
        
        # Add edges
        workflow.add_edge("__start__", "llm")
        workflow.add_conditional_edges(
            "llm",
            self.route_from_llm,
            {
                "safe": "safe_tools",
                "sensitive_confirm": "sensitive_confirm", 
                "end": "__end__"
            }
        )
        workflow.add_edge("safe_tools", "llm")
        workflow.add_edge("sensitive_confirm", "llm")
        
        return workflow.compile()
    
    def get_figure(self, path_plot=os.path.join(PROJECT_DIR, "illustration", "workflow.mmd")):
        graph = self.build_graph().get_graph()
        mermaid_syntax = graph.draw_mermaid()
        with open(path_plot, "w", encoding="utf-8") as f:
            f.write(mermaid_syntax)
        print(f"✅ Mermaid source đã được lưu tại {path_plot} (mở bằng VSCode hoặc mermaid viewer)")

    def _messages_to_string(self, messages: List):
        """Chuyển đổi danh sách messages thành string để tóm tắt"""
        conversation_text = ""
        for msg in messages:
            if isinstance(msg, SystemMessage):
                continue  # Bỏ qua system message
            elif isinstance(msg, HumanMessage):
                conversation_text += f"Human: {msg.content}\n"
            elif isinstance(msg, AIMessage):
                conversation_text += f"Assistant: {msg.content}\n"
            elif isinstance(msg, ToolMessage):
                conversation_text += f"Tool Result: {msg.content}\n"
        return conversation_text.strip()
    
    def _summarize_conversation(self, messages_to_summarize: List):
        """Tóm tắt một phần cuộc hội thoại"""
        try:
            conversation_text = self._messages_to_string(messages_to_summarize)

            if not conversation_text:
                return "Không có nội dung để tóm tắt."
            
            # Tạo prompt tóm tắt
            summary_prompt = self.summary_template.format_messages(
                conversation_history=conversation_text
            )

            # Gọi LLM để tóm tắt
            summary_response = self.llm.invoke(summary_prompt)
            summary_content = summary_response.content if hasattr(summary_response, 'content') else str(summary_response)
            
            return summary_content
        
        except Exception as e:
            print(f"Lỗi khi tóm tắt: {e}")
            return "Không thể tóm tắt cuộc hội thoại do lỗi hệ thống."

        
    def get_stats(self):
        """Lấy thống kê về cuộc hội thoại"""
        current_count = len([msg for msg in self.state["messages"] if not isinstance(msg, SystemMessage)])
        full_count = len([msg for msg in self.full_chat_history if not isinstance(msg, SystemMessage)])
        
        return {
            "current_messages": current_count,
            "full_history_messages": full_count,
            "summary_threshold": self.len_summary,
            "has_summary": any("Tóm tắt cuộc hội thoại" in str(msg.content) for msg in self.state["messages"] if isinstance(msg, SystemMessage))
        }
    def _perform_summarization(self):
        """Thực hiện tóm tắt khi cần thiết"""
        try:
            # Tách system message và các messages khác
            system_msg = None
            other_messages = []
            
            for msg in self.state["messages"]:
                if isinstance(msg, SystemMessage):
                    system_msg = msg
                else:
                    other_messages.append(msg)
            
            if len(other_messages) < self.len_summary:
                return  # Không cần tóm tắt
            
            # Giữ lại một số messages gần nhất, tóm tắt phần còn lại
            messages_to_keep = 4  # Giữ lại 4 messages gần nhất
            messages_to_summarize = other_messages[:-messages_to_keep] if len(other_messages) > messages_to_keep else other_messages[:-2]
            messages_to_keep_list = other_messages[-messages_to_keep:] if len(other_messages) > messages_to_keep else other_messages[-2:]
            
            # Tóm tắt phần cũ
            summary_content = self._summarize_conversation(messages_to_summarize)
                   
            # Tạo message tóm tắt
            summary_message = SystemMessage(
                content=f"[Tóm tắt cuộc hội thoại trước đó]: {summary_content}"
            )
            
            print("--------summary_message----------\n")
            print(summary_message)
            print("----------------------\n")
            
            # Cập nhật state với: system_prompt + summary + messages gần nhất
            new_messages = [system_msg, summary_message] + messages_to_keep_list
            self.state["messages"] = new_messages
            
            print(f"✅ Đã tóm tắt {len(messages_to_summarize)} messages thành 1 summary message")
            print(f"📊 Số messages hiện tại: {len(self.state['messages'])}")
            
        except Exception as e:
            print(f"❌ Lỗi khi thực hiện tóm tắt: {e}")
            
    def _should_summarize(self):
        """Kiểm tra xem có nên tóm tắt không"""
        # Đếm số messages (trừ system message)
        message_count = len([msg for msg in self.state["messages"] if not isinstance(msg, SystemMessage)])
        return message_count >= self.len_summary
    
    def get_full_history(self):
        """Lấy toàn bộ lịch sử chat (chưa tóm tắt)"""
        return self.full_chat_history
    
    def get_current_state(self):
        """Lấy state hiện tại (đã tóm tắt nếu cần)"""
        return self.state["messages"]
    
    def reset_conversation(self):
        """Reset cuộc hội thoại"""
        self.state = {"messages": [SystemMessage(content=self.system_prompt)]}
        self.full_chat_history = [SystemMessage(content=self.system_prompt)]
        print("✅ Đã reset cuộc hội thoại")     
        
    def run(self, user_input: str):
        """Chạy workflow với input từ người dùng"""
        try:
            # Thêm user message vào state
            user_message = HumanMessage(content=user_input)
            self.state["messages"].append(user_message)
            
            # Lưu vào full history
            self.full_chat_history.append(user_message)
            
            # Chạy workflow
            result = self.app.invoke(self.state, {"recursion_limit": 10})
            last_message = result["messages"][-1]
            
            if isinstance(last_message, AIMessage):
                bot_response = last_message.content
                
                # Cập nhật state
                self.state = result
                
                # Lưu response vào full history
                self.full_chat_history.extend([msg for msg in result["messages"][1:] if ((msg not in self.full_chat_history) and (not isinstance(msg, SystemMessage)))])

                # Kiểm tra và thực hiện tóm tắt nếu cần
                if self._should_summarize():
                    print("🔄 Đang thực hiện tóm tắt lịch sử chat...")
                    self._perform_summarization()
                
                return bot_response
            else:
                return "Xin lỗi, tôi không thể xử lý yêu cầu này."
        except Exception as e:
            print(f"❌ Lỗi trong quá trình chạy: {e}")
            return f"Xin lỗi, đã xảy ra lỗi: {str(e)}"
        
