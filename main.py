import os
import asyncio
import discord
from discord.ext import commands
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Модель Groq. Если ошибка, попробуй llama-3.1-8b-instant
MODEL = "llama-3.3-70b-versatile"

groq = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


def ask_groq(user_text: str) -> str:
    response = groq.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "Ты простой полезный бот в Discord. Отвечай кратко и понятно."
            },
            {
                "role": "user",
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

    # Discord ограничивает сообщения до 2000 символов
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