import discord
from discord.ext import commands
from datetime import datetime

# --- CONFIGURATION DES SALONS ---
LOGS_CHANNELS = {
    "messages": 1476233336333799697,    # Salon LOGS-messages (Suppressions)
    "message02": 1476233342771925053,   # Salon LOGS-message02 (Modifications)
    "salons": 1476233348052553869,      # Salon LOGS-salons (Création/Suppression)
    "roles": 1476233353450623068,       # Salon LOGS-roles (Création/Modif rôles)
    "vocal": 1476233360601780358,       # Salon LOGS-vocal
    "mutes": 1497540093232283748,       # Nouveau : Mutes (Timeouts)
    "kicks": 1497540650667610192,       # Nouveau : Exclusions
    "bans": 1497540697115463761,        # Nouveau : Bannissements
    "images": 1496522037081014362       # Nouveau : Logs Images
}

class Logs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_log(self, channel_type, embed):
        channel_id = LOGS_CHANNELS.get(channel_type)
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel:
                await channel.send(embed=embed)

    # --- LOGS-MESSAGES (SUPPRESSION) ---
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot: return
        
        # Gestion des Images (Nouveau point demandé)
        if message.attachments:
            for attachment in message.attachments:
                embed_img = discord.Embed(title="🖼️ Image Supprimée", color=discord.Color.dark_red(), timestamp=datetime.now())
                embed_img.add_field(name="Auteur", value=message.author.mention)
                embed_img.add_field(name="Salon", value=message.channel.mention)
                embed_img.set_footer(text=f"ID du message: {message.id}")
                # Note: On ne peut pas "récupérer" l'image elle-même si elle est supprimée des serveurs Discord, 
                # mais on logge l'info qu'une image de nom {attachment.filename} a disparu.
                embed_img.add_field(name="Fichier", value=attachment.filename)
                await self.send_log("images", embed_img)

        embed = discord.Embed(title="🗑️ Message Supprimé", color=discord.Color.red(), timestamp=datetime.now())
        embed.add_field(name="Auteur", value=message.author.mention)
        embed.add_field(name="Salon", value=message.channel.mention)
        embed.add_field(name="Message", value=message.content or "Vide (Image/Fichier)", inline=False)
        await self.send_log("messages", embed)

    # --- LOGS-IMAGES (ENVOI) ---
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        if message.attachments:
            for attachment in message.attachments:
                if any(attachment.filename.lower().endswith(ext) for ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']):
                    embed = discord.Embed(title="📸 Image Envoyée", color=discord.Color.blue(), timestamp=datetime.now())
                    embed.add_field(name="Auteur", value=message.author.mention)
                    embed.add_field(name="Salon", value=message.channel.mention)
                    embed.set_image(url=attachment.url)
                    await self.send_log("images", embed)

    # --- LOGS-MESSAGE02 (MODIFICATION) ---
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or before.content == after.content: return
        embed = discord.Embed(title="📝 Message Modifié", color=discord.Color.orange(), timestamp=datetime.now())
        embed.add_field(name="Auteur", value=before.author.mention)
        embed.add_field(name="Ancien", value=before.content, inline=False)
        embed.add_field(name="Nouveau", value=after.content, inline=False)
        await self.send_log("message02", embed)

    # --- LOGS-SALONS (CREATION/SUPPRESSION) ---
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        embed = discord.Embed(title="📂 Salon Créé", color=discord.Color.green(), timestamp=datetime.now())
        embed.add_field(name="Nom", value=f"`#{channel.name}`")
        embed.add_field(name="Catégorie", value=channel.category.name if channel.category else "Aucune")
        await self.send_log("salons", embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        embed = discord.Embed(title="📁 Salon Supprimé", color=discord.Color.red(), timestamp=datetime.now())
        embed.add_field(name="Nom", value=f"`#{channel.name}`")
        await self.send_log("salons", embed)

    # --- LOGS-ROLES (CREATION/SUPPRESSION/MODIFICATION) ---
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        embed = discord.Embed(title="🎭 Rôle Créé", color=discord.Color.blue(), timestamp=datetime.now())
        embed.add_field(name="Nom du rôle", value=role.name)
        await self.send_log("roles", embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        embed = discord.Embed(title="🔥 Rôle Supprimé", color=discord.Color.dark_red(), timestamp=datetime.now())
        embed.add_field(name="Nom du rôle", value=role.name)
        await self.send_log("roles", embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        if before.name != after.name:
            embed = discord.Embed(title="✏️ Rôle Renommé", color=discord.Color.blurple(), timestamp=datetime.now())
            embed.add_field(name="Ancien Nom", value=before.name)
            embed.add_field(name="Nouveau Nom", value=after.name)
            await self.send_log("roles", embed)

    # --- LOGS-VOCAL ---
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel is None and after.channel is not None:
            embed = discord.Embed(title="🎙️ Connexion Vocale", color=discord.Color.green(), timestamp=datetime.now())
            embed.add_field(name="Membre", value=member.mention)
            embed.add_field(name="Salon", value=after.channel.mention)
            await self.send_log("vocal", embed)
        elif before.channel is not None and after.channel is None:
            embed = discord.Embed(title="🔇 Déconnexion Vocale", color=discord.Color.red(), timestamp=datetime.now())
            embed.add_field(name="Membre", value=member.mention)
            embed.add_field(name="Salon quitté", value=before.channel.name)
            await self.send_log("vocal", embed)
        elif before.channel is not None and after.channel is not None and before.channel != after.channel:
            embed = discord.Embed(title="🔄 Changement de Salon", color=discord.Color.blurple(), timestamp=datetime.now())
            embed.add_field(name="Membre", value=member.mention)
            embed.add_field(name="De", value=before.channel.name, inline=True)
            embed.add_field(name="À", value=after.channel.name, inline=True)
            await self.send_log("vocal", embed)

        if before.channel is not None and after.channel is not None and before.channel == after.channel:
            if before.status != after.status:
                embed = discord.Embed(title="💬 Statut Vocal Modifié", color=discord.Color.gold(), timestamp=datetime.now())
                embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
                embed.add_field(name="Membre", value=member.mention)
                embed.add_field(name="Ancien Statut", value=f"`{before.status}`" if before.status else "*Aucun*", inline=False)
                embed.add_field(name="Nouveau Statut", value=f"`{after.status}`" if after.status else "*Aucun*", inline=False)
                await self.send_log("vocal", embed)

    # --- NOUVEAUX LOGS : MUTE, KICK, BAN ---

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # Log pour le MUTE (Timeout)
        if before.timed_out_until != after.timed_out_until:
            if after.timed_out_until is not None:
                # L'utilisateur vient d'être mute
                async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
                    mod = entry.user
                    reason = entry.reason or "Aucune raison"
                
                embed = discord.Embed(title="🔇 Membre Mute (Timeout)", color=discord.Color.orange(), timestamp=datetime.now())
                embed.add_field(name="Cible", value=after.mention)
                embed.add_field(name="Modérateur", value=mod.mention)
                embed.add_field(name="Fin du mute", value=discord.utils.format_dt(after.timed_out_until, style='R'))
                embed.add_field(name="Raison", value=reason, inline=False)
                await self.send_log("mutes", embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # Log pour l'EXCLUSION (Kick)
        async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
            if entry.target.id == member.id:
                embed = discord.Embed(title="👢 Membre Exclu", color=discord.Color.red(), timestamp=datetime.now())
                embed.add_field(name="Cible", value=f"{member} ({member.id})")
                embed.add_field(name="Modérateur", value=entry.user.mention)
                embed.add_field(name="Raison", value=entry.reason or "Aucune raison", inline=False)
                await self.send_log("kicks", embed)
                break

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        # Log pour le BANNISSEMENT
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            if entry.target.id == user.id:
                embed = discord.Embed(title="🔨 Membre Banni", color=discord.Color.dark_red(), timestamp=datetime.now())
                embed.add_field(name="Cible", value=f"{user} ({user.id})")
                embed.add_field(name="Modérateur", value=entry.user.mention)
                embed.add_field(name="Raison", value=entry.reason or "Aucune raison", inline=False)
                await self.send_log("bans", embed)
                break

async def setup(bot):
    await bot.add_cog(Logs(bot))
