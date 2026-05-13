import discord
from discord.ext import commands
from collections import defaultdict

OWNER_ID = 1454933872142979215
ADMIN_ROLES = [
    1495856636366164130,
    1500497331882168482,
    1495856698479349861,
    1495511911360364664,
    1495515834003624027
]

class PointsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.points = defaultdict(int)
    
    def has_admin_role(self, member):
        """Vérifie si le membre a un rôle admin"""
        return any(role.id in ADMIN_ROLES for role in member.roles)
    
    # ===== AJOUTER DES POINTS =====
    @discord.app_commands.command(name="admin_points", description="Ajouter des points à un admin")
    async def add_points(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        """/admin_points @admin 5"""
        
        # Vérifier que c'est le owner ou un admin
        if interaction.user.id != OWNER_ID and not self.has_admin_role(interaction.user):
            await interaction.response.send_message("❌ Tu n'as pas la permission", ephemeral=True)
            return
        
        # Vérifier que le member a un rôle admin
        if not self.has_admin_role(member):
            await interaction.response.send_message(f"❌ {member.mention} n'a pas de rôle admin", ephemeral=True)
            return
        
        if amount <= 0:
            await interaction.response.send_message("❌ Le nombre de points doit être positif", ephemeral=True)
            return
        
        # Ajouter les points
        self.points[member.id] += amount
        current_points = self.points[member.id]
        
        # Envoyer le message de congrats
        embed = discord.Embed(
            title="🎉 POINTS GAGNÉS !",
            description=f"{member.mention} a gagné **{amount} points** ! 🌟\n\n"
            f"**Points totaux :** {current_points}/10",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=member.avatar.url)
        embed.add_field(name="Félicitations !", value="Bravo pour tes efforts ! 💪", inline=False)
        
        await interaction.response.send_message(embed=embed)
        
        # Vérifier si 10 points atteints
        if current_points >= 10:
            embed_rank = discord.Embed(
                title="⭐ RANK UP !",
                description=f"{member.mention} a atteint **10 points** ! 🏆\n\n"
                f"L'admin a obtenu un nouveau rank ! Félicitations ! 🎊",
                color=discord.Color.gold()
            )
            await interaction.followup.send(embed=embed_rank)
    
    # ===== RETIRER DES POINTS =====
    @discord.app_commands.command(name="admin_points_retirer", description="Retirer des points à un admin")
    async def remove_points(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        """/admin_points_retirer @admin 3"""
        
        # Vérifier que c'est le owner ou un admin
        if interaction.user.id != OWNER_ID and not self.has_admin_role(interaction.user):
            await interaction.response.send_message("❌ Tu n'as pas la permission", ephemeral=True)
            return
        
        # Vérifier que le member a un rôle admin
        if not self.has_admin_role(member):
            await interaction.response.send_message(f"❌ {member.mention} n'a pas de rôle admin", ephemeral=True)
            return
        
        if amount <= 0:
            await interaction.response.send_message("❌ Le nombre de points doit être positif", ephemeral=True)
            return
        
        # Retirer les points
        self.points[member.id] -= amount
        
        # Pas de points négatifs
        if self.points[member.id] < 0:
            self.points[member.id] = 0
        
        current_points = self.points[member.id]
        
        # Envoyer le message
        embed = discord.Embed(
            title="❌ POINTS RETIRÉS",
            description=f"{member.mention} a perdu **{amount} points** 😢\n\n"
            f"**Points restants :** {current_points}/10",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.avatar.url)
        
        await interaction.response.send_message(embed=embed)
    
    # ===== VOIR LES POINTS =====
    @discord.app_commands.command(name="admin_points_info", description="Voir les points d'un admin")
    async def points_info(self, interaction: discord.Interaction, member: discord.Member = None):
        """/admin_points_info ou /admin_points_info @admin"""
        
        if member is None:
            member = interaction.user
        
        points = self.points[member.id]
        
        embed = discord.Embed(
            title="📊 POINTS",
            description=f"{member.mention}\n\n**Points :** {points}/10",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=member.avatar.url)
        
        if points >= 10:
            embed.add_field(name="Status", value="✅ RANK UP ! (10 points atteints)", inline=False)
        else:
            embed.add_field(name="Status", value=f"⏳ {10 - points} points avant rank up", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(PointsCog(bot))
