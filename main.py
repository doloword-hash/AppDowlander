import os
import asyncio
import threading
import discord
from discord.ext import commands
from openai import OpenAI
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "llama-3.3-70b-versatile"

groq = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- ХИТРЫЙ ТРЮК: Мини-веб-сервер для Render и UptimeRobot ---
app = Flask(__name__)

@app.route("/")
def home():
    return "Бот работает и ждет пинга!"

def run_flask():
    # Render автоматически передает переменную окружения PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# Запускаем веб-сервер в отдельном потоке, чтобы он не блокировал бота
threading.Thread(target=run_flask, daemon=True).start()
# --------------------------------------------------------------

def ask_groq(user_text: str) -> str:
    response = groq.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system", # Пробелы убраны
                "content": "Ты простой полезный бот в Discord. Отвечай кратко и понятно."
            },
            {
                "role": "user", # Пробелы убраны
                "content": user_text
            }
        ],
        temperature=0.7,
        max_tokens=500
    )
    return response.choices[0].message.content.strip()

@bot.event
async def on_ready():
    print(f"Бот запущен как {bot.user}")

@bot.command(name="ai")
async def ai_command(ctx, *, text: str):
    async with ctx.typing():
        try:
            answer = await asyncio.to_thread(ask_groq, text)
        except Exception as error:
            print("Ошибка Groq:", error)
            await ctx.reply("Ошибка при запросе к Groq. Проверь API-ключ или модель.")
            return
        
        for i in range(0, len(answer), 2000):
            await ctx.reply(
                answer[i:i + 2000],
                mention_author=False
            )

@ai_command.error
async def ai_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply("Использование: `!ai твой вопрос`")

bot.run(DISCORD_TOKEN)
