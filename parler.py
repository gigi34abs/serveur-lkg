import discord
from discord.ext import commands

ALLOWED_ROLES = [
    1454933872142979215,
    1495856636366164130,
    1500497331882168482
]

class ParlerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    def has_allowed_role(self, member):
        """Vérifie si le membre a un rôle autorisé"""
        return any(role.id in ALLOWED_ROLES for role in member.roles)
    
    @discord.app_commands.command(name="parler", description="Parler en tant que bot")
    async def parler(self, interaction: discord.Interaction, message: str):
        """/parler Bonjour tout le monde !"""
        
        # Vérifier les permissions
        if not self.has_allowed_role(interaction.user):
            await interaction.response.send_message("❌ Tu n'as pas la permission d'utiliser cette commande", ephemeral=True)
            return
        
        if len(message) < 1:
            await interaction.response.send_message("❌ Le message ne peut pas être vide", ephemeral=True)
            return
        
        if len(message) > 2000:
            await interaction.response.send_message("❌ Le message dépasse 2000 caractères", ephemeral=True)
            return
        
        # Envoyer le message
        await interaction.channel.send(message)
        
        # Confirmer
        await interaction.response.send_message("✅ Message envoyé !", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ParlerCog(bot))
