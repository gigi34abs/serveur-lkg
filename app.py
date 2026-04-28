import os
import discord
from discord.ext import commands
import asyncio

# --- CONFIGURATION ---
# On récupère le token de façon sécurisée via les variables d'environnement
TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # ← CHANGÉ ICI

# Configuration des permissions (Intents)
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- CHARGEMENT DES EXTENSIONS (tes fichiers logs, ticket, gestion) ---
async def load_extensions():
    # Liste de tes fichiers sans le .py
    extensions = ['logs', 'ticket', 'admin', 'lock',]
    for ext in extensions:
        try:
            await bot.load_extension(ext)
            print(f"✅ Extension chargée : {ext}")
        except Exception as e:
            print(f"❌ Impossible de charger {ext} : {e}")

@bot.event
async def on_ready():
    print(f'🚀 Connecté en tant que : {bot.user.name}')
    # Synchronisation des commandes slash (/)
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
            print("❌ ERREUR : Aucun TOKEN trouvé dans les variables d'environnement !")

if __name__ == "__main__":
    asyncio.run(main())
