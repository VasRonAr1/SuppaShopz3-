



# Файл для хранения списка зарегистрированных чатов

# Список разрешённых @username в Телеграм


import logging
import json
import os
import asyncio
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputMediaPhoto, InputMediaVideo, InputMediaDocument,
    InputMediaAudio, InputMediaAnimation,
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters,
)

# --- настройки -------------------------------------------------
BOT_TOKEN = '7781913191:AAGmxczdLZv6g4Vsw6sK_aJvOHEEKMcBX50'            # вставьте токен бота
ALLOWED_USERNAMES = {  'SupaShopz', 'SpammBotss' } # кому разрешено пользоваться
STATE_WAIT = 'await_broadcast'      # флаг ожидания сообщения
registered_chats = []               # список чатов

# --- служебные функции ----------------------------------------
def load_chats():
    global registered_chats
    if os.path.exists('chats.json'):
        with open('chats.json', encoding='utf-8') as f:
            registered_chats = json.load(f)

def save_chats():
    with open('chats.json', 'w', encoding='utf-8') as f:
        json.dump(registered_chats, f, ensure_ascii=False, indent=2)

async def broadcast_text(text, context):
    for c in registered_chats:
        try:
            await context.bot.send_message(c['chat_id'], text)
        except Exception as e:
            logging.error(f"{c['chat_id']}: {e}")

async def broadcast_media(group, context):
    for c in registered_chats:
        try:
            await context.bot.send_media_group(c['chat_id'], group)
        except Exception as e:
            logging.error(f"{c['chat_id']}: {e}")

def make_input(msg, caption=False):
    cap = msg.caption if caption else None
    if msg.photo:
        return InputMediaPhoto(msg.photo[-1].file_id, caption=cap)
    if msg.video:
        return InputMediaVideo(msg.video.file_id, caption=cap)
    if msg.document:
        return InputMediaDocument(msg.document.file_id, caption=cap)
    if msg.audio:
        return InputMediaAudio(msg.audio.file_id, caption=cap)
    if msg.animation:
        return InputMediaAnimation(msg.animation.file_id, caption=cap)
    raise ValueError('Неизвестный тип медиа')

# --- команды ---------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username not in ALLOWED_USERNAMES:
        await update.message.reply_text(
            'Hallo, möchtest du auch so einen Bot? '
            'Schreib mir @SpammBotss, du kannst ihn einen Tag lang kostenlos ausprobieren.'
        )
        return
    registered_chats.clear()
    async for ch in context.bot.get_my_chats():
        registered_chats.append({'chat_id': ch.id, 'title': ch.title or str(ch.id)})
    save_chats()

    kb = [
        [InlineKeyboardButton('📂 Chats ansehen', callback_data='view'),
         InlineKeyboardButton('📤 Nachricht senden', callback_data='send')],
        [InlineKeyboardButton('🛑 Verteilung stoppen', callback_data='stop')],
    ]
    await update.message.reply_text('📋 Wählen Sie eine Aktion:', reply_markup=InlineKeyboardMarkup(kb))

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('/start – меню\n/help – помощь')

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == 'view':
        txt = '\n'.join(f"{c['chat_id']}: {c['title']}" for c in registered_chats) or '—'
        await q.edit_message_text('Список чатов:\n' + txt)
    elif q.data == 'send':
        context.user_data[STATE_WAIT] = True
        await q.edit_message_text('Пришлите сообщение (текст, медиа или альбом до 8 элементов).')
    elif q.data == 'stop':
        context.user_data.pop(STATE_WAIT, None)
        await q.edit_message_text('Рассылка остановлена.')

# --- приём сообщений ------------------------------------------
async def collector(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get(STATE_WAIT):
        return

    msg = update.message
    if not msg.media_group_id:                           # одиночное
        if msg.text or msg.caption:                      # текст
            await broadcast_text(msg.text or msg.caption, context)
        if any([msg.photo, msg.video, msg.document, msg.audio, msg.animation]):  # одиночное медиа
            await broadcast_media([make_input(msg, True)], context)
        context.user_data.pop(STATE_WAIT, None)
        return

    # альбом
    album_store = context.user_data.setdefault('albums', {})
    gid = msg.media_group_id
    album_store.setdefault(gid, []).append(msg)

    await asyncio.sleep(1)                               # ждём остальные элементы
    batch = album_store.pop(gid, [])
    if not batch:
        return
    batch.sort(key=lambda m: m.message_id)
    media = [make_input(m, i == 0) for i, m in enumerate(batch)][:8]  # макс 8
    await broadcast_media(media, context)
    context.user_data.pop(STATE_WAIT, None)

# --- запуск ----------------------------------------------------
def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')
    load_chats()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, collector))

    app.run_polling()

if __name__ == '__main__':
    main()
