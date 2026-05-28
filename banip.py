import discord
from discord.ext import commands
from collections import defaultdict

class BanIPCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.banned_ips = defaultdict(list)  # {ip: [user_ids]}
    
    def get_user_ip(self, user_id):
        """Récupère l'IP d'un utilisateur (simulé)"""
        return hash(str(user_id)) % 256
    
    @discord.app_commands.command(name="banip", description="Bannir un utilisateur par IP (@ping ou ID)")
    async def ban_ip(self, interaction: discord.Interaction, user: str, *, reason: str = "Pas de raison"):
        """/banip @user Raison ou /banip 123456789 Raison"""
        
        # Vérifier les perms
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Tu dois être admin", ephemeral=True)
            return
        
        guild = interaction.guild
        member = None
        user_id = None
        
        # Essayer de récupérer par @ping
        try:
            if user.startswith("<@"):
                user_id = int(user.strip("<@!>"))
                member = await guild.fetch_member(user_id)
            else:
                # Essayer comme ID direct
                user_id = int(user)
                try:
                    member = await guild.fetch_member(user_id)
                except:
                    pass
        except ValueError:
            await interaction.response.send_message("❌ ID ou mention invalide", ephemeral=True)
            return
        
        if user_id is None:
            await interaction.response.send_message("❌ Utilisateur introuvable", ephemeral=True)
            return
        
        # Récupérer l'IP
        ip = self.get_user_ip(user_id)
        
        # Ajouter à la liste des IPs bannies
        self.banned_ips[ip].append(user_id)
        
        # Bannir l'utilisateur si possible
        if member:
            try:
                await guild.ban(member, reason=f"Ban IP - {reason}")
            except:
                pass
        else:
            # Utilisateur n'existe plus sur le serveur, on le bannit quand même
            try:
                user_obj = await self.bot.fetch_user(user_id)
                await guild.ban(user_obj, reason=f"Ban IP - {reason}")
            except:
                pass
        
        # Message de confirmation
        embed = discord.Embed(
            title="⛔ UTILISATEUR BANNI PAR IP",
            description=f"**ID :** `{user_id}`\n"
            f"**IP :** `{ip}`\n"
            f"**Raison :** {reason}",
            color=discord.Color.dark_red()
        )
        await interaction.response.send_message(embed=embed)
        
        # Log
        embed_log = discord.Embed(
            title="🚫 Ban IP",
            description=f"**ID :** {user_id}\n**IP :** `{ip}`\n**Raison :** {reason}",
            color=discord.Color.dark_red()
        )
        
        for channel in guild.channels:
            if "log" in channel.name.lower() and isinstance(channel, discord.TextChannel):
                try:
                    await channel.send(embed=embed_log)
                except:
                    pass
    
    @discord.app_commands.command(name="unbanip", description="Débannir une IP")
    async def unban_ip(self, interaction: discord.Interaction, user_id: int):
        """/unbanip 123456789"""
        
        # Vérifier les perms
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Tu dois être admin", ephemeral=True)
            return
        
        guild = interaction.guild
        
        # Récupérer l'IP
        ip = self.get_user_ip(user_id)
        
        # Débannir
        try:
            user_obj = await self.bot.fetch_user(user_id)
            await guild.unban(user_obj)
        except:
            pass
        
        # Retirer de la liste
        if ip in self.banned_ips and user_id in self.banned_ips[ip]:
            self.banned_ips[ip].remove(user_id)
        
        embed = discord.Embed(
            title="✅ UTILISATEUR DÉBANNI",
            description=f"**ID :** {user_id}\n**IP :** `{ip}`",
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
            await interaction.response.send_message("❌ Aucune IP bannie", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🚫 IPs BANNIES",
            color=discord.Color.dark_red()
        )
        
        for ip, users in list(self.banned_ips.items())[:25]:  # Max 25 fields
            embed.add_field(
                name=f"IP: `{ip}`",
                value=f"**Users:** {len(users)} banni(s)\n**IDs:** {', '.join(map(str, users[:5]))}{'...' if len(users) > 5 else ''}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Vérifier si l'IP est bannie à la connexion"""
        guild = member.guild
        ip = self.get_user_ip(member.id)
        
        if ip in self.banned_ips:
            try:
                await guild.ban(member, reason="IP bannie - tentative de reconnexion")
                
                embed = discord.Embed(
                    title="🚫 TENTATIVE DE RECONNEXION DÉTECTÉE",
                    description=f"{member.mention} (ID: {member.id}) a tenté de se reconnecter avec une IP bannie",
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
