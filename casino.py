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

# ================= PARTIE 2 =================
# Commandes du groupe /jouer

class AcceptView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="J'accepte les règles", style=discord.ButtonStyle.success, custom_id="accept_rules")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(CASINO_ROLE_ID)
        if role is None:
            await interaction.response.send_message("Le rôle Casino n'existe pas.", ephemeral=True)
            return
        if role in interaction.user.roles:
            await interaction.response.send_message("Vous avez déjà ce rôle.", ephemeral=True)
            return
        await interaction.user.add_roles(role)
        # Initialiser le compte à 100€ en poche
        user_data = get_user_data(interaction.user.id)
        if user_data["pocket"] == 0 and user_data["bank"] == 0:
            set_user_data(interaction.user.id, pocket=100, bank=0)
        await interaction.response.send_message(f"Félicitations ! Vous avez reçu le rôle {role.mention} et 100€ ont été ajoutés à votre compte.", ephemeral=True)

@bot.tree.command(name="jouer", description="Commandes pour gérer le casino")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
async def jouer(interaction: discord.Interaction):
    # Cette commande est un groupe, on utilise des sous-commandes
    pass

@jouer.command(name="role", description="Donner le rôle Casino avec message d'acceptation (admin uniquement)")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
async def jouer_role(interaction: discord.Interaction):
    if not is_admin(interaction):
        await interaction.response.send_message("Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)
        return
    embed = discord.Embed(
        title="⚠️ Avertissement Casino",
        description="En acceptant ce rôle, vous pourrez participer aux jeux d'argent du serveur.\n"
                    "Vous devez vous contrôler et jouer de manière responsable.\n"
                    "Si vous perdez trop, vous pourrez demander à un admin de vous retirer.\n"
                    "En cliquant sur le bouton ci-dessous, vous acceptez ces conditions.",
        color=discord.Color.orange()
    )
    view = AcceptView()
    await interaction.response.send_message(embed=embed, view=view)

@jouer.command(name="enlever", description="Retirer un membre du casino (admin uniquement)")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
@app_commands.describe(membre="Le membre à retirer")
async def jouer_enlever(interaction: discord.Interaction, membre: discord.Member):
    if not is_admin(interaction):
        await interaction.response.send_message("Vous n'avez pas la permission.", ephemeral=True)
        return
    role = interaction.guild.get_role(CASINO_ROLE_ID)
    if role not in membre.roles:
        await interaction.response.send_message(f"{membre.mention} n'a pas le rôle Casino.", ephemeral=True)
        return
    await membre.remove_roles(role)
    # Supprimer les données économiques (réinitialisation)
    user_id = str(membre.id)
    if user_id in economy:
        del economy[user_id]
        save_data(economy)
    await interaction.response.send_message(f"{membre.mention} a été retiré du casino et ses données ont été effacées.", ephemeral=True)
