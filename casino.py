# ================= PARTIE 1 =================
# Imports et configuration de base

import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import random
import asyncio
from datetime import datetime, timedelta
import os

# --- Configuration ---
# Récupérer le token depuis les variables d'environnement
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise ValueError("La variable d'environnement DISCORD_BOT_TOKEN n'est pas définie.")

# ID de votre serveur (à remplacer)
GUILD_ID = 1454859381169590527  # Remplacez par l'ID de votre serveur

# IDs importants
ADMIN_ROLE_ID = 1454933872142979215
CASINO_ROLE_ID = 1499809955841310871
COMMAND_CATEGORY_ID = 1498394439079559318
GIVEAWAY_CHANNEL_ID = 1498394479319716040

# Fichiers de données
DATA_FILE = "economy_data.json"
GAME_STATES_FILE = "game_states.json"

# Initialisation du bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= Gestion des données =================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_games():
    if os.path.exists(GAME_STATES_FILE):
        with open(GAME_STATES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_games(data):
    with open(GAME_STATES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

economy = load_data()
game_states = load_games()

def get_user_data(user_id):
    user_id = str(user_id)
    if user_id not in economy:
        economy[user_id] = {"pocket": 0, "bank": 0}
        save_data(economy)
    return economy[user_id]

def set_user_data(user_id, pocket=None, bank=None):
    user_id = str(user_id)
    if user_id not in economy:
        economy[user_id] = {"pocket": 0, "bank": 0}
    if pocket is not None:
        economy[user_id]["pocket"] = pocket
    if bank is not None:
        economy[user_id]["bank"] = bank
    save_data(economy)

# ================= Vérifications =================
def is_admin(interaction: discord.Interaction):
    return interaction.user.get_role(ADMIN_ROLE_ID) is not None

def has_casino_role(interaction: discord.Interaction):
    return interaction.user.get_role(CASINO_ROLE_ID) is not None

def in_command_category(interaction: discord.Interaction):
    return interaction.channel.category_id == COMMAND_CATEGORY_ID

# ================= Bot events =================
@bot.event
async def on_ready():
    print(f"Bot connecté en tant que {bot.user}")
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Commandes synchronisées : {len(synced)}")
    except Exception as e:
        print(f"Erreur de synchronisation : {e}")
    giveaway_loop.start()
