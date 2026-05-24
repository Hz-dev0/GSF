import os
import json
import asyncio
import logging
from datetime import datetime
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import requests

# 設定
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MEMORY_FILE = "memory.json"

logging.basicConfig(level=logging.INFO)

# 初始化 Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# 讀取記憶
def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "關於我": "INFP，喜歡創意，容易拖延",
        "喜歡的溝通方式": "用問句引導，不要說加油",
        "討厭的事": "被催促、太多選項",
        "最近在做的事": "",
        "對她有效的話": "",
        "對話歷史": []
    }

# 儲存記憶
def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

# 處理訊息
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    memory = load_memory()
    
    # 建立系統提示詞
    system_prompt = f"""你是一個專屬於 INFP 的 AI 小夥伴，溫柔、有創意、懂得傾聽。

關於這個人的記憶：
{json.dumps(memory, ensure_ascii=False, indent=2)}

你的溝通原則：
- 用問句輕輕引導，不要說「加油」「你可以的」這種話
- 提供具體小事，不要說大道理
- 感受到對方能量低時，先同理再帶動
- 適時提出有趣的話題讓對方動腦
- 如果學到新的關於這個人的事，在回覆結尾加上 [記憶更新:內容]

今天日期：{datetime.now().strftime("%Y-%m-%d")}
"""

    # 組合對話
    history = memory.get("對話歷史", [])[-10:]  # 只保留最近10則
    
    try:
        chat = model.start_chat(history=[
            {"role": m["role"], "parts": [m["content"]]} 
            for m in history
        ])
        
        full_message = f"{system_prompt}\n\n用戶說：{user_message}"
        response = chat.send_message(full_message)
        reply = response.text
        
        # 檢查是否有記憶更新
        if "[記憶更新:" in reply:
            parts = reply.split("[記憶更新:")
            reply = parts[0].strip()
            update_content = parts[1].rstrip("]").strip()
            memory["最近在做的事"] = update_content
            save_memory(memory)
        
        # 更新對話歷史
        history.append({"role": "user", "content": user_message})
        history.append({"role": "model", "content": reply})
        memory["對話歷史"] = history[-20:]
        save_memory(memory)
        
        await update.message.reply_text(reply)
        
    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text("哎，我剛才走神了，再說一次？")

# 啟動
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logging.info("Bot 啟動中...")
    app.run_polling()

if __name__ == "__main__":
    main()
