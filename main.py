from src.controller import ChatController
from src.models import llm
from src.Prompts import system_prompt
from src.chatTools import safe_tools, sensitive_tools

SaleChatbot = ChatController(llm, safe_tools, sensitive_tools, system_prompt)

while True:
    user_input = input("[👤 Bạn]: ").strip()
    if user_input.lower() in {"exit", "quit"}:
        print("Kết thúc cuộc trò chuyện.")
        break
    response = SaleChatbot.run(user_input)
    print(f"[🤖 Bot]: {response}")