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

# ================= PARTIE 3 =================
# Commandes du groupe /banque

@bot.tree.command(name="banque", description="Gestion de votre banque")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
async def banque(interaction: discord.Interaction):
    pass

@banque.command(name="voir", description="Voir votre argent en poche et en banque")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
async def banque_voir(interaction: discord.Interaction):
    if not in_command_category(interaction):
        await interaction.response.send_message("Cette commande est réservée aux salons de la catégorie Casino.", ephemeral=True)
        return
    if not has_casino_role(interaction):
        await interaction.response.send_message("Vous n'avez pas le rôle Casino.", ephemeral=True)
        return
    data = get_user_data(interaction.user.id)
    embed = discord.Embed(title="Votre situation financière", color=discord.Color.green())
    embed.add_field(name="Argent en poche", value=f"{data['pocket']}€", inline=True)
    embed.add_field(name="Argent en banque", value=f"{data['bank']}€", inline=True)
    embed.add_field(name="Total", value=f"{data['pocket'] + data['bank']}€", inline=False)
    await interaction.response.send_message(embed=embed)

@banque.command(name="depot", description="Déposer de l'argent en banque")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
@app_commands.describe(montant="Montant à déposer")
async def banque_depot(interaction: discord.Interaction, montant: int):
    if not in_command_category(interaction):
        await interaction.response.send_message("Cette commande est réservée aux salons de la catégorie Casino.", ephemeral=True)
        return
    if not has_casino_role(interaction):
        await interaction.response.send_message("Vous n'avez pas le rôle Casino.", ephemeral=True)
        return
    if montant <= 0:
        await interaction.response.send_message("Le montant doit être positif.", ephemeral=True)
        return
    data = get_user_data(interaction.user.id)
    if data["pocket"] < montant:
        await interaction.response.send_message("Vous n'avez pas assez d'argent en poche.", ephemeral=True)
        return
    data["pocket"] -= montant
    data["bank"] += montant
    set_user_data(interaction.user.id, pocket=data["pocket"], bank=data["bank"])
    await interaction.response.send_message(f"Vous avez déposé {montant}€ en banque. Nouveau solde en poche : {data['pocket']}€, banque : {data['bank']}€.")

@banque.command(name="retrait", description="Retirer de l'argent de la banque")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
@app_commands.describe(montant="Montant à retirer")
async def banque_retrait(interaction: discord.Interaction, montant: int):
    if not in_command_category(interaction):
        await interaction.response.send_message("Cette commande est réservée aux salons de la catégorie Casino.", ephemeral=True)
        return
    if not has_casino_role(interaction):
        await interaction.response.send_message("Vous n'avez pas le rôle Casino.", ephemeral=True)
        return
    if montant <= 0:
        await interaction.response.send_message("Le montant doit être positif.", ephemeral=True)
        return
    data = get_user_data(interaction.user.id)
    if data["bank"] < montant:
        await interaction.response.send_message("Vous n'avez pas assez d'argent en banque.", ephemeral=True)
        return
    data["bank"] -= montant
    data["pocket"] += montant
    set_user_data(interaction.user.id, pocket=data["pocket"], bank=data["bank"])
    await interaction.response.send_message(f"Vous avez retiré {montant}€ de la banque. Nouveau solde en poche : {data['pocket']}€, banque : {data['bank']}€.")

@banque.command(name="argent", description="Voir l'argent d'un autre membre")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
@app_commands.describe(membre="Le membre à consulter")
async def banque_argent(interaction: discord.Interaction, membre: discord.Member):
    if not in_command_category(interaction):
        await interaction.response.send_message("Cette commande est réservée aux salons de la catégorie Casino.", ephemeral=True)
        return
    if not has_casino_role(interaction):
        await interaction.response.send_message("Vous n'avez pas le rôle Casino.", ephemeral=True)
        return
    data = get_user_data(membre.id)
    embed = discord.Embed(title=f"Argent de {membre.display_name}", color=discord.Color.blue())
    embed.add_field(name="Poche", value=f"{data['pocket']}€", inline=True)
    embed.add_field(name="Banque", value=f"{data['bank']}€", inline=True)
    embed.add_field(name="Total", value=f"{data['pocket'] + data['bank']}€", inline=False)
    await interaction.response.send_message(embed=embed)

@banque.command(name="classement", description="Classement des plus riches du serveur")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
async def banque_classement(interaction: discord.Interaction):
    if not in_command_category(interaction):
        await interaction.response.send_message("Cette commande est réservée aux salons de la catégorie Casino.", ephemeral=True)
        return
    if not has_casino_role(interaction):
        await interaction.response.send_message("Vous n'avez pas le rôle Casino.", ephemeral=True)
        return
    # Trier par total (pocket + bank)
    sorted_users = sorted(economy.items(), key=lambda x: x[1]["pocket"] + x[1]["bank"], reverse=True)
    embed = discord.Embed(title="🏆 Classement des plus riches", color=discord.Color.gold())
    description = ""
    for i, (user_id, data) in enumerate(sorted_users[:10], 1):
        member = interaction.guild.get_member(int(user_id))
        if member:
            name = member.display_name
        else:
            name = f"Utilisateur inconnu ({user_id})"
        total = data["pocket"] + data["bank"]
        description += f"{i}. {name} : {total}€\n"
    if not description:
        description = "Aucun joueur enregistré."
    embed.description = description
    await interaction.response.send_message(embed=embed)

# ================= PARTIE 4 =================
# Commandes du groupe /argent

@bot.tree.command(name="argent", description="Gestion des transactions entre joueurs")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
async def argent(interaction: discord.Interaction):
    pass

@argent.command(name="donner", description="Donner de l'argent à un autre membre")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
@app_commands.describe(membre="Le bénéficiaire", montant="Montant à donner (minimum 1)")
async def argent_donner(interaction: discord.Interaction, membre: discord.Member, montant: int):
    if not in_command_category(interaction):
        await interaction.response.send_message("Cette commande est réservée aux salons de la catégorie Casino.", ephemeral=True)
        return
    if not has_casino_role(interaction):
        await interaction.response.send_message("Vous n'avez pas le rôle Casino.", ephemeral=True)
        return
    if montant < 1:
        await interaction.response.send_message("Le montant minimum est de 1€.", ephemeral=True)
        return
    if membre.id == interaction.user.id:
        await interaction.response.send_message("Vous ne pouvez pas vous donner de l'argent à vous-même.", ephemeral=True)
        return
    data = get_user_data(interaction.user.id)
    if data["pocket"] < montant:
        await interaction.response.send_message("Vous n'avez pas assez d'argent en poche.", ephemeral=True)
        return
    data["pocket"] -= montant
    set_user_data(interaction.user.id, pocket=data["pocket"])
    # Ajouter au destinataire
    dest_data = get_user_data(membre.id)
    dest_data["pocket"] += montant
    set_user_data(membre.id, pocket=dest_data["pocket"])
    await interaction.response.send_message(f"Vous avez donné {montant}€ à {membre.mention}.")

@argent.command(name="voler", description="Voler de l'argent en poche d'un membre (1 chance sur 3)")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
@app_commands.describe(membre="La victime", montant="Montant à voler")
async def argent_voler(interaction: discord.Interaction, membre: discord.Member, montant: int):
    if not in_command_category(interaction):
        await interaction.response.send_message("Cette commande est réservée aux salons de la catégorie Casino.", ephemeral=True)
        return
    if not has_casino_role(interaction):
        await interaction.response.send_message("Vous n'avez pas le rôle Casino.", ephemeral=True)
        return
    if montant <= 0:
        await interaction.response.send_message("Le montant doit être positif.", ephemeral=True)
        return
    if membre.id == interaction.user.id:
        await interaction.response.send_message("Vous ne pouvez pas vous voler vous-même.", ephemeral=True)
        return
    # Vérifier que la victime a assez d'argent en poche
    victime_data = get_user_data(membre.id)
    if victime_data["pocket"] < montant:
        await interaction.response.send_message(f"{membre.mention} n'a pas assez d'argent en poche pour ce vol.", ephemeral=True)
        return
    # Vérifier que le voleur a assez pour la pénalité en cas d'échec (il perd le montant tenté)
    voleur_data = get_user_data(interaction.user.id)
    if voleur_data["pocket"] < montant:
        await interaction.response.send_message("Vous n'avez pas assez d'argent pour couvrir la perte en cas d'échec.", ephemeral=True)
        return
    # Tirage au sort : 1/3 de réussite
    if random.randint(1, 3) == 1:
        # Réussite : voler le montant
        victime_data["pocket"] -= montant
        set_user_data(membre.id, pocket=victime_data["pocket"])
        voleur_data["pocket"] += montant
        set_user_data(interaction.user.id, pocket=voleur_data["pocket"])
        await interaction.response.send_message(f"✅ Vous avez réussi à voler {montant}€ à {membre.mention} !")
    else:
        # Échec : perdre le montant (ajouté à la victime ? ou perdu ? Le texte dit "on perd la somme qu'on voulait voler" donc perdue pour le voleur, pas pour la victime)
        # On enlève au voleur sans rien donner à la victime (l'argent est perdu)
        voleur_data["pocket"] -= montant
        set_user_data(interaction.user.id, pocket=voleur_data["pocket"])
        await interaction.response.send_message(f"❌ Échec ! Vous avez perdu {montant}€ en tentant de voler {membre.mention}.")

# ================= PARTIE 5 =================
# Système de giveaway automatique

giveaway_running = False

@tasks.loop(minutes=30)
async def giveaway_loop():
    now = datetime.now()
    # Entre 14h et 20h (heure locale du bot)
    if not (14 <= now.hour < 20):
        return
    channel = bot.get_channel(GIVEAWAY_CHANNEL_ID)
    if channel is None:
        return
    # Vérifier qu'un giveaway n'est pas déjà en cours
    global giveaway_running
    if giveaway_running:
        return
    giveaway_running = True
    try:
        # Message de giveaway
        embed = discord.Embed(
            title="🎉 Giveaway automatique !",
            description="Réagissez avec 🎉 pour participer !\nTirage dans 10 minutes.\nGain : **500€**",
            color=discord.Color.purple()
        )
        msg = await channel.send(embed=embed)
        await msg.add_reaction("🎉")
        await asyncio.sleep(600)  # 10 minutes
        # Récupérer les réactions
        msg = await channel.fetch_message(msg.id)
        users = []
        async for user in msg.reactions[0].users():
            if not user.bot:
                users.append(user)
        if users:
            winner = random.choice(users)
            # Ajouter 500€ en poche
            data = get_user_data(winner.id)
            data["pocket"] += 500
            set_user_data(winner.id, pocket=data["pocket"])
            await channel.send(f"🎉 Félicitations {winner.mention} ! Vous avez gagné 500€ !")
        else:
            await channel.send("Personne n'a participé, dommage !")
    finally:
        giveaway_running = False
