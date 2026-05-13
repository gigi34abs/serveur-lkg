import discord
from discord.ext import commands

ROLE_ID = 1456274804549357739

class MaintenanceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @discord.app_commands.command(name="maintenance", description="Maintenance du serveur")
    @discord.app_commands.describe(
        action="mettre ou enlevé",
        member="La personne (optionnel)"
    )
    async def maintenance(self, interaction: discord.Interaction, action: str, member: discord.Member = None):
        """/maintenance mettre ou /maintenance enlevé @user"""
        
        # Vérifier les perms
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Tu dois être admin", ephemeral=True)
            return
        
        role = interaction.guild.get_role(ROLE_ID)
        
        if not role:
            await interaction.response.send_message("❌ Le rôle n'existe pas", ephemeral=True)
            return
        
        # METTRE LE RÔLE
        if action.lower() in ["mettre", "add"]:
            
            # Si personne spécifiée
            if member is not None:
                if role in member.roles:
                    await interaction.response.send_message(f"❌ {member.mention} a déjà ce rôle", ephemeral=True)
                    return
                
                try:
                    await member.add_roles(role)
                    embed = discord.Embed(
                        title="✅ RÔLE AJOUTÉ",
                        description=f"Le rôle {role.mention} a été donné à {member.mention} ! 🎉",
                        color=discord.Color.green()
                    )
                    await interaction.response.send_message(embed=embed)
                except:
                    await interaction.response.send_message("❌ Erreur lors de l'ajout du rôle", ephemeral=True)
            
            # Sinon à tout le monde
            else:
                count = 0
                for m in interaction.guild.members:
                    if not m.bot and role not in m.roles:
                        try:
                            await m.add_roles(role)
                            count += 1
                        except:
                            pass
                
                embed = discord.Embed(
                    title="✅ MAINTENANCE ACTIVÉE",
                    description=f"Le rôle {role.mention} a été donné à **{count} personnes** ! 🔧",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed)
        
        # ENLEVER LE RÔLE
        elif action.lower() in ["enlevé", "enlever", "remove"]:
            
            # Si personne spécifiée
            if member is not None:
                if role not in member.roles:
                    await interaction.response.send_message(f"❌ {member.mention} n'a pas ce rôle", ephemeral=True)
                    return
                
                try:
                    await member.remove_roles(role)
                    embed = discord.Embed(
                        title="✅ RÔLE ENLEVÉ",
                        description=f"Le rôle {role.mention} a été enlevé à {member.mention} ! 🗑️",
                        color=discord.Color.red()
                    )
                    await interaction.response.send_message(embed=embed)
                except:
                    await interaction.response.send_message("❌ Erreur lors de l'enlèvement du rôle", ephemeral=True)
            
            # Sinon à tout le monde
            else:
                count = 0
                for m in interaction.guild.members:
                    if not m.bot and role in m.roles:
                        try:
                            await m.remove_roles(role)
                            count += 1
                        except:
                            pass
                
                embed = discord.Embed(
                    title="✅ MAINTENANCE DÉSACTIVÉE",
                    description=f"Le rôle {role.mention} a été enlevé à **{count} personnes** ! ✅",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
        
        else:
            await interaction.response.send_message("❌ Action invalide : utilise 'mettre' ou 'enlevé'", ephemeral=True)

async def setup(bot):
    await bot.add_cog(MaintenanceCog(bot))
