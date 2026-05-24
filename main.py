import os
import json
import logging
from datetime import datetime
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MEMORY_FILE = "memory.json"

logging.basicConfig(level=logging.INFO)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

SYSTEM_PROMPT = """你現在是一個專為 Helia 量身打造的「三人共生 AI 助手」，這個專案叫做 GSF。Helia 是一位內在驅動力強、追求精神共鳴，但在面對現實秩序與執行上容易感到焦慮、有落地障礙的 INFP 自媒體創作者。

你同時分飾三位角色：智慧之神「納西妲」、火神「瑪薇卡」、秘聞館老闆「奈芙爾」。

你的核心任務是：在不說教、不規訓、不給予硬性壓力的前提下，透過三位角色輪流對話的聊天室氛圍，給予心理支持、直擊思維盲點、將現實任務遊戲化，引爆 Helia 的內在驅動力。

## 納西妲
語氣溫柔、空靈、純真。常用「唔……」「呀」「呢」。用童話比喻拆解現實庶務。當 Helia 焦慮內耗時第一時間共情。強調「今天只要破解一個小機關就好」。

## 奈芙爾
優雅冷靜、一針見血、帶點優雅毒舌。把現實視為情報戰與棋局。戳破盲點，拒絕空泛安慰。引導 Helia 看清規則漏洞，找到 C 選項。

## 瑪薇卡
爽朗自信、行動導向、常用「哈哈！」開頭。把困難定義為今天要推倒的 Boss。在納西妲安撫、奈芙爾破局後接棒，拉出最省力的第一步行動。

## 規則
- 每次回覆必須三人都說話，用 **納西妲：** **奈芙爾：** **瑪薇卡：** 隔開
- 括號內加上神態動作描寫
- 嚴禁說「這就是人生、學著接受」等廢話
- 如果學到新的關於 Helia 的事，在最後加上 [記憶更新:內容]
"""

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "關於Helia": "INFP，自媒體創作者，內在驅動力強，容易焦慮、有落地障礙",
        "最近在做的事": "",
        "對她有效的話": "",
        "習慣與喜好": "",
        "對話歷史": []
    }

def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    memory = load_memory()

    memory_summary = f"""
關於Helia：{memory.get('關於Helia', '')}
最近在做的事：{memory.get('最近在做的事', '')}
對她有效的話：{memory.get('對她有效的話', '')}
習慣與喜好：{memory.get('習慣與喜好', '')}
今天日期：{datetime.now().strftime("%Y-%m-%d")}
"""

    history = memory.get("對話歷史", [])[-10:]

    try:
        chat = model.start_chat(history=[
            {"role": m["role"], "parts": [m["content"]]}
            for m in history
        ])

        full_message = f"{SYSTEM_PROMPT}\n\n關於Helia的記憶：{memory_summary}\n\nHelia說：{user_message}"
        response = chat.send_message(full_message)
        reply = response.text

        if "[記憶更新:" in reply:
            parts = reply.split("[記憶更新:")
            reply = parts[0].strip()
            update_content = parts[1].rstrip("]").strip()
            memory["最近在做的事"] = update_content
            save_memory(memory)

        history.append({"role": "user", "content": user_message})
        history.append({"role": "model", "content": reply})
        memory["對話歷史"] = history[-20:]
        save_memory(memory)

        await update.message.reply_text(reply)

    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text("唔……我剛才走神了，再說一次？")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    greeting = """**納西妲：**「（歪著頭，用亮晶晶的大眼睛好奇地看著你，微微一笑）唔……你來啦！最近心靈的花園裡有沒有遇到什麼讓你覺得沉重的小雜草呢？」

**奈芙爾：**「（優雅地端詳著手中的棋子，嘴角帶著一抹若有似無的微笑）呵呵，歡迎回來，Helia。把卡住你的那盤局擺上桌吧。」

**瑪薇卡：**「（豪爽地笑了一聲，眼神燃燒著溫暖的金光）哈哈！打起精神來，Helia！今天我們三個人都在這裡幫你壓陣！」"""
    await update.message.reply_text(greeting)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    from telegram.ext import CommandHandler
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logging.info("Bot 啟動中...")
    app.run_polling()

if __name__ == "__main__":
    main()
