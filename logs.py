import discord
from discord.ext import commands
from datetime import datetime

# --- CONFIGURATION DES SALONS ---
LOGS_CHANNELS = {
    "messages": 1476233336333799697,    # Salon LOGS-messages (Suppressions)
    "message02": 1476233342771925053,   # Salon LOGS-message02 (Modifications)
    "salons": 1476233348052553869,      # Salon LOGS-salons (Création/Suppression)
    "roles": 1476233353450623068,       # Salon LOGS-roles (Création/Modif rôles)
    "vocal": 1476233360601780358        # Salon LOGS-vocal
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
        embed = discord.Embed(title="🗑️ Message Supprimé", color=discord.Color.red(), timestamp=datetime.now())
        embed.add_field(name="Auteur", value=message.author.mention)
        embed.add_field(name="Salon", value=message.channel.mention)
        embed.add_field(name="Message", value=message.content or "Vide (Image/Fichier)", inline=False)
        await self.send_log("messages", embed)

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

    # --- LOGS-VOCAL (REJOINDRE/QUITTER/CHANGER/STATUT) ---
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # 1. Connexion à un salon
        if before.channel is None and after.channel is not None:
            embed = discord.Embed(title="🎙️ Connexion Vocale", color=discord.Color.green(), timestamp=datetime.now())
            embed.add_field(name="Membre", value=member.mention)
            embed.add_field(name="Salon", value=after.channel.mention) # mention du salon c'est plus joli
            await self.send_log("vocal", embed)

        # 2. Déconnexion d'un salon
        elif before.channel is not None and after.channel is None:
            embed = discord.Embed(title="🔇 Déconnexion Vocale", color=discord.Color.red(), timestamp=datetime.now())
            embed.add_field(name="Membre", value=member.mention)
            embed.add_field(name="Salon quitté", value=before.channel.name)
            await self.send_log("vocal", embed)

        # 3. Changement de salon
        elif before.channel is not None and after.channel is not None and before.channel != after.channel:
            embed = discord.Embed(title="🔄 Changement de Salon", color=discord.Color.blurple(), timestamp=datetime.now())
            embed.add_field(name="Membre", value=member.mention)
            embed.add_field(name="De", value=before.channel.name, inline=True)
            embed.add_field(name="À", value=after.channel.name, inline=True)
            await self.send_log("vocal", embed)

        # 4. Changement de Statut Vocal (Correction pour Kokoro)
        # On vérifie si l'utilisateur est dans le même salon mais que son texte de statut a changé
        if before.channel is not None and after.channel is not None and before.channel == after.channel:
            # On compare les status (attribut de VoiceState)
            if before.status != after.status:
                embed = discord.Embed(title="💬 Statut Vocal Modifié", color=discord.Color.gold(), timestamp=datetime.now())
                embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
                embed.add_field(name="Membre", value=member.mention)
                embed.add_field(name="Ancien Statut", value=f"`{before.status}`" if before.status else "*Aucun*", inline=False)
                embed.add_field(name="Nouveau Statut", value=f"`{after.status}`" if after.status else "*Aucun*", inline=False)
                embed.add_field(name="Salon", value=after.channel.mention)
                await self.send_log("vocal", embed)

async def setup(bot):
    await bot.add_cog(Logs(bot))
