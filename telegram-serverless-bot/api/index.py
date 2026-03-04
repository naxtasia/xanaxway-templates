import os
import json
import httpx
import time
import base64
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

app = FastAPI()

# --- (Vercel Environment Variables) ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
AI_API_TOKEN = os.getenv("AI_API_TOKEN")
AI_ENDPOINT = "https://api.xanaxway.com/v4/generative/model/completions"
MODELS_ENDPOINT = "https://api.xanaxway.com/v1/models"
LOGO_URL = "https://cdn.xanaxway.com/brand/xanaxway-llm-logo.jpg"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")  # Örnek: "kullanici_adi/repo_adi"
GITHUB_FILENAME = os.getenv("GITHUB_FILENAME", "bot_settings.json")
# örnek format, [123456789]
AUTHORIZED_USERS = []
RATE_LIMIT_SECONDS = 5

# --- GLOBAL DEĞİŞKENLER ---
bot_settings = {
    "system_prompt": "Sen yardımsever bir asistansın.",
    "current_model": "openai/gpt-4-mini"
}
user_states = {}
last_request_time = {}
user_memories = {}

ptb_app = Application.builder().token(BOT_TOKEN).build()

# --- GITHUB API ---

async def get_settings_from_github():
    """Ayarları doğrudan GitHub'dan çeker."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return bot_settings

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILENAME}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                content_b64 = resp.json()['content']
                content_str = base64.b64decode(content_b64).decode("utf-8")
                return json.loads(content_str)
    except Exception as e:
        print(f"GitHub'dan ayarlar çekilemedi: {e}")
    
    return bot_settings

async def save_settings_to_github(new_settings):
    """Ayarları GitHub reposuna kaydeder (Commit atar)."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILENAME}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # 1. Mevcut dosyanın SHA değerini al (Güncelleme için zorunlu)
            res = await client.get(url, headers=headers)
            sha = res.json().get("sha") if res.status_code == 200 else None
            
            # 2. İçeriği Base64 formatına çevir
            content_str = json.dumps(new_settings, indent=4, ensure_ascii=False)
            content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
            
            payload = {
                "message": "Bot ayarları güncellendi",
                "content": content_b64
            }
            if sha:
                payload["sha"] = sha
                
            # 3. Dosyayı güncelle
            put_res = await client.put(url, headers=headers, json=payload)
            return put_res.status_code in [200, 201]
    except Exception as e:
        print(f"GitHub'a kaydedilemedi: {e}")
        return False

# --- YAPAY ZEKA FONKSİYONU ---

async def ask_ai(user_id, user_message):
    headers = {
        "Authorization": f"Bearer {AI_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    if user_id not in user_memories:
        user_memories[user_id] = []
    
    user_memories[user_id].append({"role": "user", "content": user_message})
    
    if len(user_memories[user_id]) > 6:
        user_memories[user_id] = user_memories[user_id][-6:]

    full_messages = [{"role": "system", "content": bot_settings["system_prompt"]}] + user_memories[user_id]

    payload = {
        "model": bot_settings["current_model"],
        "messages": full_messages,
        "generation_config": {"temperature": 0.6, "max_tokens": 500},
        "stream": False
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(AI_ENDPOINT, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            ai_reply = data['choices'][0]['message']['content']
        
        user_memories[user_id].append({"role": "assistant", "content": ai_reply})
        return ai_reply
    except Exception as e:
        return f"❌ AI Yanıt Hatası: {str(e)}"

# --- TELEGRAM BOT HANDLERLARI ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_settings
    # Başlangıçta en güncel ayarları GitHub'dan çek
    bot_settings = await get_settings_from_github()
    
    keyboard = [[
        InlineKeyboardButton("📜 Sistem Talimatları", callback_data='sys_instr'),
        InlineKeyboardButton("🚀 Sohbeti Başlat", callback_data='start_chat')
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "Merhaba, ben XanaxWay tarafından güçlendirilmiş üretken yapay zeka tabanlı bir asistanım. "
        f"Şu anda {bot_settings['current_model']} modelini kullanıyorsunuz."
    )
    
    await context.bot.send_photo(
        chat_id=update.effective_chat.id, 
        photo=LOGO_URL,
        caption=welcome_text, 
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_settings
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == 'sys_instr':
        if user_id not in AUTHORIZED_USERS:
            await query.message.reply_text("⛔ Yetkiniz yok!")
            return
        
        admin_keyboard = [
            [InlineKeyboardButton("✍️ Talimatı Değiştir", callback_data='change_prompt')],
            [InlineKeyboardButton("🤖 Model Seç", callback_data='list_models')],
            [InlineKeyboardButton("🧹 Hafızaları Temizle", callback_data='clear_all_mem')],
            [InlineKeyboardButton("⬅️ Geri", callback_data='back_to_start')]
        ]
        status_text = (
            f"**🛠 YÖNETİM PANELİ**\n\n"
            f"**Aktif Model:** `{bot_settings['current_model']}`\n"
            f"**Aktif Talimat:** `{bot_settings['system_prompt']}`"
        )
        await query.edit_message_caption(caption=status_text, reply_markup=InlineKeyboardMarkup(admin_keyboard), parse_mode="Markdown")

    elif query.data == 'clear_all_mem':
        user_memories.clear()
        await query.message.reply_text("🧹 Tüm kullanıcıların konuşma geçmişi temizlendi.")

    elif query.data == 'change_prompt':
        user_states[user_id] = "waiting_new_prompt"
        await query.message.reply_text("📝 Yeni sistem talimatını girin:")

    elif query.data == 'list_models':
        headers = {"Authorization": f"Bearer {AI_API_TOKEN}"}
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(MODELS_ENDPOINT, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                models = data.get("data", [])
            
            # Sadece ilk 15 modeli listeliyoruz (Telegram sınırlarını aşmamak için)
            model_kb = []
            for m in models[:15]:
                model_kb.append([InlineKeyboardButton(f"🔹 {m['id']}", callback_data=f"setmod_{m['id']}")])
            
            model_kb.append([InlineKeyboardButton("⬅️ Geri", callback_data='sys_instr')])
            await query.edit_message_caption(caption="🤖 **Model Seçimi:**", reply_markup=InlineKeyboardMarkup(model_kb))
        except Exception as e:
            await query.message.reply_text(f"❌ Modeller çekilemedi. Hata Detayı: {str(e)}")

    elif query.data.startswith('setmod_'):
        new_model = query.data.replace('setmod_', '')
        bot_settings["current_model"] = new_model
        
        # Değişikliği GitHub'a kaydet
        success = await save_settings_to_github(bot_settings)
        if success:
            await query.message.reply_text(f"✅ Model seçildi ve kalıcı olarak kaydedildi: `{bot_settings['current_model']}`")
        else:
            await query.message.reply_text(f"⚠️ Model seçildi: `{bot_settings['current_model']}` (Ancak GitHub'a kaydedilemedi, repo ayarlarını kontrol edin)")

    elif query.data == 'start_chat':
        user_states[user_id] = "chatting"
        await query.message.reply_text("🚀 Sohbet modülümüz aktif! Geçmişinizi hatırlayarak cevap vereceğim.")

    elif query.data == 'back_to_start':
        await query.message.delete()
        await start(update, context)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_settings
    user_id = update.effective_user.id
    state = user_states.get(user_id)
    text = update.message.text

    if state == "waiting_new_prompt" and user_id in AUTHORIZED_USERS:
        bot_settings["system_prompt"] = text
        user_states[user_id] = None
        
        # Değişikliği GitHub'a kaydet
        success = await save_settings_to_github(bot_settings)
        if success:
            await update.message.reply_text("✅ Yeni talimat kaydedildi ve GitHub ile senkronize edildi.")
        else:
            await update.message.reply_text("⚠️ Yeni talimat geçici olarak kaydedildi (GitHub senkronizasyonu başarısız).")
        return

    if state == "chatting":
        current_time = time.time()
        if user_id in last_request_time and (current_time - last_request_time[user_id] < RATE_LIMIT_SECONDS):
            await update.message.reply_text(f"⚠️ {RATE_LIMIT_SECONDS} saniye beklemeniz gerekiyor.")
            return
        
        last_request_time[user_id] = current_time
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        response = await ask_ai(user_id, text)
        await update.message.reply_text(response)
    else:
        if user_id not in AUTHORIZED_USERS:
            await update.message.reply_text("Lütfen /start komutu ile başlayın ve Sohbeti Başlat butonuna tıklayın.")

# --- HANDLER BAĞLANTILARI ---
ptb_app.add_handler(CommandHandler("start", start))
ptb_app.add_handler(CallbackQueryHandler(button_handler))
ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

# --- VERCEL WEBHOOK ENDPOINT ---
@app.post("/api/webhook")
async def telegram_webhook(request: Request):
    if not ptb_app._initialized:
        await ptb_app.initialize()
    
    try:
        req_json = await request.json()
        update = Update.de_json(req_json, ptb_app.bot)
        await ptb_app.process_update(update)
    except Exception as e:
        print(f"Webhook Hatası: {e}")
        
    return {"status": "ok"}
