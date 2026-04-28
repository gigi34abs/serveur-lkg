import discord
from discord.ext import commands
from discord import app_commands
import json
import os

# --- CONFIGURATION ---
ADMIN_IDS = [1433802915205742612, 1495018019674390678, 1342146881446350929]
CONFIG_FILE = "invite_config.json"

def is_admin(interaction: discord.Interaction):
    return interaction.user.id in ADMIN_IDS

# --- GESTION DE LA CONFIG ---
def save_config(guild_id, channel_id):
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
    config[str(guild_id)] = channel_id
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

def get_config(guild_id):
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            return config.get(str(guild_id))
    return None

class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites = {}

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            try:
                self.invites[guild.id] = await guild.invites()
            except:
                self.invites[guild.id] = []

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # On récupère le salon configuré
        channel_id = get_config(member.guild.id)
        if not channel_id:
            return # Pas de salon configuré, on ne fait rien

        channel = member.guild.get_channel(int(channel_id))
        if not channel:
            return

        invites_before = self.invites.get(member.guild.id, [])
        try:
            invites_after = await member.guild.invites()
        except:
            return

        inviter = None
        count = 0

        for invite in invites_before:
            for new_invite in invites_after:
                if invite.code == new_invite.code and new_invite.uses > invite.uses:
                    inviter = invite.inviter
                    count = new_invite.uses
                    break
        
        self.invites[member.guild.id] = invites_after

        if inviter:
            await channel.send(f"Bienvenue {member.mention} ! Tu as été invité(e) par **{inviter.name}** qui a désormais **{count}** invitation(s).")
        else:
            await channel.send(f"Bienvenue {member.mention} ! Invité par: **Inconnu**")

    # --- GROUPE DE COMMANDES ---
    invite_group = app_commands.Group(name="invite", description="Système d'invitations LKG")

    @invite_group.command(name="config", description="Configure le salon de bienvenue pour les invitations")
    @app_commands.describe(salon="Le salon où les messages seront envoyés")
    async def config(self, interaction: discord.Interaction, salon: discord.TextChannel):
        if not is_admin(interaction):
            return await interaction.response.send_message("❌ Accès réservé aux administrateurs fondateurs.", ephemeral=True)

        save_config(interaction.guild.id, salon.id)
        await interaction.response.send_message(f"✅ Le système d'invitations est maintenant configuré sur {salon.mention} !", ephemeral=True)

    @invite_group.command(name="liste", description="Voir les invitations d'un membre")
    async def liste(self, interaction: discord.Interaction, membre: discord.Member):
        if not is_admin(interaction):
            return await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)

        total = 0
        try:
            invites = await interaction.guild.invites()
            for i in invites:
                if i.inviter.id == membre.id:
                    total += i.uses
            await interaction.response.send_message(f"📊 {membre.mention} a un total de **{total}** invitations.")
        except:
            await interaction.response.send_message("❌ Erreur : Je n'ai pas la permission `Gérer le serveur`.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(InviteTracker(bot))
