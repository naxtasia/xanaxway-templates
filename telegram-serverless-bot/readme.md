# 🚀 XanaxWay Serverless Telegram AI Bot

![xanaxway logo](https://cdn.xanaxway.com/brand/xanaxway-llm-logo.jpg)  
  
  **A fully serverless, ultra-fast, and memory-enabled Telegram AI Bot powered by the XanaxWay Neural API. Deploy for FREE on Vercel.**[Live Demo: @xanaxway_cloud_bot](https://t.me/xanaxway_cloud_bot) • [XanaxWay API Docs](https://xanaxway.com)

---

## ✨ Features (Özellikler)
- **☁️ 100% Serverless (Zero Cost):** Designed to run on Vercel Webhooks. No VPS or 24/7 server required.
- **🧠 Contextual Memory:** Remembers the last 6 messages per user for fluid conversations.
- **⚡ Ultra-Fast Async Architecture:** Built with `FastAPI` and `httpx` for non-blocking, lightning-fast AI responses.
- **🎛️ Dynamic Admin Panel:** Change the AI model and system prompt directly via Telegram Inline Buttons.
- **💾 GitHub State Management:** Saves bot configurations directly to a GitHub Repo instead of a database, bypassing Vercel's stateless nature!
- **🛡️ Built-in Rate Limiting:** Prevents spam and API abuse.

---

## 🛠️ Installation & Deployment (Kurulum)

You can deploy your own AI bot in 3 minutes using Vercel.

### Step 1: Clone the Repository
```bash
git clone https://github.com/naxtasia/xanaxway-templates.git
cd telegram-serverless-bot
```

### Step 2: Set Up Environment Variables (.env)
Add the following variables to your Vercel Project settings:
- `BOT_TOKEN` : Your Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- `AI_API_TOKEN` : Your XanaxWay API Key
- `GITHUB_TOKEN` : Your GitHub Personal Access Token (for saving settings)
- `GITHUB_REPO` : e.g., `username/repo_name`

### Step 3: Deploy to Vercel
1. Push this code to your GitHub.
2. Go to Vercel and import your repository.
3. Set the Root Directory to the folder containing the `api` folder.
4. Deploy!

### Step 4: Set Telegram Webhook
Run this URL in your browser to connect Telegram to your Vercel App:
```text
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://<YOUR-VERCEL-DOMAIN>.vercel.app/api/webhook
```

---

## 🤖 Supported Models (XanaxWay API)
This bot uses the [XanaxWay Gateway](https://xanaxway.com), seamlessly switching between top-tier models:
- `openai/gpt-4-mini`
- `xanaxway/nexa-7.1-mini`
- `meta/llama-3`
- *And many more...*

---

## 👨‍💻 Architecture (How it works)
Unlike traditional polling bots (`application.run_polling()`), this bot uses a **Webhook Endpoint** (`/api/webhook`). When a user sends a message, Telegram sends a POST request to Vercel. Vercel spins up the Python instance, processes the AI request asynchronously via `httpx`, replies to the user, and goes back to sleep. **0$ Server Cost.**

---

## 📜 License
Developed by **Naxtasia** & **XanaxWay Neural Systems**
