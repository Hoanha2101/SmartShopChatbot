# from src.controller import ChatController
# from src.models import llm
# from src.Prompts import system_prompt
# from src.chatTools import safe_tools, sensitive_tools

# SaleChatbot = ChatController(llm, safe_tools, sensitive_tools, system_prompt)

# # SaleChatbot.get_figure()

# while True:
#     user_input = input("[👤 Bạn]: ").strip()
#     if user_input.lower() in {"exit", "quit"}:
#         print("Kết thúc cuộc trò chuyện.")
#         break
#     response = SaleChatbot.run(user_input)
#     print(f"[🤖 Bot]: {response}")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import logging
import pandas as pd

from src.controller import ChatController
from src.models import llm
from src.Prompts import system_prompt
from src.chatTools import safe_tools, sensitive_tools

# Khởi tạo FastAPI app
app = FastAPI(title="Sale Chatbot API", version="1.0.0")

# Cấu hình CORS để cho phép React app kết nối
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong production nên chỉ định cụ thể domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo chatbot
SaleChatbot = ChatController(llm, safe_tools, sensitive_tools, system_prompt)

# Pydantic models cho request/response
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    response: str
    session_id: str
    success: bool = True

class HealthResponse(BaseModel):
    status: str
    message: str

# Dictionary để lưu trữ session (trong production nên dùng Redis hoặc database)
sessions = {}

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return HealthResponse(status="healthy", message="Sale Chatbot API is running!")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check"""
    return HealthResponse(status="healthy", message="All systems operational")

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_message: ChatMessage):
    """Main chat endpoint"""
    try:
        # Lấy session_id, nếu không có thì tạo mới
        session_id = chat_message.session_id or "default"
        
        # Xử lý tin nhắn bằng chatbot
        response = SaleChatbot.run(chat_message.message)
        
        # Lưu lại lịch sử chat cho session này
        if session_id not in sessions:
            sessions[session_id] = []
        
        sessions[session_id].append({
            "user_message": chat_message.message,
            "bot_response": response,
            "timestamp": str(pd.Timestamp.now())
        })
        
        return ChatResponse(
            response=response,
            session_id=session_id,
            success=True
        )
    
    except Exception as e:
        logging.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """Lấy lịch sử chat của một session"""
    if session_id not in sessions:
        return {"history": [], "session_id": session_id}
    
    return {"history": sessions[session_id], "session_id": session_id}

@app.delete("/chat/history/{session_id}")
async def clear_chat_history(session_id: str):
    """Xóa lịch sử chat của một session"""
    if session_id in sessions:
        del sessions[session_id]
    return {"message": f"History cleared for session {session_id}"}

@app.get("/sessions")
async def list_sessions():
    """Liệt kê tất cả các session hiện tại"""
    return {"sessions": list(sessions.keys())}

if __name__ == "__main__":
    # Cấu hình logging
    logging.basicConfig(level=logging.INFO)
    
    # Chạy server
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,  # Tự động reload khi code thay đổi
        log_level="info"
    )