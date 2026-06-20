import os
import asyncio
import threading
from flask import Flask
from telethon import TelegramClient, events

app = Flask(__name__)

@app.route('/')
def home():
    return "Бот-секретарь работает!", 200

@app.route('/health')
def health():
    return "OK", 200

API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '')
PHONE = os.environ.get('PHONE', '')
DEEPSEEK_USERNAME = '@DeepSeekBot'

if not API_ID or not API_HASH or not PHONE:
    raise ValueError("Задай API_ID, API_HASH и PHONE в переменных окружения!")

client = TelegramClient('session', API_ID, API_HASH)

@client.on(events.NewMessage(incoming=True))
async def handler(event):
    if event.out:
        return
    sender = await event.get_sender()
    if not sender or sender.bot:
        return
    if sender.id == (await client.get_me()).id:
        return
    contact_id = sender.id
    contact_name = sender.first_name or 'друг'
    try:
        messages = await client.get_messages(contact_id, limit=20)
        my_msgs = [msg.text for msg in messages if msg.out and msg.text and len(msg.text) < 500]
        my_msgs = my_msgs[:10]
        history_text = "\n".join([f"Я написал: {msg}" for msg in my_msgs]) if my_msgs else "Истории общения пока нет."
    except Exception:
        history_text = "Историю не удалось загрузить."
    prompt = f"""Ты — {contact_name} (так меня зовут). Твоя задача — ответить на сообщение от {contact_name} так, как ответил бы я лично.
Вот примеры моих недавних сообщений этому человеку:
{history_text}

Теперь я получил от него сообщение:
"{event.message.text}"

Напиши ответ в моём стиле (используй мои любимые фразы, эмодзи, краткость). Ответ должен быть не длиннее 2-3 предложений."""
    try:
        deepseek_entity = await client.get_entity(DEEPSEEK_USERNAME)
        await client.send_message(deepseek_entity, prompt)
        for _ in range(20):
            await asyncio.sleep(1)
            async for msg in client.iter_messages(deepseek_entity, limit=1):
                if msg.text and not msg.out and msg.date > event.date:
                    await client.send_message(contact_id, msg.text)
                    return
        await client.send_message(contact_id, "Привет! Я сейчас в небе, связь нестабильна. Отпишусь, как только приземлюсь!")
    except Exception:
        await client.send_message(contact_id, "Извини, я сейчас не могу ответить, но обязательно напишу позже!")

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(client.start(phone=PHONE))
    print("✅ Секретарь запущен и слушает сообщения...")
    loop.run_until_complete(client.run_until_disconnected())

thread = threading.Thread(target=run_bot)
thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
