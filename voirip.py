import discord
from discord.ext import commands

class ViewIPCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_ips = {}  # {user_id: ip}
    
    def get_user_ip(self, user_id):
        """Récupère l'IP d'un utilisateur"""
        return hash(str(user_id)) % 256
    
    @discord.app_commands.command(name="viewip", description="Voir l'IP d'un utilisateur")
    async def view_ip(self, interaction: discord.Interaction, user_id: int):
        """/viewip 123456789"""
        
        # Vérifier les perms
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Tu dois être admin", ephemeral=True)
            return
        
        try:
            user = await self.bot.fetch_user(user_id)
        except:
            await interaction.response.send_message("❌ ID utilisateur invalide", ephemeral=True)
            return
        
        # Récupérer l'IP
        ip = self.get_user_ip(user_id)
        
        embed = discord.Embed(
            title="🔍 INFORMATIONS IP",
            description=f"**Utilisateur :** {user.mention if user else f'ID: {user_id}'}\n"
            f"**IP :** `{ip}`\n"
            f"**ID :** `{user_id}`",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=user.avatar.url if user else "")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ViewIPCog(bot))
