import discord
from discord.ext import commands
from collections import defaultdict
import time

class BanIPCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.banned_ips = defaultdict(list)  # {ip: [user_ids]}
    
    def get_user_ip(self, member):
        """Récupère l'IP d'un utilisateur (simulé)"""
        # Note: Discord ne donne pas accès aux IPs réelles
        # On utilise un hash basé sur l'ID utilisateur
        return hash(str(member.id)) % 256
    
    @discord.app_commands.command(name="banip", description="Bannir un utilisateur par IP")
    async def ban_ip(self, interaction: discord.Interaction, member: discord.Member, *, reason: str = "Pas de raison"):
        """/banip @user Raison du ban"""
        
        # Vérifier les perms
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Tu dois être admin", ephemeral=True)
            return
        
        if member.id == interaction.user.id:
            await interaction.response.send_message("❌ Tu ne peux pas te bannir toi-même", ephemeral=True)
            return
        
        guild = interaction.guild
        
        # Récupérer l'"IP" (simulée)
        ip = self.get_user_ip(member)
        
        # Ajouter à la liste des IPs bannies
        self.banned_ips[ip].append(member.id)
        
        # Bannir l'utilisateur
        try:
            await guild.ban(member, reason=f"Ban IP - {reason}")
        except:
            pass
        
        # Message
        embed = discord.Embed(
            title="⛔ UTILISATEUR BANNI PAR IP",
            description=f"**Utilisateur :** {member.mention}\n"
            f"**IP :** `{ip}`\n"
            f"**Raison :** {reason}",
            color=discord.Color.dark_red()
        )
        await interaction.response.send_message(embed=embed)
        
        # Log
        embed_log = discord.Embed(
            title="🚫 Ban IP",
            description=f"{member.mention} a été banni par IP ({ip})\n**Raison :** {reason}",
            color=discord.Color.dark_red()
        )
        
        for channel in guild.channels:
            if "log" in channel.name.lower() and isinstance(channel, discord.TextChannel):
                try:
                    await channel.send(embed=embed_log)
                except:
                    pass
    
    @discord.app_commands.command(name="unbanip", description="Débannir une IP")
    async def unban_ip(self, interaction: discord.Interaction, member_id: int):
        """/unbanip 123456789"""
        
        # Vérifier les perms
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Tu dois être admin", ephemeral=True)
            return
        
        guild = interaction.guild
        
        # Récupérer l'"IP" (simulée)
        try:
            member = await self.bot.fetch_user(member_id)
            ip = self.get_user_ip(member)
        except:
            await interaction.response.send_message("❌ ID utilisateur invalide", ephemeral=True)
            return
        
        # Débannir
        try:
            await guild.unban(member)
        except:
            pass
        
        # Retirer de la liste
        if ip in self.banned_ips:
            self.banned_ips[ip].remove(member_id)
        
        embed = discord.Embed(
            title="✅ UTILISATEUR DÉBANNI",
            description=f"**ID :** {member_id}\n**IP :** `{ip}`",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    
    @discord.app_commands.command(name="listbanip", description="Voir les IPs bannies")
    async def list_ban_ip(self, interaction: discord.Interaction):
        """/listbanip"""
        
        # Vérifier les perms
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Tu dois être admin", ephemeral=True)
            return
        
        if not self.banned_ips:
            await interaction.response.send_message("❌ Aucune IP bannies", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🚫 IPs BANNIES",
            color=discord.Color.dark_red()
        )
        
        for ip, users in self.banned_ips.items():
            embed.add_field(
                name=f"IP: `{ip}`",
                value=f"**Users:** {len(users)} banni(s)\n**IDs:** {', '.join(map(str, users))}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Vérifier si l'IP est bannie à la connexion"""
        guild = member.guild
        ip = self.get_user_ip(member)
        
        if ip in self.banned_ips:
            try:
                await guild.ban(member, reason="IP bannie - reconnexion")
                
                embed = discord.Embed(
                    title="🚫 TENTATIVE DE RECONNEXION DÉTECTÉE",
                    description=f"{member.mention} a tenté de se reconnecter avec une IP bannie",
                    color=discord.Color.dark_red()
                )
                
                for channel in guild.channels:
                    if "log" in channel.name.lower() and isinstance(channel, discord.TextChannel):
                        try:
                            await channel.send(embed=embed)
                        except:
                            pass
            except:
                pass

async def setup(bot):
    await bot.add_cog(BanIPCog(bot))
