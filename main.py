import asyncio
import os
from telethon import TelegramClient, events

# ===== Читаем переменные окружения (зададим на Bothost) =====
API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '')
PHONE = os.environ.get('PHONE', '')  # твой номер в формате +79123456789

# Имя пользователя DeepSeek-бота (уточни, если другое)
DEEPSEEK_USERNAME = '@DeepSeekBot'

if not API_ID or not API_HASH or not PHONE:
    raise ValueError("Задай API_ID, API_HASH и PHONE в переменных окружения!")

client = TelegramClient('session', API_ID, API_HASH)

@client.on(events.NewMessage(incoming=True))
async def handler(event):
    # Игнорируем свои же сообщения
    if event.out:
        return

    sender = await event.get_sender()
    if not sender or sender.bot:
        return  # не отвечаем ботам (и DeepSeek в том числе)

    # Игнорируем сообщения от самого себя (если вдруг)
    if sender.id == (await client.get_me()).id:
        return

    contact_id = sender.id
    contact_name = sender.first_name or 'друг'

    # Берём последние 10 своих сообщений этому контакту (чтобы понять твой стиль)
    try:
        messages = await client.get_messages(contact_id, limit=20)
        my_msgs = [msg.text for msg in messages if msg.out and msg.text and len(msg.text) < 500]
        my_msgs = my_msgs[:10]
        history_text = "\n".join([f"Я написал: {msg}" for msg in my_msgs]) if my_msgs else "Истории общения пока нет."
    except Exception as e:
        history_text = "Историю не удалось загрузить."

    # Формируем промпт для DeepSeek
    prompt = f"""Ты — {contact_name} (так меня зовут). Твоя задача — ответить на сообщение от {contact_name} так, как ответил бы я лично.
Вот примеры моих недавних сообщений этому человеку:
{history_text}

Теперь я получил от него сообщение:
"{event.message.text}"

Напиши ответ в моём стиле (используй мои любимые фразы, эмодзи, краткость). Ответ должен быть не длиннее 2-3 предложений."""

    # Отправляем запрос в DeepSeek
    try:
        deepseek_entity = await client.get_entity(DEEPSEEK_USERNAME)
        await client.send_message(deepseek_entity, prompt)

        # Ждём ответ от DeepSeek (до 20 секунд)
        for _ in range(20):
            await asyncio.sleep(1)
            async for msg in client.iter_messages(deepseek_entity, limit=1):
                if msg.text and not msg.out and msg.date > event.date:
                    # Отправляем ответ другу
                    await client.send_message(contact_id, msg.text)
                    return

        # Если не дождались — дежурный ответ
        await client.send_message(contact_id, "Привет! Я сейчас в небе, связь нестабильна. Отпишусь, как только приземлюсь!")
    except Exception as e:
        # Если что-то пошло не так (бот недоступен и т.п.)
        await client.send_message(contact_id, "Извини, я сейчас не могу ответить, но обязательно напишу позже!")

async def main():
    await client.start(phone=PHONE)
    print("✅ Секретарь запущен и слушает сообщения...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
