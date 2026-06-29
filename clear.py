import discord
from discord.ext import commands
import asyncio

class ClearCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- COMMANDE CLEAR AVEC RESTRICTION DE RÔLES ---
    @commands.command(name="clear")
    @commands.has_any_role(
        1495856636366164130, 
        1495856698479349861, 
        1500497331882168482, 
        1454933872142979215
    )
    async def clear_messages(self, ctx, amount: str = "10"):
        """Efface des messages : +lkg clear 50 ou +lkg clear all"""
        
        try:
            # Si c'est "all", efface tous les messages
            if amount.lower() == "all":
                deleted = await ctx.channel.purge()
                embed = discord.Embed(
                    title="🧹 TOUS LES MESSAGES SUPPRIMÉS",
                    description=f"**{len(deleted)} messages** ont été effacés",
                    color=discord.Color.green()
                )
                msg = await ctx.send(embed=embed)
                await asyncio.sleep(5)
                try:
                    await msg.delete()
                except:
                    pass
                return
            
            # Sinon convertir en nombre
            amount_int = int(amount)
            
            if amount_int > 500:
                await ctx.send("❌ Maximum 500 messages à la fois")
                return
            
            if amount_int < 1:
                await ctx.send("❌ Minimum 1 message")
                return
            
            deleted = await ctx.channel.purge(limit=amount_int)
            
            embed = discord.Embed(
                title="🧹 Messages Supprimés",
                description=f"**{len(deleted)} messages** ont été effacés",
                color=discord.Color.green()
            )
            msg = await ctx.send(embed=embed)
            
            await asyncio.sleep(5)
            try:
                await msg.delete()
            except:
                pass
        
        except ValueError:
            await ctx.send("❌ Utilise: +lkg clear [nombre]\nExemple: +lkg clear 50 ou +lkg clear all")

    # --- GESTIONNAIRE D'ERREUR POUR LES PERMISSIONS ---
    @clear_messages.error
    async def clear_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole):
            # Envoie un message privé pour dire qu'il n'a pas le rôle
            try:
                await ctx.author.send("❌ Tu n'as pas la permission d'utiliser cette commande !")
            except:
                # Si les MP sont bloqués, répond dans le salon
                await ctx.send("❌ Tu n'as pas la permission d'utiliser cette commande !", delete_after=5)
        else:
            # Relance l'erreur si c'est autre chose
            raise error

# --- FONCTION SETUP OBLIGATOIRE ---
async def setup(bot):
    await bot.add_cog(ClearCog(bot))
