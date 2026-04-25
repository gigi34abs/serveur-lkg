import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio
import os

# ==========================================================
# CONFIGURATION DES ADMINISTRATEURS AUTORISÉS
# ==========================================================
ADMIN_IDS = [1433802915205742612, 1495018019674390678, 1342146881446350929]

def is_admin(interaction: discord.Interaction) -> bool:
    """Vérifie si l'utilisateur est dans la liste VIP"""
    return interaction.user.id in ADMIN_IDS

# ==========================================================
# SYSTÈME DE MODÉRATION AVANCÉ
# ==========================================================

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- COMMANDE /BAN ---
    @app_commands.command(name="ban", description="Bannir définitivement un membre indésirable")
    @app_commands.describe(membre="Le fauteur de trouble", raison="Pourquoi cette sanction ?")
    async def ban(self, interaction: discord.Interaction, membre: discord.Member, raison: str = "Non spécifiée"):
        if not is_admin(interaction):
            return await interaction.response.send_message("❌ **Accès refusé.** Cette commande est réservée à l'élite du serveur.", ephemeral=True)

        if membre.id in ADMIN_IDS:
            return await interaction.response.send_message("🛡️ **Erreur :** Vous ne pouvez pas bannir un autre administrateur.", ephemeral=True)

        embed_dm = discord.Embed(
            title="🚫 Sanction Irréversible",
            description=f"Vous avez été banni du serveur **{interaction.guild.name}**",
            color=0xff0000,
            timestamp=datetime.datetime.now()
        )
        embed_dm.add_field(name="⚖️ Raison", value=raison, inline=False)
        embed_dm.set_footer(text="Bot de Modération LKG")

        try:
            await membre.send(embed=embed_dm)
        except:
            pass 

        await membre.ban(reason=f"Par {interaction.user}: {raison}")

        embed_log = discord.Embed(title="🔨 Marteau du Ban utilisé", color=0x990000)
        embed_log.set_author(name=membre.display_name, icon_url=membre.display_avatar.url)
        embed_log.add_field(name="👤 Utilisateur", value=f"{membre.mention} ({membre.id})", inline=True)
        embed_log.add_field(name="👮 Modérateur", value=interaction.user.mention, inline=True)
        embed_log.add_field(name="📝 Raison", value=raison, inline=False)
        embed_log.set_footer(text=f"Action effectuée le {datetime.datetime.now().strftime('%d/%m/%Y à %H:%M')}")
        
        await interaction.response.send_message(embed=embed_log)

    # --- COMMANDE /MUTE (Timeout) ---
    @app_commands.command(name="mute", description="Réduire un membre au silence temporairement")
    @app_commands.describe(membre="Le membre à mute", temps="Durée en minutes", raison="Raison du silence")
    async def mute(self, interaction: discord.Interaction, membre: discord.Member, temps: int, raison: str = "Non spécifiée"):
        if not is_admin(interaction):
            return await interaction.response.send_message("⚠️ **Permission manquante.**", ephemeral=True)

        duree = datetime.timedelta(minutes=temps)
        
        try:
            await membre.timeout(duree, reason=raison)
            
            embed_mute = discord.Embed(title="🙊 Mise en sourdine effectuée", color=0xffa500)
            embed_mute.add_field(name="👤 Membre", value=membre.mention, inline=True)
            embed_mute.add_field(name="⏳ Durée", value=f"{temps} minute(s)", inline=True)
            embed_mute.add_field(name="⚖️ Raison", value=raison, inline=False)
            
            await interaction.response.send_message(embed=embed_mute)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erreur : {e}", ephemeral=True)

    # --- COMMANDE /EXCLURE ---
    @app_commands.command(name="exclure", description="Expulser un membre du serveur")
    @app_commands.describe(membre="Le membre à exclure", raison="Motif de l'exclusion", temps="Temps recommandé avant retour")
    async def exclure(self, interaction: discord.Interaction, membre: discord.Member, raison: str = "Non spécifiée", temps: int = 10):
        if not is_admin(interaction):
            return await interaction.response.send_message("❌ Commande réservée.", ephemeral=True)

        embed_exclure = discord.Embed(title="👢 Expulsion du serveur", color=0xffff00)
        embed_exclure.add_field(name="📝 Raison", value=raison)
        embed_exclure.add_field(name="⏳ Conseil", value=f"Reviens dans {temps} minutes.")
        
        try:
            await membre.send(embed=embed_exclure)
        except:
            pass

        await membre.kick(reason=f"Exclusion par {interaction.user}: {raison}")
        await interaction.response.send_message(f"✅ **{membre.display_name}** a été éjecté.")

    # --- COMMANDE /ADMIN HELP (AVEC ESPACE) ---
    @app_commands.command(name="admin-help", description="Affiche le panel secret des commandes")
    async def admin_help(self, interaction: discord.Interaction):
        if not is_admin(interaction):
            return await interaction.response.send_message("❌ Accès interdit.", ephemeral=True)

        embed_help = discord.Embed(
            title="🛠️ Panel d'Administration - Serveur LKG",
            description="Liste des outils de modération (Réservé aux Admins).",
            color=0x2b2d31,
            timestamp=datetime.datetime.now()
        )
        
        embed_help.add_field(name="🔨 `/ban`", value="Bannissement définitif.", inline=False)
        embed_help.add_field(name="🙊 `/mute`", value="Silence temporaire (Timeout).", inline=False)
        embed_help.add_field(name="👢 `/exclure`", value="Expulsion (Kick).", inline=False)
        embed_help.set_footer(text="Système de sécurité LKG actif ✅")
        
        await interaction.response.send_message(embed=embed_help, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Admin(bot))
