import discord
from discord.ext import commands
from discord import app_commands
import datetime

# Tes 3 IDs autorisés
ADMIN_IDS = [1433802915205742612, 1495018019674390678, 1342146881446350929]

def is_admin(interaction: discord.Interaction) -> bool:
    return interaction.user.id in ADMIN_IDS

class Salons(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- LOCK SOFT (Fils autorisés) ---
    @app_commands.command(name="locksoft", description="Verrouille le salon mais laisse les fils ouverts")
    async def locksoft(self, interaction: discord.Interaction):
        if not is_admin(interaction):
            return await interaction.response.send_message("❌ Seuls les admins certifiés peuvent verrouiller ce salon.", ephemeral=True)

        role = interaction.guild.default_role
        overwrite = interaction.channel.overwrites_for(role)
        
        overwrite.send_messages = False
        overwrite.create_public_threads = True
        overwrite.send_messages_in_threads = True
        
        await interaction.channel.set_permissions(role, overwrite=overwrite)

        embed = discord.Embed(
            title="🔒 Salon en mode Lecture Seule",
            description="Le chat principal est bloqué.\n\n👉 **Note :** Vous pouvez toujours créer ou répondre dans des **Fils (Threads)**.",
            color=0x3498db
        )
        await interaction.response.send_message(embed=embed)

    # --- LOCK HARD (Tout bloqué + Emojis restreints) ---
    @app_commands.command(name="lockhard", description="Verrouille tout (pas de fils, pas de nouveaux emojis)")
    async def lockhard(self, interaction: discord.Interaction):
        if not is_admin(interaction):
            return await interaction.response.send_message("❌ Accès refusé : ID non reconnu.", ephemeral=True)

        role = interaction.guild.default_role
        overwrite = interaction.channel.overwrites_for(role)
        
        overwrite.send_messages = False
        overwrite.create_public_threads = False
        overwrite.add_reactions = False # Impossible d'ajouter de nouveaux emojis
        
        await interaction.channel.set_permissions(role, overwrite=overwrite)

        embed = discord.Embed(
            title="🚫 Verrouillage Maximum",
            description="Ce salon est totalement fermé.\n\n❌ Messages : Bloqués\n❌ Fils : Bloqués\n❌ Emojis : Nouveaux emojis interdits",
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed)

    # --- UNLOCK ---
    @app_commands.command(name="unlock", description="Réouvrir le salon")
    async def unlock(self, interaction: discord.Interaction):
        if not is_admin(interaction):
            return await interaction.response.send_message("❌ Non autorisé.", ephemeral=True)

        role = interaction.guild.default_role
        overwrite = interaction.channel.overwrites_for(role)
        
        overwrite.send_messages = None
        overwrite.create_public_threads = None
        overwrite.add_reactions = None
        
        await interaction.channel.set_permissions(role, overwrite=overwrite)
        await interaction.response.send_message("🔓 Le salon est de nouveau ouvert !")

async def setup(bot):
    await bot.add_cog(Salons(bot))
