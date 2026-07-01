# =========================================================
# PARTIE 1 – IMPORTS, CONFIGURATION, DONNÉES
# =========================================================

import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import random
import asyncio
from datetime import datetime, timedelta
import os
import time

# --- Configuration ---
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise ValueError("La variable d'environnement DISCORD_BOT_TOKEN n'est pas définie.")

GUILD_ID = 1454859381169590527 # À remplacer par l'ID de votre serveur

# IDs importants
ADMIN_ROLE_ID = 1454933872142979215
COMMAND_CATEGORY_ID = None  # On autorise toutes les catégories maintenant

# Fichiers de données
DATA_FILE = "economy_data.json"
GAME_STATES_FILE = "game_states.json"
SHOP_FILE = "shop_data.json"

# Initialisation du bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# =========================================================
# GESTION DES DONNÉES
# =========================================================

def load_json(file):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

economy = load_json(DATA_FILE)
game_states = load_json(GAME_STATES_FILE)
shop_items = load_json(SHOP_FILE)

# Si la boutique est vide, on met des articles par défaut
if not shop_items:
    shop_items = {
        "protecteur": {"price": 1500, "description": "Protège votre compte contre un vol (une fois)"},
        "double_gain": {"price": 2000, "description": "Double les gains de votre prochain jeu (une fois)"}
    }
    save_json(SHOP_FILE, shop_items)

def get_user_data(user_id):
    user_id = str(user_id)
    if user_id not in economy:
        economy[user_id] = {
            "pocket": 0,
            "bank": 0,
            "protection": False,
            "double_gain": False,
            "last_message_time": 0,
            "message_count": 0,
            "daily_claimed": 0
        }
        save_json(DATA_FILE, economy)
    return economy[user_id]

def set_user_data(user_id, **kwargs):
    user_id = str(user_id)
    if user_id not in economy:
        economy[user_id] = {"pocket": 0, "bank": 0, "protection": False, "double_gain": False, "last_message_time": 0, "message_count": 0, "daily_claimed": 0}
    for key, value in kwargs.items():
        economy[user_id][key] = value
    save_json(DATA_FILE, economy)

def is_admin(interaction):
    return interaction.user.get_role(ADMIN_ROLE_ID) is not None

# =========================================================
# GESTION DES MATCHS
# =========================================================

class Match:
    def __init__(self, channel_id, players, bet_per_player, max_players):
        self.channel_id = str(channel_id)
        self.players = players  # liste d'IDs
        self.bet_per_player = bet_per_player
        self.max_players = max_players
        self.teams = {}  # team_id -> [user_ids]
        self.current_turn_index = 0
        self.turn_start_time = None
        self.match_start_time = time.time()
        self.duration = 300  # 5 minutes
        self.turn_timeout = 30  # 30 secondes par action
        self.actions = {}  # user_id -> action (pour le tour en cours)
        self.scores = {}   # user_id -> score (somme des dés)
        self.finished = False
        self.winner_team = None
        # Initialiser les équipes : on alterne les joueurs entre équipe 1 et 2
        half = len(players) // 2
        self.teams[1] = players[:half]
        self.teams[2] = players[half:]
        # Si nombre impair, le dernier joueur rejoint l'équipe 1
        if len(players) % 2 != 0:
            self.teams[1].append(players[-1])
        # Scores initialisés à 0
        for p in players:
            self.scores[p] = 0

    def is_full(self):
        return len(self.players) >= self.max_players

    def add_player(self, user_id):
        if len(self.players) < self.max_players:
            self.players.append(user_id)
            # Rééquilibrer les équipes
            half = len(self.players) // 2
            self.teams[1] = self.players[:half]
            self.teams[2] = self.players[half:]
            if len(self.players) % 2 != 0:
                self.teams[1].append(self.players[-1])
            self.scores[user_id] = 0
            return True
        return False

    def get_current_player(self):
        if self.current_turn_index < len(self.players):
            return self.players[self.current_turn_index]
        return None

    def next_turn(self):
        self.current_turn_index = (self.current_turn_index + 1) % len(self.players)
        self.turn_start_time = time.time()
        self.actions = {}

    def is_timeout(self):
        if self.turn_start_time is None:
            return False
        return time.time() - self.turn_start_time > self.turn_timeout

    def is_match_over(self):
        return time.time() - self.match_start_time > self.duration

    def get_team_score(self, team_id):
        total = 0
        for uid in self.teams[team_id]:
            total += self.scores.get(uid, 0)
        return total

    def get_winning_team(self):
        score1 = self.get_team_score(1)
        score2 = self.get_team_score(2)
        if score1 > score2:
            return 1
        elif score2 > score1:
            return 2
        else:
            return None  # égalité

# Stockage des matchs actifs
active_matches = {}  # channel_id -> Match

# =========================================================
# FONCTIONS UTILITAIRES
# =========================================================

def random_dice():
    return random.randint(1, 6)

def get_user_mention(user_id):
    return f"<@{user_id}>"

def format_currency(amount):
    return f"{amount}€"

# =========================================================
# BOT EVENTS
# =========================================================

@bot.event
async def on_ready():
    print(f"Bot connecté en tant que {bot.user}")
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Commandes synchronisées : {len(synced)}")
    except Exception as e:
        print(f"Erreur de synchronisation : {e}")
    # Démarrer la tâche de gains par message
    message_gain_loop.start()

# Tâche pour ajouter 5€ par message (déclenchée à chaque message)
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    # Ignorer les commandes (pour éviter de spam)
    if message.content.startswith('!'):
        return
    user_id = message.author.id
    data = get_user_data(user_id)
    # Vérifier le cooldown (1 message toutes les 10 secondes pour éviter le spam)
    now = time.time()
    if now - data.get("last_message_time", 0) >= 10:
        data["pocket"] += 5
        data["last_message_time"] = now
        data["message_count"] = data.get("message_count", 0) + 1
        set_user_data(user_id, pocket=data["pocket"], last_message_time=data["last_message_time"], message_count=data["message_count"])
    await bot.process_commands(message)

# =========================================================
# PARTIE 2 – COMMANDES DE BASE
# =========================================================

@bot.tree.command(name="banque", description="Gestion de votre banque")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
async def banque(interaction: discord.Interaction):
    pass

@banque.command(name="voir", description="Voir votre argent en poche et en banque")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
async def banque_voir(interaction: discord.Interaction):
    data = get_user_data(interaction.user.id)
    embed = discord.Embed(title="Votre situation financière", color=discord.Color.green())
    embed.add_field(name="Argent en poche", value=format_currency(data["pocket"]), inline=True)
    embed.add_field(name="Argent en banque", value=format_currency(data["bank"]), inline=True)
    embed.add_field(name="Total", value=format_currency(data["pocket"] + data["bank"]), inline=False)
    if data.get("protection"):
        embed.add_field(name="🛡️ Protection", value="Active (1 utilisation restante)", inline=False)
    if data.get("double_gain"):
        embed.add_field(name="⚡ Double gain", value="Disponible (prochain jeu)", inline=False)
    await interaction.response.send_message(embed=embed)

@banque.command(name="depot", description="Déposer de l'argent en banque")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
@app_commands.describe(montant="Montant à déposer")
async def banque_depot(interaction: discord.Interaction, montant: int):
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
    await interaction.response.send_message(f"Vous avez déposé {format_currency(montant)}. Nouveau solde poche : {format_currency(data['pocket'])}, banque : {format_currency(data['bank'])}.")

@banque.command(name="retrait", description="Retirer de l'argent de la banque")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
@app_commands.describe(montant="Montant à retirer")
async def banque_retrait(interaction: discord.Interaction, montant: int):
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
    await interaction.response.send_message(f"Vous avez retiré {format_currency(montant)}. Nouveau solde poche : {format_currency(data['pocket'])}, banque : {format_currency(data['bank'])}.")

@bot.tree.command(name="argent", description="Transactions entre joueurs")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
async def argent(interaction: discord.Interaction):
    pass

@argent.command(name="donner", description="Donner de l'argent à un autre membre")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
@app_commands.describe(membre="Le bénéficiaire", montant="Montant à donner")
async def argent_donner(interaction: discord.Interaction, membre: discord.Member, montant: int):
    if montant <= 0:
        await interaction.response.send_message("Le montant doit être positif.", ephemeral=True)
        return
    if membre.id == interaction.user.id:
        await interaction.response.send_message("Vous ne pouvez pas vous donner à vous-même.", ephemeral=True)
        return
    data = get_user_data(interaction.user.id)
    if data["pocket"] < montant:
        await interaction.response.send_message("Vous n'avez pas assez d'argent en poche.", ephemeral=True)
        return
    data["pocket"] -= montant
    set_user_data(interaction.user.id, pocket=data["pocket"])
    dest = get_user_data(membre.id)
    dest["pocket"] += montant
    set_user_data(membre.id, pocket=dest["pocket"])
    await interaction.response.send_message(f"Vous avez donné {format_currency(montant)} à {membre.mention}.")

@argent.command(name="voler", description="Voler de l'argent en poche (1/3 chance de réussite)")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
@app_commands.describe(membre="La victime", montant="Montant à voler")
async def argent_voler(interaction: discord.Interaction, membre: discord.Member, montant: int):
    if montant <= 0:
        await interaction.response.send_message("Le montant doit être positif.", ephemeral=True)
        return
    if membre.id == interaction.user.id:
        await interaction.response.send_message("Vous ne pouvez pas vous voler vous-même.", ephemeral=True)
        return
    voleur = get_user_data(interaction.user.id)
    victime = get_user_data(membre.id)
    if victime["pocket"] < montant:
        await interaction.response.send_message(f"{membre.mention} n'a pas assez d'argent en poche.", ephemeral=True)
        return
    if voleur["pocket"] < montant:
        await interaction.response.send_message("Vous n'avez pas assez d'argent pour couvrir la perte en cas d'échec.", ephemeral=True)
        return
    # Vérifier si la victime a une protection
    if victime.get("protection", False):
        victime["protection"] = False  # Consomme la protection
        set_user_data(membre.id, protection=False)
        await interaction.response.send_message(f"{membre.mention} est protégé ! Vous perdez {format_currency(montant)} et la protection est consommée.")
        # Le voleur perd le montant
        voleur["pocket"] -= montant
        set_user_data(interaction.user.id, pocket=voleur["pocket"])
        return
    # Chance : 1/3
    if random.randint(1, 3) == 1:
        # Réussite
        victime["pocket"] -= montant
        voleur["pocket"] += montant
        set_user_data(membre.id, pocket=victime["pocket"])
        set_user_data(interaction.user.id, pocket=voleur["pocket"])
        await interaction.response.send_message(f"✅ Vous avez volé {format_currency(montant)} à {membre.mention} !")
    else:
        # Échec : le voleur perd le montant
        voleur["pocket"] -= montant
        set_user_data(interaction.user.id, pocket=voleur["pocket"])
        await interaction.response.send_message(f"❌ Échec ! Vous avez perdu {format_currency(montant)}.")

@bot.tree.command(name="journalier", description="Réclamer 200€ chaque jour")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
async def journalier(interaction: discord.Interaction):
    user_id = interaction.user.id
    data = get_user_data(user_id)
    now = time.time()
    if now - data.get("daily_claimed", 0) < 86400:
        remaining = int(86400 - (now - data.get("daily_claimed", 0)))
        await interaction.response.send_message(f"Vous avez déjà réclamé vos 200€. Prochain dans {remaining//3600}h {(remaining%3600)//60}min.", ephemeral=True)
        return
    data["pocket"] += 200
    data["daily_claimed"] = now
    set_user_data(user_id, pocket=data["pocket"], daily_claimed=data["daily_claimed"])
    await interaction.response.send_message("Vous avez reçu 200€ ! Revenez demain.")

# =========================================================
# PARTIE 3 – SYSTEME DE MATCHS
# =========================================================

@bot.tree.command(name="match", description="Créer ou rejoindre un match")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
async def match(interaction: discord.Interaction):
    pass

@match.command(name="creer", description="Créer un match (1v1 à 5v5)")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
@app_commands.describe(mise="Montant misé par joueur (entre 10 et 10000)", places="Nombre de places par équipe (1 à 5)")
async def match_creer(interaction: discord.Interaction, mise: int, places: int = 1):
    if mise < 10 or mise > 10000:
        await interaction.response.send_message("La mise doit être entre 10€ et 10000€.", ephemeral=True)
        return
    if places < 1 or places > 5:
        await interaction.response.send_message("Le nombre de places doit être entre 1 et 5.", ephemeral=True)
        return
    channel_id = interaction.channel_id
    if str(channel_id) in active_matches:
        await interaction.response.send_message("Un match est déjà en cours dans ce salon.", ephemeral=True)
        return
    # Vérifier que le créateur a assez d'argent en poche
    data = get_user_data(interaction.user.id)
    if data["pocket"] < mise:
        await interaction.response.send_message(f"Vous n'avez pas assez d'argent en poche (besoin de {format_currency(mise)}).", ephemeral=True)
        return
    # Créer le match
    match = Match(channel_id, [interaction.user.id], mise, places * 2)
    active_matches[str(channel_id)] = match
    # Prélever la mise du créateur
    data["pocket"] -= mise
    set_user_data(interaction.user.id, pocket=data["pocket"])
    embed = discord.Embed(title="🎯 Match créé !", description=f"{interaction.user.mention} a créé un match avec une mise de {format_currency(mise)}.\nPlaces disponibles : {places} par équipe.\nUtilisez `/match rejoindre` pour participer !", color=discord.Color.blue())
    await interaction.response.send_message(embed=embed)

@match.command(name="rejoindre", description="Rejoindre un match existant")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
async def match_rejoindre(interaction: discord.Interaction):
    channel_id = str(interaction.channel_id)
    match = active_matches.get(channel_id)
    if not match:
        await interaction.response.send_message("Aucun match en cours dans ce salon.", ephemeral=True)
        return
    if interaction.user.id in match.players:
        await interaction.response.send_message("Vous êtes déjà dans le match.", ephemeral=True)
        return
    if match.is_full():
        await interaction.response.send_message("Le match est complet.", ephemeral=True)
        return
    # Vérifier que le joueur a assez d'argent
    data = get_user_data(interaction.user.id)
    if data["pocket"] < match.bet_per_player:
        await interaction.response.send_message(f"Vous n'avez pas assez d'argent (besoin de {format_currency(match.bet_per_player)}).", ephemeral=True)
        return
    # Ajouter le joueur
    if not match.add_player(interaction.user.id):
        await interaction.response.send_message("Erreur lors de l'ajout.", ephemeral=True)
        return
    # Prélever la mise
    data["pocket"] -= match.bet_per_player
    set_user_data(interaction.user.id, pocket=data["pocket"])
    await interaction.response.send_message(f"{interaction.user.mention} a rejoint le match ! ({len(match.players)}/{match.max_players})")
    # Si le match est plein, démarrer automatiquement
    if len(match.players) == match.max_players:
        await start_match(interaction, match)

async def start_match(interaction, match):
    # Démarrer le match
    embed = discord.Embed(title="⚔️ Le match commence !", description="Chaque joueur va lancer un dé à son tour.\nVous avez 30 secondes pour jouer.\nLe match dure 5 minutes.", color=discord.Color.gold())
    await interaction.channel.send(embed=embed)
    match.match_start_time = time.time()
    match.current_turn_index = 0
    match.turn_start_time = time.time()
    # Boucle de jeu
    bot.loop.create_task(run_match_loop(interaction.channel, match))

async def run_match_loop(channel, match):
    while not match.is_match_over() and not match.finished:
        current_player = match.get_current_player()
        if current_player is None:
            break
        # Envoyer un message pour demander l'action
        await channel.send(f"{get_user_mention(current_player)}, c'est à vous ! Lancez le dé avec `/match lancer` ou passez avec `/match passer`. Vous avez 30 secondes.")
        # Attendre l'action ou timeout
        start_time = time.time()
        while time.time() - start_time < 30:
            # Vérifier si l'action a été faite (dans la commande lancer/passer on modifie match.actions)
            if current_player in match.actions:
                action = match.actions[current_player]
                if action == "lance":
                    score = random_dice()
                    match.scores[current_player] = score
                    await channel.send(f"{get_user_mention(current_player)} a lancé le dé et obtenu **{score}** !")
                elif action == "passe":
                    match.scores[current_player] = 0
                    await channel.send(f"{get_user_mention(current_player)} a passé son tour.")
                match.actions.pop(current_player)
                break
            await asyncio.sleep(1)
        else:
            # Timeout : le joueur ne joue pas, il passe automatiquement
            match.scores[current_player] = 0
            await channel.send(f"{get_user_mention(current_player)} n'a pas joué à temps, il passe.")
        # Passer au joueur suivant
        match.next_turn()
        # Vérifier si le match est terminé (temps écoulé ou tous les joueurs ont joué un certain nombre de tours ? on arrête à 5 min)
    # Fin du match
    if not match.finished:
        await end_match(channel, match)

async def end_match(channel, match):
    match.finished = True
    winner_team = match.get_winning_team()
    if winner_team is None:
        await channel.send("🤝 Match nul ! Les mises sont remboursées.")
        # Rembourser les mises
        for uid in match.players:
            data = get_user_data(uid)
            data["pocket"] += match.bet_per_player
            set_user_data(uid, pocket=data["pocket"])
    else:
        losing_team = 2 if winner_team == 1 else 1
        winners = match.teams[winner_team]
        losers = match.teams[losing_team]
        total_pot = match.bet_per_player * len(match.players)
        # Appliquer le double gain si un gagnant l'a
        # On va distribuer à chaque gagnant sa part
        share = total_pot // len(winners)
        for uid in winners:
            data = get_user_data(uid)
            gain = share
            if data.get("double_gain", False):
                gain *= 2
                data["double_gain"] = False  # Consomme le double gain
                set_user_data(uid, double_gain=False)
            data["pocket"] += gain
            set_user_data(uid, pocket=data["pocket"])
        await channel.send(f"🏆 L'équipe {winner_team} remporte le match ! Chaque gagnant reçoit {format_currency(share)} (avec double gain pour certains).")
        # Les perdants ne récupèrent rien
    # Supprimer le match
    active_matches.pop(str(channel.id), None)

@match.command(name="lancer", description="Lancer le dé lors de votre tour")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
async def match_lancer(interaction: discord.Interaction):
    channel_id = str(interaction.channel_id)
    match = active_matches.get(channel_id)
    if not match:
        await interaction.response.send_message("Aucun match en cours.", ephemeral=True)
        return
    current = match.get_current_player()
    if interaction.user.id != current:
        await interaction.response.send_message("Ce n'est pas votre tour.", ephemeral=True)
        return
    if interaction.user.id in match.actions:
        await interaction.response.send_message("Vous avez déjà joué ce tour.", ephemeral=True)
        return
    match.actions[interaction.user.id] = "lance"
    await interaction.response.send_message("Dé lancé !", ephemeral=True)

@match.command(name="passer", description="Passer votre tour")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
async def match_passer(interaction: discord.Interaction):
    channel_id = str(interaction.channel_id)
    match = active_matches.get(channel_id)
    if not match:
        await interaction.response.send_message("Aucun match en cours.", ephemeral=True)
        return
    current = match.get_current_player()
    if interaction.user.id != current:
        await interaction.response.send_message("Ce n'est pas votre tour.", ephemeral=True)
        return
    if interaction.user.id in match.actions:
        await interaction.response.send_message("Vous avez déjà joué ce tour.", ephemeral=True)
        return
    match.actions[interaction.user.id] = "passe"
    await interaction.response.send_message("Vous avez passé votre tour.", ephemeral=True)

# =========================================================
# PARTIE 4 – BOUTIQUE ET ADMIN
# =========================================================

@bot.tree.command(name="boutique", description="Afficher la boutique")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
async def boutique(interaction: discord.Interaction):
    embed = discord.Embed(title="🛒 Boutique", color=discord.Color.gold())
    for item_id, item in shop_items.items():
        embed.add_field(name=item_id, value=f"Prix : {format_currency(item['price'])}\n{item.get('description', '')}", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="acheter", description="Acheter un article de la boutique")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
@app_commands.describe(article="Nom de l'article (protecteur ou double_gain)")
async def acheter(interaction: discord.Interaction, article: str):
    if article not in shop_items:
        await interaction.response.send_message("Article introuvable. Consultez `/boutique`.", ephemeral=True)
        return
    data = get_user_data(interaction.user.id)
    item = shop_items[article]
    if data["pocket"] < item["price"]:
        await interaction.response.send_message(f"Vous n'avez pas assez d'argent. Prix : {format_currency(item['price'])}", ephemeral=True)
        return
    data["pocket"] -= item["price"]
    if article == "protecteur":
        data["protection"] = True
    elif article == "double_gain":
        data["double_gain"] = True
    set_user_data(interaction.user.id, pocket=data["pocket"], protection=data.get("protection", False), double_gain=data.get("double_gain", False))
    await interaction.response.send_message(f"Vous avez acheté {article} !")

@bot.tree.command(name="admin", description="Commandes d'administration (admin uniquement)")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
async def admin(interaction: discord.Interaction):
    pass

@admin.command(name="argent", description="Ajouter/retirer/inspecter l'argent d'un membre")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
@app_commands.describe(action="ajouter, retirer ou inspecter", membre="Le membre", montant="Montant (pour ajouter/retirer)")
async def admin_argent(interaction: discord.Interaction, action: str, membre: discord.Member, montant: int = None):
    if not is_admin(interaction):
        await interaction.response.send_message("Permission refusée.", ephemeral=True)
        return
    data = get_user_data(membre.id)
    if action == "inspecter":
        embed = discord.Embed(title=f"Compte de {membre.display_name}", color=discord.Color.blue())
        embed.add_field(name="Poche", value=format_currency(data["pocket"]))
        embed.add_field(name="Banque", value=format_currency(data["bank"]))
        embed.add_field(name="Protection", value="Oui" if data.get("protection") else "Non")
        embed.add_field(name="Double gain", value="Oui" if data.get("double_gain") else "Non")
        await interaction.response.send_message(embed=embed)
        return
    if montant is None or montant <= 0:
        await interaction.response.send_message("Montant invalide.", ephemeral=True)
        return
    if action == "ajouter":
        data["pocket"] += montant
        set_user_data(membre.id, pocket=data["pocket"])
        await interaction.response.send_message(f"Ajouté {format_currency(montant)} à {membre.mention}.")
    elif action == "retirer":
        if data["pocket"] < montant:
            await interaction.response.send_message(f"{membre.mention} n'a pas assez en poche.", ephemeral=True)
            return
        data["pocket"] -= montant
        set_user_data(membre.id, pocket=data["pocket"])
        await interaction.response.send_message(f"Retiré {format_currency(montant)} à {membre.mention}.")
    else:
        await interaction.response.send_message("Action invalide. Utilisez ajouter, retirer ou inspecter.", ephemeral=True)

@admin.command(name="boutique", description="Ajouter ou supprimer un article de la boutique")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
@app_commands.describe(action="ajouter ou supprimer", nom="Nom de l'article", prix="Prix (pour ajouter)", description="Description (pour ajouter)")
async def admin_boutique(interaction: discord.Interaction, action: str, nom: str, prix: int = None, description: str = None):
    if not is_admin(interaction):
        await interaction.response.send_message("Permission refusée.", ephemeral=True)
        return
    global shop_items
    if action == "ajouter":
        if prix is None or description is None:
            await interaction.response.send_message("Pour ajouter, spécifiez prix et description.", ephemeral=True)
            return
        shop_items[nom] = {"price": prix, "description": description}
        save_json(SHOP_FILE, shop_items)
        await interaction.response.send_message(f"Article {nom} ajouté à la boutique.")
    elif action == "supprimer":
        if nom not in shop_items:
            await interaction.response.send_message("Article introuvable.", ephemeral=True)
            return
        del shop_items[nom]
        save_json(SHOP_FILE, shop_items)
        await interaction.response.send_message(f"Article {nom} supprimé.")
    else:
        await interaction.response.send_message("Action invalide. Utilisez ajouter ou supprimer.", ephemeral=True)

@admin.command(name="reset", description="Réinitialiser les données d'un membre (admin)")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
@app_commands.describe(membre="Le membre à réinitialiser")
async def admin_reset(interaction: discord.Interaction, membre: discord.Member):
    if not is_admin(interaction):
        await interaction.response.send_message("Permission refusée.", ephemeral=True)
        return
    user_id = str(membre.id)
    if user_id in economy:
        del economy[user_id]
        save_json(DATA_FILE, economy)
        await interaction.response.send_message(f"Les données de {membre.mention} ont été réinitialisées.")
    else:
        await interaction.response.send_message(f"{membre.mention} n'a pas de données.", ephemeral=True)

# =========================================================
# PARTIE 5 – CLASSEMENT, AIDE ET LANCEMENT
# =========================================================

@bot.tree.command(name="classement", description="Classement des plus riches du serveur")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
async def classement(interaction: discord.Interaction):
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
        description += f"{i}. {name} : {format_currency(total)}\n"
    if not description:
        description = "Aucun joueur enregistré."
    embed.description = description
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="aide", description="Afficher toutes les commandes disponibles")
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.default_permissions()
async def aide(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 Aide - Commandes du Casino", color=discord.Color.blue())
    embed.add_field(name="💰 Banque", value="`/banque voir` – Voir son argent\n`/banque depot` – Déposer\n`/banque retrait` – Retirer", inline=False)
    embed.add_field(name="💸 Argent", value="`/argent donner` – Donner à un membre\n`/argent voler` – Voler (1/3 chance)", inline=False)
    embed.add_field(name="🎮 Matchs", value="`/match creer` – Créer un match\n`/match rejoindre` – Rejoindre\n`/match lancer` – Lancer le dé\n`/match passer` – Passer son tour", inline=False)
    embed.add_field(name="🛒 Boutique", value="`/boutique` – Voir les articles\n`/acheter` – Acheter un article", inline=False)
    embed.add_field(name="📆 Journalier", value="`/journalier` – 200€ par jour", inline=False)
    embed.add_field(name="🏆 Classement", value="`/classement` – Voir les plus riches", inline=False)
    embed.add_field(name="🔧 Admin", value="`/admin argent` – Gérer l'argent\n`/admin boutique` – Gérer la boutique\n`/admin reset` – Réinitialiser un membre", inline=False)
    await interaction.response.send_message(embed=embed)

# =========================================================
# LANCEMENT DU BOT
# =========================================================

if __name__ == "__main__":
    bot.run(TOKEN)
