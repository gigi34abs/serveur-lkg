import discord
from discord.ext import commands
import asyncio

# =========================================================
# CONFIG
# =========================================================

# Salons où envoyer le ping (mention) puis supprimer
PING_CHANNEL_IDS = [
    1496204414216835072,
    1476242905705218182
]

# Salon où envoyer le message de bienvenue stylé
WELCOME_CHANNEL_ID = 1495350639419592825

# =========================================================
# COG
# =========================================================

class Welcome(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # =====================================================
    # MEMBER JOIN
    # =====================================================

    @commands.Cog.listener()
    async def on_member_join(self, member):

        try:

            # =============================================
            # PING DANS LES SALONS CONCERNÉS
            # =============================================

            for channel_id in PING_CHANNEL_IDS:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    ping_message = await channel.send(
                        f"{member.mention}"
                    )
                    # Supprimer après 10 secondes
                    await asyncio.sleep(10)
                    try:
                        await ping_message.delete()
                    except:
                        pass

            # =============================================
            # MESSAGE DE BIENVENUE STYLÉ
            # =============================================

            welcome_channel = self.bot.get_channel(WELCOME_CHANNEL_ID)

            if welcome_channel:

                # Création d'un embed très chic
                embed = discord.Embed(
                    title="✨ **BIENVENUE SUR LE SERVEUR LKG** ✨",
                    description=(
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        "🎉 **Nous sommes ravis de t'accueillir !** 🎉\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"👋 **Hey {member.mention} !**\n\n"
                        "🌟 **Tu fais désormais partie de la famille LKG !**\n"
                        "💬 N'hésite pas à te présenter et à discuter avec nous.\n"
                        "🎮 Ici, on partage, on s'amuse et on respecte tout le monde.\n\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    ),
                    color=discord.Color.from_rgb(255, 215, 0)  # Or brillant
                )

                # Ajout de champs décoratifs
                embed.add_field(
                    name="📌 **RÈGLES À RESPECTER**",
                    value=(
                        "• Reste courtois et respectueux\n"
                        "• Pas de spam ni de publicité\n"
                        "• Utilise les salons appropriés\n"
                        "• Amuse-toi bien !"
                    ),
                    inline=False
                )

                embed.add_field(
                    name="🎮 **ACTIVITÉS**",
                    value=(
                        "• Parties en vocal\n"
                        "• Jeux concours\n"
                        "• Giveaways réguliers\n"
                        "• Événements exclusifs"
                    ),
                    inline=True
                )

                embed.add_field(
                    name="👥 **COMMUNAUTÉ**",
                    value=(
                        f"• {len(member.guild.members)} membres actifs\n"
                        "• Entraide et bonne humeur\n"
                        "• Staff à l'écoute"
                    ),
                    inline=True
                )

                # Mini-bannière (image) – RETIRÉE
                # embed.set_image(
                #     url="https://i.imgur.com/6Z8d5XW.png"
                # )

                # Avatar du membre en miniature
                embed.set_thumbnail(
                    url=member.display_avatar.url
                )

                # Pied de page avec heure et nom
                embed.set_footer(
                    text=f"🎊 {member.name} a rejoint le serveur • {discord.utils.utcnow().strftime('%d/%m/%Y à %H:%M')}",
                    icon_url=member.guild.icon.url if member.guild.icon else None
                )

                # Envoi du message
                await welcome_channel.send(
                    content=f"🎉 **{member.mention}** 🎉",
                    embed=embed
                )

        except Exception as e:
            print(f"[WELCOME ERROR] {e}")

# =========================================================
# SETUP
# =========================================================

async def setup(bot):
    await bot.add_cog(Welcome(bot))
