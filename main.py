from src.controller import ChatController
from src.models import llm
from src.Prompts import system_prompt
from src.chatTools import safe_tools, sensitive_tools

SaleChatbot = ChatController(llm, safe_tools, sensitive_tools, system_prompt)

# SaleChatbot.get_figure()