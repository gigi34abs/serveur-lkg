import discord
from discord.ext import commands
from datetime import datetime, timezone
import asyncio

LOGS_CHANNELS = {
    "emoji": 1504073832099483648,
    "moderation_advanced": 1504073965499322368,
    "invitations": 1504074085049700472
}

class ExtraLogs(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # =====================================================
    # SEND LOG
    # =====================================================

    async def send_log(self, channel_key, embed):
        try:
            channel_id = LOGS_CHANNELS.get(channel_key)
            if not channel_id:
                return

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return

            await channel.send(embed=embed)

        except Exception as e:
            print(f"[LOG ERROR] {e}")

    # =====================================================
    # EMOJIS / STICKERS
    # =====================================================

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):

        try:
            before_ids = {e.id for e in before}
            after_ids = {e.id for e in after}

            # CREATED
            for emoji in after:
                if emoji.id not in before_ids:

                    embed = discord.Embed(
                        title="😀 Emoji Créé",
                        color=discord.Color.green(),
                        timestamp=datetime.now(timezone.utc)
                    )

                    embed.add_field(name="Nom", value=emoji.name, inline=True)
                    embed.add_field(name="ID", value=emoji.id, inline=True)
                    embed.set_thumbnail(url=emoji.url)

                    await self.send_log("emoji", embed)

            # DELETED
            for emoji in before:
                if emoji.id not in after_ids:

                    embed = discord.Embed(
                        title="🗑️ Emoji Supprimé",
                        color=discord.Color.red(),
                        timestamp=datetime.now(timezone.utc)
                    )

                    embed.add_field(name="Nom", value=emoji.name, inline=True)
                    embed.add_field(name="ID", value=emoji.id, inline=True)

                    await self.send_log("emoji", embed)

        except Exception as e:
            print(f"[EMOJI LOG ERROR] {e}")

    # =====================================================
    # INVITES CREATE
    # =====================================================

    @commands.Cog.listener()
    async def on_invite_create(self, invite):

        try:
            embed = discord.Embed(
                title="🔗 Invitation Créée",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(name="Code", value=invite.code, inline=True)
            embed.add_field(name="Salon", value=invite.channel.mention, inline=True)
            embed.add_field(
                name="Créée par",
                value=invite.inviter.mention if invite.inviter else "Inconnu",
                inline=False
            )

            await self.send_log("invitations", embed)

        except Exception as e:
            print(f"[INVITE CREATE ERROR] {e}")

    # =====================================================
    # INVITES DELETE
    # =====================================================

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):

        try:
            embed = discord.Embed(
                title="🗑️ Invitation Supprimée",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(name="Code", value=invite.code, inline=True)
            embed.add_field(name="Salon", value=invite.channel.mention, inline=True)

            await self.send_log("invitations", embed)

        except Exception as e:
            print(f"[INVITE DELETE ERROR] {e}")

    # =====================================================
    # UNBAN
    # =====================================================

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):

        await asyncio.sleep(1)

        try:

            moderator = None
            reason = "Aucune"

            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.unban):
                if entry.target.id == user.id:
                    moderator = entry.user
                    reason = entry.reason or "Aucune"
                    break

            embed = discord.Embed(
                title="🔓 Membre Débanni",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(name="Utilisateur", value=f"{user} ({user.id})", inline=False)
            embed.add_field(name="Modérateur", value=moderator.mention if moderator else "Inconnu", inline=False)
            embed.add_field(name="Raison", value=reason, inline=False)

            await self.send_log("moderation_advanced", embed)

        except Exception as e:
            print(f"[UNBAN ERROR] {e}")

    # =====================================================
    # BULK DELETE
    # =====================================================

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):

        try:

            if not messages:
                return

            channel = messages[0].channel

            users = set()

            for m in messages:
                if not m.author.bot:
                    users.add(str(m.author))

            embed = discord.Embed(
                title="🧹 Suppression Massive",
                color=discord.Color.dark_red(),
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(name="Salon", value=channel.mention, inline=True)
            embed.add_field(name="Messages supprimés", value=len(messages), inline=True)

            embed.add_field(
                name="Utilisateurs concernés",
                value="\n".join(list(users)[:20]) or "Aucun",
                inline=False
            )

            await self.send_log("moderation_advanced", embed)

        except Exception as e:
            print(f"[BULK DELETE ERROR] {e}")


async def setup(bot):
    await bot.add_cog(ExtraLogs(bot))
