import discord
from discord.ext import commands
from datetime import datetime, timezone
import aiohttp
import asyncio
import os
import re

# =========================================================
# CONFIGURATION
# =========================================================

LOGS_CHANNELS = {
    "messages": 1476233336333799697,
    "message_edit": 1476233342771925053,
    "salons": 1476233348052553869,
    "roles": 1476233353450623068,
    "vocal": 1476233360601780358,
    "mutes": 1497540093232283748,
    "kicks": 1497540650667610192,
    "bans": 1497540697115463761,
    "images": 1496522037081014362,
    "moderation": 1504072244366807040
}

SAVE_FOLDER = "saved_attachments"

os.makedirs(SAVE_FOLDER, exist_ok=True)

IMAGE_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".mp4",
    ".mov",
    ".webm"
)

# =========================================================
# INSULTES
# =========================================================

BAD_WORDS = {
    "fdp",
    "tg",
    "ntm",
    "pute",
    "enculé",
    "encule",
    "connard",
    "salope",
    "batard",
    "bâtard",
    "nique",
    "tamere",
    "ta mère",
    "ferme ta gueule"
}

# =========================================================
# DOMAINES AUTORISÉS
# =========================================================

AUTHORIZED_DOMAINS = {
    "youtube.com",
    "youtu.be",
    "tiktok.com",
    "github.com"
}

LINK_REGEX = re.compile(
    r"(https?://[^\s]+|www\.[^\s]+)",
    re.IGNORECASE
)

DISCORD_INVITE_REGEX = re.compile(
    r"(discord\.gg/|discord\.com/invite/)",
    re.IGNORECASE
)

# =========================================================
# COG
# =========================================================

class Logs(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.message_cache = {}

    # =====================================================
    # SEND LOG
    # =====================================================

    async def send_log(self, log_type, embed=None, files=None):

        try:

            channel_id = LOGS_CHANNELS.get(log_type)

            if not channel_id:
                return

            channel = self.bot.get_channel(channel_id)

            if not channel:
                return

            await channel.send(
                embed=embed,
                files=files or []
            )

        except Exception as e:
            print(f"[LOG ERROR] {e}")

    # =====================================================
    # SAVE ATTACHMENTS
    # =====================================================

    async def save_attachment(self, attachment):

        try:

            filename = f"{attachment.id}_{attachment.filename}"
            path = os.path.join(
                SAVE_FOLDER,
                filename
            )

            async with aiohttp.ClientSession() as session:

                async with session.get(
                    attachment.url
                ) as response:

                    if response.status == 200:

                        with open(path, "wb") as f:
                            f.write(
                                await response.read()
                            )

            return path

        except Exception as e:
            print(f"[ATTACHMENT ERROR] {e}")
            return None

    # =====================================================
    # REAL MODERATOR
    # =====================================================

    async def get_real_moderator(
        self,
        guild,
        action,
        target_id
    ):

        try:

            async for entry in guild.audit_logs(
                limit=10,
                action=action
            ):

                if not entry.target:
                    continue

                if entry.target.id != target_id:
                    continue

                now = datetime.now(
                    timezone.utc
                )

                diff = (
                    now - entry.created_at
                ).total_seconds()

                if diff <= 10:
                    return (
                        entry.user,
                        entry.reason
                    )

        except Exception as e:
            print(f"[AUDIT ERROR] {e}")

        return None, "Aucune raison"

    # =====================================================
    # MESSAGE CREATE
    # =====================================================

    @commands.Cog.listener()
    async def on_message(self, message):

        if message.author.bot:
            return

        try:

            # =================================================
            # SAVE FILES
            # =================================================

            saved_files = []

            if message.attachments:

                for attachment in message.attachments:

                    path = await self.save_attachment(
                        attachment
                    )

                    if path:
                        saved_files.append(path)

                self.message_cache[message.id] = {
                    "files": saved_files
                }

            # =================================================
            # IMAGE LOGS
            # =================================================

            for attachment in message.attachments:

                if attachment.filename.lower().endswith(
                    IMAGE_EXTENSIONS
                ):

                    embed = discord.Embed(
                        title="📸 Image Envoyée",
                        color=discord.Color.blue(),
                        timestamp=datetime.now()
                    )

                    embed.set_author(
                        name=str(message.author),
                        icon_url=message.author.display_avatar.url
                    )

                    embed.add_field(
                        name="Utilisateur",
                        value=message.author.mention
                    )

                    embed.add_field(
                        name="Salon",
                        value=message.channel.mention
                    )

                    embed.add_field(
                        name="Fichier",
                        value=attachment.filename,
                        inline=False
                    )

                    embed.set_image(
                        url=attachment.url
                    )

                    embed.set_footer(
                        text=f"Message ID : {message.id}"
                    )

                    await self.send_log(
                        "images",
                        embed
                    )

            # =================================================
            # INSULTES
            # =================================================

            content_lower = message.content.lower()

            for word in BAD_WORDS:

                if word in content_lower:

                    embed = discord.Embed(
                        title="⚠️ Insulte Détectée",
                        color=discord.Color.orange(),
                        timestamp=datetime.now()
                    )

                    embed.set_author(
                        name=str(message.author),
                        icon_url=message.author.display_avatar.url
                    )

                    embed.add_field(
                        name="Utilisateur",
                        value=message.author.mention
                    )

                    embed.add_field(
                        name="Salon",
                        value=message.channel.mention
                    )

                    embed.add_field(
                        name="Mot détecté",
                        value=f"`{word}`"
                    )

                    embed.add_field(
                        name="Message",
                        value=message.content[:1000],
                        inline=False
                    )

                    await self.send_log(
                        "moderation",
                        embed
                    )

                    break

            # =================================================
            # INVITATIONS DISCORD
            # =================================================

            if DISCORD_INVITE_REGEX.search(
                message.content
            ):

                embed = discord.Embed(
                    title="🚫 Invitation Discord",
                    color=discord.Color.dark_red(),
                    timestamp=datetime.now()
                )

                embed.set_author(
                    name=str(message.author),
                    icon_url=message.author.display_avatar.url
                )

                embed.add_field(
                    name="Utilisateur",
                    value=message.author.mention
                )

                embed.add_field(
                    name="Salon",
                    value=message.channel.mention
                )

                embed.add_field(
                    name="Message",
                    value=message.content[:1000],
                    inline=False
                )

                await self.send_log(
                    "moderation",
                    embed
                )

            # =================================================
            # LIENS NON AUTORISÉS
            # =================================================

            links = LINK_REGEX.findall(
                message.content
            )

            if links:

                unauthorized = False

                for link in links:

                    if not any(
                        domain in link
                        for domain in AUTHORIZED_DOMAINS
                    ):
                        unauthorized = True
                        break

                if unauthorized:

                    embed = discord.Embed(
                        title="🚫 Lien Non Autorisé",
                        color=discord.Color.red(),
                        timestamp=datetime.now()
                    )

                    embed.set_author(
                        name=str(message.author),
                        icon_url=message.author.display_avatar.url
                    )

                    embed.add_field(
                        name="Utilisateur",
                        value=message.author.mention
                    )

                    embed.add_field(
                        name="Salon",
                        value=message.channel.mention
                    )

                    embed.add_field(
                        name="Message",
                        value=message.content[:1000],
                        inline=False
                    )

                    await self.send_log(
                        "moderation",
                        embed
                    )

        except Exception as e:
            print(f"[MESSAGE ERROR] {e}")

    # =====================================================
    # MESSAGE DELETE
    # =====================================================

    @commands.Cog.listener()
    async def on_message_delete(
        self,
        message
    ):

        if message.author.bot:
            return

        try:

            embed = discord.Embed(
                title="🗑️ Message Supprimé",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )

            embed.set_author(
                name=str(message.author),
                icon_url=message.author.display_avatar.url
            )

            embed.add_field(
                name="Auteur",
                value=f"{message.author.mention}\n`{message.author.id}`",
                inline=False
            )

            embed.add_field(
                name="Salon",
                value=message.channel.mention,
                inline=False
            )

            embed.add_field(
                name="Message",
                value=message.content[:1000]
                if message.content
                else "*Vide*",
                inline=False
            )

            await self.send_log(
                "messages",
                embed
            )

            # =============================================
            # RESTORE FILES
            # =============================================

            data = self.message_cache.get(
                message.id
            )

            if data:

                files = []

                for path in data["files"]:

                    if os.path.exists(path):

                        files.append(
                            discord.File(path)
                        )

                if files:

                    img_embed = discord.Embed(
                        title="🖼️ Fichier Supprimé",
                        color=discord.Color.dark_red(),
                        timestamp=datetime.now()
                    )

                    img_embed.set_author(
                        name=str(message.author),
                        icon_url=message.author.display_avatar.url
                    )

                    img_embed.add_field(
                        name="Auteur",
                        value=message.author.mention
                    )

                    img_embed.add_field(
                        name="Salon",
                        value=message.channel.mention
                    )

                    img_embed.add_field(
                        name="Message",
                        value=message.content
                        or "*Aucun texte*",
                        inline=False
                    )

                    await self.send_log(
                        "images",
                        img_embed,
                        files
                    )

        except Exception as e:
            print(f"[DELETE ERROR] {e}")

    # =====================================================
    # MESSAGE EDIT
    # =====================================================

    @commands.Cog.listener()
    async def on_message_edit(
        self,
        before,
        after
    ):

        if before.author.bot:
            return

        if before.content == after.content:
            return

        try:

            embed = discord.Embed(
                title="✏️ Message Modifié",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )

            embed.set_author(
                name=str(before.author),
                icon_url=before.author.display_avatar.url
            )

            embed.add_field(
                name="Auteur",
                value=before.author.mention
            )

            embed.add_field(
                name="Salon",
                value=before.channel.mention
            )

            embed.add_field(
                name="Ancien",
                value=before.content[:1000]
                or "*Vide*",
                inline=False
            )

            embed.add_field(
                name="Nouveau",
                value=after.content[:1000]
                or "*Vide*",
                inline=False
            )

            await self.send_log(
                "message_edit",
                embed
            )

        except Exception as e:
            print(f"[EDIT ERROR] {e}")

    # =====================================================
    # VOICE LOGS
    # =====================================================

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member,
        before,
        after
    ):

        try:

            # JOIN

            if before.channel is None and after.channel:

                embed = discord.Embed(
                    title="🎙️ Connexion Vocale",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )

                embed.add_field(
                    name="Membre",
                    value=member.mention
                )

                embed.add_field(
                    name="Salon",
                    value=after.channel.mention
                )

                await self.send_log(
                    "vocal",
                    embed
                )

            # LEAVE

            elif before.channel and after.channel is None:

                embed = discord.Embed(
                    title="🔇 Déconnexion Vocale",
                    color=discord.Color.red(),
                    timestamp=datetime.now()
                )

                embed.add_field(
                    name="Membre",
                    value=member.mention
                )

                embed.add_field(
                    name="Salon",
                    value=before.channel.name
                )

                await self.send_log(
                    "vocal",
                    embed
                )

            # MOVE

            elif (
                before.channel
                and after.channel
                and before.channel != after.channel
            ):

                embed = discord.Embed(
                    title="🔄 Changement Vocal",
                    color=discord.Color.blurple(),
                    timestamp=datetime.now()
                )

                embed.add_field(
                    name="Membre",
                    value=member.mention
                )

                embed.add_field(
                    name="Avant",
                    value=before.channel.name
                )

                embed.add_field(
                    name="Après",
                    value=after.channel.name
                )

                await self.send_log(
                    "vocal",
                    embed
                )

        except Exception as e:
            print(f"[VOICE ERROR] {e}")

# =====================================================
    # TIMEOUT
    # =====================================================

    @commands.Cog.listener()
    async def on_member_update(
        self,
        before,
        after
    ):

        try:

            if before.timed_out_until != after.timed_out_until:

                moderator, reason = await self.get_real_moderator(
                    after.guild,
                    discord.AuditLogAction.member_update,
                    after.id
                )

                # TIMEOUT ADDED

                if after.timed_out_until:

                    embed = discord.Embed(
                        title="🔇 Timeout",
                        color=discord.Color.orange(),
                        timestamp=datetime.now()
                    )

                    embed.add_field(
                        name="Membre",
                        value=after.mention
                    )

                    embed.add_field(
                        name="Modérateur",
                        value=moderator.mention
                        if moderator
                        else "Inconnu"
                    )

                    embed.add_field(
                        name="Raison",
                        value=reason
                        or "Aucune",
                        inline=False
                    )

                    embed.add_field(
                        name="Fin",
                        value=discord.utils.format_dt(
                            after.timed_out_until,
                            style="R"
                        )
                    )

                    await self.send_log(
                        "mutes",
                        embed
                    )

                # TIMEOUT REMOVED

                else:

                    embed = discord.Embed(
                        title="🔊 Timeout Retiré",
                        color=discord.Color.green(),
                        timestamp=datetime.now()
                    )

                    embed.add_field(
                        name="Membre",
                        value=after.mention
                    )

                    embed.add_field(
                        name="Modérateur",
                        value=moderator.mention
                        if moderator
                        else "Inconnu"
                    )

                    await self.send_log(
                        "mutes",
                        embed
                    )

        except Exception as e:
            print(f"[TIMEOUT ERROR] {e}")

    # =====================================================
    # KICKS
    # =====================================================

    @commands.Cog.listener()
    async def on_member_remove(
        self,
        member
    ):

        await asyncio.sleep(1)

        try:

            moderator, reason = await self.get_real_moderator(
                member.guild,
                discord.AuditLogAction.kick,
                member.id
            )

            if moderator:

                embed = discord.Embed(
                    title="👢 Membre Exclu",
                    color=discord.Color.red(),
                    timestamp=datetime.now()
                )

                embed.add_field(
                    name="Membre",
                    value=f"{member} ({member.id})"
                )

                embed.add_field(
                    name="Modérateur",
                    value=moderator.mention
                )

                embed.add_field(
                    name="Raison",
                    value=reason
                    or "Aucune",
                    inline=False
                )

                await self.send_log(
                    "kicks",
                    embed
                )

        except Exception as e:
            print(f"[KICK ERROR] {e}")

    # =====================================================
    # BANS
    # =====================================================

    @commands.Cog.listener()
    async def on_member_ban(
        self,
        guild,
        user
    ):

        await asyncio.sleep(1)

        try:

            moderator, reason = await self.get_real_moderator(
                guild,
                discord.AuditLogAction.ban,
                user.id
            )

            embed = discord.Embed(
                title="🔨 Membre Banni",
                color=discord.Color.dark_red(),
                timestamp=datetime.now()
            )

            embed.add_field(
                name="Utilisateur",
                value=f"{user} ({user.id})"
            )

            embed.add_field(
                name="Modérateur",
                value=moderator.mention
                if moderator
                else "Inconnu"
            )

            embed.add_field(
                name="Raison",
                value=reason
                or "Aucune",
                inline=False
            )

            await self.send_log(
                "bans",
                embed
            )

        except Exception as e:
            print(f"[BAN ERROR] {e}")

# =========================================================
# SETUP
# =========================================================

async def setup(bot):
    await bot.add_cog(Logs(bot))
