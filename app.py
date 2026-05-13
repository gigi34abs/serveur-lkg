import os
import discord
from discord.ext import commands
import asyncio
from flask import Flask
import threading

# --- CONFIGURATION ---
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- UPTIMEROBOT PING ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive! ✅", 200

def run_flask():
    app.run(host='0.0.0.0', port=8080)

flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

# --- CHARGEMENT DES EXTENSIONS ---
async def load_extensions():
    extensions = ['banip', 'parler', 'points', 'clear', 'logs', 'ticket', 'admin', 'lock', 'regles', 'invite']
    for ext in extensions:
        try:
            await bot.load_extension(ext)
            print(f"✅ Extension chargée : {ext}")
        except Exception as e:
            print(f"❌ Impossible de charger {ext} : {e}")

@bot.event
async def on_ready():
    print(f'🚀 Connecté en tant que : {bot.user.name}')
    try:
        synced = await bot.tree.sync()
        print(f"🔗 {len(synced)} commandes slash synchronisées !")
    except Exception as e:
        print(f"❌ Erreur de synchronisation : {e}")

async def main():
    async with bot:
        await load_extensions()
        if TOKEN:
            await bot.start(TOKEN)
        else:
            print("❌ ERREUR : Aucun TOKEN trouvé !")

if __name__ == "__main__":
    asyncio.run(main())
