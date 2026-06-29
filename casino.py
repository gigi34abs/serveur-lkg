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

# ================= PARTIE 6.1 =================
# Jeu Mystère

@bot.tree.command(name="jeux", description="Jeux de casino")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
async def jeux(interaction: discord.Interaction):
    pass

@jeux.command(name="mystere", description="Devinez si votre carte est plus haute que celle du bot")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
async def jeux_mystere(interaction: discord.Interaction):
    if not in_command_category(interaction):
        await interaction.response.send_message("Cette commande est réservée aux salons de la catégorie Casino.", ephemeral=True)
        return
    if not has_casino_role(interaction):
        await interaction.response.send_message("Vous n'avez pas le rôle Casino.", ephemeral=True)
        return
    data = get_user_data(interaction.user.id)
    total = data["pocket"] + data["bank"]
    # Déterminer le pari requis
    if total < 100:
        await interaction.response.send_message("Vous devez avoir au moins 100€ pour jouer.", ephemeral=True)
        return
    elif 100 <= total <= 1000:
        required_bet = 50
    elif 1000 < total <= 5000:
        required_bet = 150
    else:
        required_bet = 250
    # Vérifier qu'il a assez en poche (car le pari est prélevé ? Non, le texte dit "parie une somme" mais le gain/perte sont fixes.
    # On va exiger qu'il ait le required_bet en poche (comme mise de départ)
    if data["pocket"] < required_bet:
        await interaction.response.send_message(f"Vous devez avoir au moins {required_bet}€ en poche pour jouer.", ephemeral=True)
        return
    # On ne prélève pas la mise, on l'utilise comme condition.
    # Générer les cartes
    user_card = random.randint(1, 14)
    bot_card = random.randint(1, 14)
    # Afficher la carte du joueur
    embed = discord.Embed(title="🃏 Carte mystère", description=f"Votre carte est : **{user_card}**\nDevinez : plus haute, plus basse ou égale ?", color=discord.Color.blue())
    # Utiliser un view pour les choix
    class MystereView(discord.ui.View):
        def __init__(self, user_id, bot_card, required_bet):
            super().__init__(timeout=60)
            self.user_id = user_id
            self.bot_card = bot_card
            self.required_bet = required_bet
            self.responded = False

        @discord.ui.button(label="Plus haute", style=discord.ButtonStyle.green)
        async def higher(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.process(interaction, "higher")

        @discord.ui.button(label="Plus basse", style=discord.ButtonStyle.red)
        async def lower(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.process(interaction, "lower")

        @discord.ui.button(label="Égale", style=discord.ButtonStyle.grey)
        async def equal(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.process(interaction, "equal")

        async def process(self, interaction: discord.Interaction, guess):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("Ce n'est pas votre partie.", ephemeral=True)
                return
            if self.responded:
                await interaction.response.send_message("Vous avez déjà répondu.", ephemeral=True)
                return
            self.responded = True
            self.stop()
            # Résultat
            result = ""
            if guess == "higher":
                if self.bot_card > user_card:
                    result = "perdu"
                elif self.bot_card < user_card:
                    result = "gagne"
                else:
                    result = "perdu"  # Égalité considérée comme perdue ?
            elif guess == "lower":
                if self.bot_card < user_card:
                    result = "gagne"
                else:
                    result = "perdu"
            else:  # equal
                if self.bot_card == user_card:
                    result = "gagne"
                else:
                    result = "perdu"
            # Appliquer les gains/pertes
            data = get_user_data(interaction.user.id)
            if result == "gagne":
                data["pocket"] += 100
                msg = f"✅ La carte du bot était {self.bot_card}. Vous gagnez 100€ !"
            else:
                data["pocket"] -= 300
                msg = f"❌ La carte du bot était {self.bot_card}. Vous perdez 300€."
            set_user_data(interaction.user.id, pocket=data["pocket"])
            await interaction.response.edit_message(content=msg, embed=None, view=None)

    view = MystereView(interaction.user.id, bot_card, required_bet)
    await interaction.response.send_message(embed=embed, view=view)

# ================= PARTIE 6.2 =================
# Coinflip 1v1

class CoinflipView(discord.ui.View):
    def __init__(self, challenger, opponent, amount):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.opponent = opponent
        self.amount = amount
        self.accepted = False

    @discord.ui.button(label="Accepter le défi", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("Ce n'est pas votre défi.", ephemeral=True)
            return
        if self.accepted:
            await interaction.response.send_message("Déjà accepté.", ephemeral=True)
            return
        self.accepted = True
        self.stop()
        # Vérifier que l'adversaire a assez
        opp_data = get_user_data(self.opponent.id)
        if opp_data["pocket"] < self.amount:
            await interaction.response.send_message("Vous n'avez pas assez d'argent pour accepter.", ephemeral=True)
            return
        # Déduire les mises
        chal_data = get_user_data(self.challenger.id)
        chal_data["pocket"] -= self.amount
        set_user_data(self.challenger.id, pocket=chal_data["pocket"])
        opp_data["pocket"] -= self.amount
        set_user_data(self.opponent.id, pocket=opp_data["pocket"])
        # Lancer le coin
        winner = random.choice([self.challenger, self.opponent])
        winner_data = get_user_data(winner.id)
        winner_data["pocket"] += self.amount * 2
        set_user_data(winner.id, pocket=winner_data["pocket"])
        await interaction.response.edit_message(content=f"🪙 Coinflip ! {winner.mention} remporte {self.amount*2}€ !", view=None)

@jeux.command(name="coinflip", description="Défiez un autre joueur en 1v1 (pari égal)")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
@app_commands.describe(adversaire="Le joueur à défier", montant="Montant à parier")
async def jeux_coinflip(interaction: discord.Interaction, adversaire: discord.Member, montant: int):
    if not in_command_category(interaction):
        await interaction.response.send_message("Cette commande est réservée aux salons de la catégorie Casino.", ephemeral=True)
        return
    if not has_casino_role(interaction):
        await interaction.response.send_message("Vous n'avez pas le rôle Casino.", ephemeral=True)
        return
    if montant < 10:
        await interaction.response.send_message("Le montant minimum est de 10€.", ephemeral=True)
        return
    if adversaire.id == interaction.user.id:
        await interaction.response.send_message("Vous ne pouvez pas vous défier vous-même.", ephemeral=True)
        return
    data = get_user_data(interaction.user.id)
    if data["pocket"] < montant:
        await interaction.response.send_message("Vous n'avez pas assez d'argent.", ephemeral=True)
        return
    # Vérifier que l'adversaire a le rôle casino
    if CASINO_ROLE_ID not in [r.id for r in adversaire.roles]:
        await interaction.response.send_message("L'adversaire n'a pas le rôle Casino.", ephemeral=True)
        return
    # Créer un message de défi
    embed = discord.Embed(title="🪙 Défi Coinflip", description=f"{interaction.user.mention} défie {adversaire.mention} pour un pari de {montant}€ !", color=discord.Color.blue())
    view = CoinflipView(interaction.user, adversaire, montant)
    await interaction.response.send_message(embed=embed, view=view)

# ================= PARTIE 6.3 =================
# Duel (Pierre-Feuille-Ciseaux)

class DuelView(discord.ui.View):
    def __init__(self, challenger, opponent, amount):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.opponent = opponent
        self.amount = amount
        self.challenger_choice = None
        self.opponent_choice = None

    @discord.ui.button(label="Pierre", style=discord.ButtonStyle.secondary)
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.set_choice(interaction, "pierre")

    @discord.ui.button(label="Feuille", style=discord.ButtonStyle.secondary)
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.set_choice(interaction, "feuille")

    @discord.ui.button(label="Ciseaux", style=discord.ButtonStyle.secondary)
    async def scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.set_choice(interaction, "ciseaux")

    async def set_choice(self, interaction: discord.Interaction, choice):
        if interaction.user.id not in [self.challenger.id, self.opponent.id]:
            await interaction.response.send_message("Vous ne participez pas à ce duel.", ephemeral=True)
            return
        if interaction.user.id == self.challenger.id:
            if self.challenger_choice is not None:
                await interaction.response.send_message("Vous avez déjà choisi.", ephemeral=True)
                return
            self.challenger_choice = choice
        else:
            if self.opponent_choice is not None:
                await interaction.response.send_message("Vous avez déjà choisi.", ephemeral=True)
                return
            self.opponent_choice = choice
        await interaction.response.send_message(f"Vous avez choisi {choice}.", ephemeral=True)
        if self.challenger_choice and self.opponent_choice:
            self.stop()
            # Déterminer le gagnant
            winner = None
            if self.challenger_choice == self.opponent_choice:
                winner = "draw"
            elif (self.challenger_choice == "pierre" and self.opponent_choice == "ciseaux") or \
                 (self.challenger_choice == "feuille" and self.opponent_choice == "pierre") or \
                 (self.challenger_choice == "ciseaux" and self.opponent_choice == "feuille"):
                winner = self.challenger
            else:
                winner = self.opponent
            # Appliquer les gains
            if winner == "draw":
                # Rendre les mises
                chal_data = get_user_data(self.challenger.id)
                chal_data["pocket"] += self.amount
                set_user_data(self.challenger.id, pocket=chal_data["pocket"])
                opp_data = get_user_data(self.opponent.id)
                opp_data["pocket"] += self.amount
                set_user_data(self.opponent.id, pocket=opp_data["pocket"])
                await interaction.channel.send("Égalité ! Les mises sont remboursées.")
            else:
                loser = self.challenger if winner == self.opponent else self.opponent
                loser_data = get_user_data(loser.id)
                loser_data["pocket"] -= self.amount
                set_user_data(loser.id, pocket=loser_data["pocket"])
                winner_data = get_user_data(winner.id)
                winner_data["pocket"] += self.amount * 2
                set_user_data(winner.id, pocket=winner_data["pocket"])
                await interaction.channel.send(f"{winner.mention} remporte le duel et gagne {self.amount*2}€ !")

@jeux.command(name="duel", description="Défiez un autre joueur à Pierre-Feuille-Ciseaux")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
@app_commands.describe(adversaire="Le joueur à défier", montant="Montant à parier")
async def jeux_duel(interaction: discord.Interaction, adversaire: discord.Member, montant: int):
    if not in_command_category(interaction):
        await interaction.response.send_message("Cette commande est réservée aux salons de la catégorie Casino.", ephemeral=True)
        return
    if not has_casino_role(interaction):
        await interaction.response.send_message("Vous n'avez pas le rôle Casino.", ephemeral=True)
        return
    if montant < 10:
        await interaction.response.send_message("Le montant minimum est de 10€.", ephemeral=True)
        return
    if adversaire.id == interaction.user.id:
        await interaction.response.send_message("Vous ne pouvez pas vous défier vous-même.", ephemeral=True)
        return
    data = get_user_data(interaction.user.id)
    if data["pocket"] < montant:
        await interaction.response.send_message("Vous n'avez pas assez d'argent.", ephemeral=True)
        return
    if CASINO_ROLE_ID not in [r.id for r in adversaire.roles]:
        await interaction.response.send_message("L'adversaire n'a pas le rôle Casino.", ephemeral=True)
        return
    # Vérifier que l'adversaire a assez
    opp_data = get_user_data(adversaire.id)
    if opp_data["pocket"] < montant:
        await interaction.response.send_message("L'adversaire n'a pas assez d'argent.", ephemeral=True)
        return
    # Prélever les mises tout de suite
    data["pocket"] -= montant
    set_user_data(interaction.user.id, pocket=data["pocket"])
    opp_data["pocket"] -= montant
    set_user_data(adversaire.id, pocket=opp_data["pocket"])
    embed = discord.Embed(title="⚔️ Duel", description=f"{interaction.user.mention} vs {adversaire.mention}\nPari : {montant}€\nChoisissez votre coup !", color=discord.Color.red())
    view = DuelView(interaction.user, adversaire, montant)
    await interaction.response.send_message(embed=embed, view=view)

# ================= PARTIE 6.4 =================
# Team Fight (5v5)

class TeamFightView(discord.ui.View):
    def __init__(self, creator, team_size):
        super().__init__(timeout=120)
        self.creator = creator
        self.team1 = [creator]
        self.team2 = []
        self.team_size = team_size
        self.bets = {}  # user_id -> bet
        self.started = False

    @discord.ui.button(label="Rejoindre Équipe 1", style=discord.ButtonStyle.blurple)
    async def join_team1(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.started:
            await interaction.response.send_message("La partie a déjà commencé.", ephemeral=True)
            return
        if interaction.user.id in [m.id for m in self.team1 + self.team2]:
            await interaction.response.send_message("Vous êtes déjà dans une équipe.", ephemeral=True)
            return
        if len(self.team1) >= self.team_size:
            await interaction.response.send_message("L'équipe 1 est pleine.", ephemeral=True)
            return
        self.team1.append(interaction.user)
        await interaction.response.send_message(f"Vous avez rejoint l'équipe 1 ! ({len(self.team1)}/{self.team_size})", ephemeral=True)
        await self.check_start()

    @discord.ui.button(label="Rejoindre Équipe 2", style=discord.ButtonStyle.green)
    async def join_team2(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.started:
            await interaction.response.send_message("La partie a déjà commencé.", ephemeral=True)
            return
        if interaction.user.id in [m.id for m in self.team1 + self.team2]:
            await interaction.response.send_message("Vous êtes déjà dans une équipe.", ephemeral=True)
            return
        if len(self.team2) >= self.team_size:
            await interaction.response.send_message("L'équipe 2 est pleine.", ephemeral=True)
            return
        self.team2.append(interaction.user)
        await interaction.response.send_message(f"Vous avez rejoint l'équipe 2 ! ({len(self.team2)}/{self.team_size})", ephemeral=True)
        await self.check_start()

    async def check_start(self):
        if len(self.team1) == self.team_size and len(self.team2) == self.team_size:
            self.started = True
            # Demander les mises à chaque joueur (ils doivent tous miser la même chose)
            # On va définir une mise de base de 50€ pour simplifier
            bet = 50
            # Vérifier que tous ont assez
            for member in self.team1 + self.team2:
                data = get_user_data(member.id)
                if data["pocket"] < bet:
                    await self.message.channel.send(f"{member.mention} n'a pas assez d'argent (besoin de {bet}€). Annulation.")
                    self.stop()
                    return
            # Prélever les mises
            for member in self.team1 + self.team2:
                data = get_user_data(member.id)
                data["pocket"] -= bet
                set_user_data(member.id, pocket=data["pocket"])
            # Lancer le combat : chaque équipe tire un nombre aléatoire, la somme détermine le gagnant
            team1_score = sum(random.randint(1, 10) for _ in self.team1)
            team2_score = sum(random.randint(1, 10) for _ in self.team2)
            total_bet = bet * len(self.team1 + self.team2)
            if team1_score > team2_score:
                winner_team = self.team1
            elif team2_score > team1_score:
                winner_team = self.team2
            else:
                # Égalité, remboursement
                for member in self.team1 + self.team2:
                    data = get_user_data(member.id)
                    data["pocket"] += bet
                    set_user_data(member.id, pocket=data["pocket"])
                await self.message.channel.send(f"⚔️ Combat terminé ! Égalité ({team1_score} - {team2_score}), les mises sont remboursées.")
                self.stop()
                return
            # Distribuer les gains (total_bet) aux gagnants
            win_per_player = total_bet // len(winner_team)
            for member in winner_team:
                data = get_user_data(member.id)
                data["pocket"] += win_per_player
                set_user_data(member.id, pocket=data["pocket"])
            await self.message.channel.send(f"⚔️ L'équipe {winner_team[0].mention} et co. remporte le combat ! Chaque gagnant reçoit {win_per_player}€.")
            self.stop()

    async def on_timeout(self):
        if not self.started:
            await self.message.channel.send("Temps écoulé, la partie est annulée.")
            # Rembourser ceux qui ont misé ? Mais on n'a pas encore prélevé.
            self.stop()

@jeux.command(name="teamfight", description="Combat 5v5 avec mise de 50€ par joueur")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
async def jeux_teamfight(interaction: discord.Interaction):
    if not in_command_category(interaction):
        await interaction.response.send_message("Cette commande est réservée aux salons de la catégorie Casino.", ephemeral=True)
        return
    if not has_casino_role(interaction):
        await interaction.response.send_message("Vous n'avez pas le rôle Casino.", ephemeral=True)
        return
    view = TeamFightView(interaction.user, 5)
    embed = discord.Embed(title="⚔️ Team Fight 5v5", description=f"{interaction.user.mention} a créé un combat !\nChaque joueur mise 50€.\nRejoignez une équipe en cliquant ci-dessous.", color=discord.Color.orange())
    msg = await interaction.response.send_message(embed=embed, view=view)
    view.message = msg
