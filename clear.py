@commands.command(name="clear")
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
