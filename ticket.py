import discord
from discord.ext import commands
from discord import app_commands, ui
import datetime
import asyncio
import json
import os

# --- CONFIGURATION ---
ADMIN_IDS = [1433802915205742612, 1495018019674390678, 1342146881446350929]
ROLE_SAYAN_ID = 1495424065857388674
ROLE_GESTION_TICKET_ID = 1495771204751986769 # Rôle obtenu via /gestion_admin
CATEGORY_TICKETS_ID = 1476233272353755344
LOG_CHANNEL_ID = 1476233279660364067 
DATA_FILE = "ticket_stats.json"

# --- GESTION DES STATS ---
def load_stats():
    if not os.path.exists(DATA_FILE): return {}
    try:
        with open(DATA_FILE, "r") as f: return json.load(f)
    except: return {}

def save_stats(stats):
    with open(DATA_FILE, "w") as f: json.dump(stats, f, indent=4)

def update_user_stat(user_id, stat_type):
    stats = load_stats()
    u_id = str(user_id)
    if u_id not in stats: stats[u_id] = {"accepte": 0, "refuse": 0, "spam": 0}
    stats[u_id][stat_type] += 1
    save_stats(stats)
    return stats[u_id]["spam"]

# --- MODAL (FORMULAIRE) ---
class TicketForm(ui.Modal, title="Ouverture de Ticket"):
    description = ui.TextInput(
        label="Détails du problème",
        style=discord.TextStyle.paragraph,
        placeholder="👤 Nom / Pseudo\n🆔 ID ou référence\n📂 Catégorie\n🖥️ Service\n📄 Description\n📸 Preuves",
        required=True,
        min_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        log_chan = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log_chan:
            embed = discord.Embed(
                title="📥 Nouvelle demande de Ticket",
                description=f"**Utilisateur :** {interaction.user.mention}\n**ID Client :** `{interaction.user.id}`\n\n**Détails :**\n{self.description.value}",
                color=discord.Color.orange(),
                timestamp=datetime.datetime.now()
            )
            view = ApproveView(interaction.user, self.description.value)
            await log_chan.send(content=f"Demande_ID_{interaction.user.id}", embed=embed, view=view)
            await interaction.response.send_message("✅ Ta demande a été envoyée au staff.", ephemeral=True)

# --- BOUTONS STAFF (LOGS) ---
class ApproveView(ui.View):
    def __init__(self, author, desc):
        super().__init__(timeout=None)
        self.author = author
        self.desc = desc

    @ui.button(label="Accepter", style=discord.ButtonStyle.green, custom_id="accept_btn")
    async def approve(self, interaction: discord.Interaction, button: ui.Button):
        # Vérification si l'utilisateur est Staff (Admin ou Rôle spécifique)
        is_staff = interaction.user.id in ADMIN_IDS or any(r.id in [ROLE_SAYAN_ID, ROLE_GESTION_TICKET_ID] for r in interaction.user.roles)
        
        if not is_staff:
            return await interaction.response.send_message("❌ Tu n'as pas la permission d'accepter ce ticket.", ephemeral=True)

        guild = interaction.guild
        category = guild.get_channel(CATEGORY_TICKETS_ID)
        sayan_role = guild.get_role(ROLE_SAYAN_ID)
        gestion_role = guild.get_role(ROLE_GESTION_TICKET_ID)
        
        update_user_stat(self.author.id, "accepte")
        
        # Configuration des permissions pour le nouveau salon
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self.author: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True)
        }

        # Ajout du rôle Sayan s'il existe
        if sayan_role:
            overwrites[sayan_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
        
        # Ajout du rôle Gestion Ticket s'il existe
        if gestion_role:
            overwrites[gestion_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)

        # Ajout explicite des 3 Admins
        for admin_id in ADMIN_IDS:
            admin_member = guild.get_member(admin_id)
            if admin_member:
                overwrites[admin_member] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)

        chan = await guild.create_text_channel(
            name=f"ticket-{self.author.name}",
            category=category,
            overwrites=overwrites
        )
        
        embed = discord.Embed(title="🎟️ Ticket Ouvert", description=f"Bienvenue {self.author.mention}\n\n**Rappel :**\n{self.desc}", color=discord.Color.green())
        await chan.send(embed=embed, view=TicketManageView(self.author))
        await interaction.message.delete()

    @ui.button(label="Refuser", style=discord.ButtonStyle.red, custom_id="deny_btn")
    async def deny(self, interaction: discord.Interaction, button: ui.Button):
        is_staff = interaction.user.id in ADMIN_IDS or any(r.id in [ROLE_SAYAN_ID, ROLE_GESTION_TICKET_ID] for r in interaction.user.roles)
        if not is_staff:
            return await interaction.response.send_message("❌ Tu n'as pas la permission.", ephemeral=True)
            
        update_user_stat(self.author.id, "refuse")
        await interaction.message.delete()

# --- BOUTONS DANS LE TICKET (GESTION) ---
class TicketManageView(ui.View):
    def __init__(self, author):
        super().__init__(timeout=None)
        self.author = author

    @ui.button(label="🔔 Rappeler le membre", style=discord.ButtonStyle.blurple, custom_id="ping_btn")
    async def ping_member(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id in ADMIN_IDS or any(r.id in [ROLE_SAYAN_ID, ROLE_GESTION_TICKET_ID] for r in interaction.user.roles):
            await interaction.channel.send(f"🔔 {self.author.mention}, le staff attend une réponse de ta part !")
            await interaction.response.defer()
        else:
            await interaction.response.send_message("❌ Seul le staff peut utiliser ce bouton.", ephemeral=True)

    @ui.button(label="✅ Problème réglé", style=discord.ButtonStyle.green, custom_id="solved_btn")
    async def solved(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id == self.author.id or interaction.user.id in ADMIN_IDS or any(r.id in [ROLE_SAYAN_ID, ROLE_GESTION_TICKET_ID] for r in interaction.user.roles):
            await interaction.channel.send(f"✅ {interaction.user.mention} a marqué le ticket comme **réglé**. Fermeture en cours...")
            await asyncio.sleep(5)
            await interaction.channel.delete()
        else:
            await interaction.response.send_message("❌ Tu n'as pas la permission de faire ça.", ephemeral=True)

    @ui.button(label="🚫 Erreur / Spam", style=discord.ButtonStyle.red, custom_id="error_close_btn")
    async def error_close(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id == self.author.id or interaction.user.id in ADMIN_IDS or any(r.id in [ROLE_SAYAN_ID, ROLE_GESTION_TICKET_ID] for r in interaction.user.roles):
            await interaction.channel.send(f"🚫 Fermeture du ticket pour erreur ou spam.")
            await asyncio.sleep(5)
            await interaction.channel.delete()
        else:
            await interaction.response.send_message("❌ Tu n'as pas la permission de faire ça.", ephemeral=True)

    @ui.button(label="📁 Fermer (Staff)", style=discord.ButtonStyle.grey, custom_id="close_btn")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id in ADMIN_IDS or any(r.id in [ROLE_SAYAN_ID, ROLE_GESTION_TICKET_ID] for r in interaction.user.roles):
            await interaction.response.send_message("📁 Fermeture du ticket...")
            await asyncio.sleep(3)
            await interaction.channel.delete()
        else:
            await interaction.response.send_message("❌ Réservé au staff.", ephemeral=True)

# --- PANEL PRINCIPAL ---
class TicketLaunch(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="🎫 FAIRE UN TICKET", style=discord.ButtonStyle.red, custom_id="main_ticket_button_lkg")
    async def make_ticket(self, interaction: discord.Interaction, button: ui.Button):
        user_id_str = str(interaction.user.id)
        open_tickets = [c for c in interaction.guild.channels if c.name.startswith(f"ticket-{interaction.user.name.lower()}")]
        
        log_chan = interaction.guild.get_channel(LOG_CHANNEL_ID)
        pending_requests = 0
        if log_chan:
            async for message in log_chan.history(limit=50):
                if f"Demande_ID_{user_id_str}" in message.content:
                    pending_requests += 1

        total_active = len(open_tickets) + pending_requests
        if total_active >= 2:
            return await interaction.response.send_message(f"🚫 Limite atteinte ! Tu as déjà **{total_active}** ticket(s) en cours.", ephemeral=True)
            
        await interaction.response.send_modal(TicketForm())

# --- COG ET COMMANDES ---
class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    ticket_group = app_commands.Group(name="ticket", description="Commandes tickets")

    @ticket_group.command(name="panel")
    async def panel(self, interaction: discord.Interaction):
        if interaction.user.id not in ADMIN_IDS: return
        
        embed = discord.Embed(
            title="🎟️ LKG – Ouverture de ticket",
            description=(
                "Bienvenue dans le panel d’assistance LKG 👋\n"
                "Merci de lire les instructions avant de créer un ticket.\n\n"
                "📝 **Informations à fournir :**\n"
                "• 👤 Nom / Pseudo\n"
                "• 🆔 ID ou référence\n"
                "• 📂 Catégorie du problème\n"
                "• 🖥️ Service concerné\n"
                "• 📄 Description claire et détaillée\n"
                "• 📸 Preuves ou captures (si nécessaire)\n\n"
                "⚠️ Les tickets incomplets peuvent être refusés.\n"
                "🚫 Merci d’éviter le spam ou les relances inutiles.\n\n"
                "🔒 Un ticket = un seul problème.\n"
                "⏳ Le temps de réponse peut varier selon l’activité.\n\n"
                "💬 L’équipe LKG fera au mieux pour vous répondre rapidement.\n"
                "Merci pour votre patience 🤝"
            ),
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, view=TicketLaunch())

async def setup(bot):
    bot.add_view(TicketLaunch())
    await bot.add_cog(Ticket(bot))
