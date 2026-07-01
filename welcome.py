import discord
from discord.ext import commands
import asyncio

# =========================================================
# CONFIG
# =========================================================

PING_CHANNEL_ID = 1496204414216835072 1476242905705218182
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
            # PING CHANNEL
            # =============================================

            ping_channel = self.bot.get_channel(
                PING_CHANNEL_ID
            )

            if ping_channel:

                ping_message = await ping_channel.send(
                    f"{member.mention}"
                )

                # DELETE AFTER 10 SEC

                await asyncio.sleep(10)

                try:
                    await ping_message.delete()
                except:
                    pass

            # =============================================
            # WELCOME CHANNEL
            # =============================================

            welcome_channel = self.bot.get_channel(
                WELCOME_CHANNEL_ID
            )

            if welcome_channel:

                embed = discord.Embed(
                    description=(
                        f"╔══════════════════╗\n"
                        f"   🎉 **BIENVENUE SUR LKG** 🎉\n"
                        f"╚══════════════════╝\n\n"
                        f"👋 Hey {member.mention} !\n\n"
                        f"💬 Dites lui bienvenue dans le serveur !\n"
                        f"✨ Nous espérons que tu passeras un bon moment ici."
                    ),
                    color=discord.Color.blurple()
                )

                embed.set_thumbnail(
                    url=member.display_avatar.url
                )

                embed.set_footer(
                    text=f"{member.name} vient de rejoindre le serveur"
                )

                await welcome_channel.send(
                    embed=embed
                )

        except Exception as e:
            print(f"[WELCOME ERROR] {e}")

# =========================================================
# SETUP
# =========================================================

async def setup(bot):
    await bot.add_cog(Welcome(bot))
