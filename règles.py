import discord
from discord.ext import commands
from discord import app_commands, ui

# --- CONFIGURATION ---
ADMIN_IDS = [1433802915205742612, 1495018019674390678, 1342146881446350929]
ROLE_MEMBRE_ID = 1454893254687326298 # <--- METS L'ID DU RÔLE À DONNER ICI

class RulesView(ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Timeout=None pour que le bouton marche à vie

    @ui.button(label="Accepter le règlement", style=discord.ButtonStyle.green, emoji="✅", custom_id="accept_rules_btn")
    async def accept(self, interaction: discord.Interaction, button: ui.Button):
        role = interaction.guild.get_role(ROLE_MEMBRE_ID)
        
        if not role:
            return await interaction.response.send_message("❌ Erreur : Le rôle configuré n'existe pas.", ephemeral=True)
        
        if role in interaction.user.roles:
            return await interaction.response.send_message("✅ Tu as déjà accepté le règlement !", ephemeral=True)
        
        try:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("🎉 Merci ! Tu as maintenant accès au reste du serveur.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Je n'ai pas les permissions nécessaires pour donner le rôle. (Vérifie que mon rôle est au-dessus du rôle à donner)", ephemeral=True)

class Regles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_regles", description="Envoie le règlement officiel du serveur")
    async def setup_regles(self, interaction: discord.Interaction):
        if interaction.user.id not in ADMIN_IDS:
            return await interaction.response.send_message("❌ Seul un administrateur peut faire ça.", ephemeral=True)

        embed = discord.Embed(
            title="📜┃RÈGLEMENT DU SERVEUR DISCORD",
            description=(
                "1️⃣┃**Respect obligatoire** 🤝\n"
                "Tout le monde doit être respecté. Les insultes, provocations, harcèlement ou moqueries sont interdits.\n\n"
                "2️⃣┃**Aucune discrimination** 🚫\n"
                "Les propos racistes, sexistes, homophobes, transphobes ou haineux sont strictement interdits.\n\n"
                "3️⃣┃**Pas de publicité** 📢❌\n"
                "Interdiction de faire la promotion d’un autre serveur, chaîne, site ou réseau social sans l’autorisation du staff.\n\n"
                "4️⃣┃**Pseudo & photo corrects** 🆔\n"
                "Votre pseudo et votre photo de profil doivent être appropriés (pas de contenu choquant, haineux ou NSFW).\n\n"
                "5️⃣┃**Pas de spam / flood** 🛑\n"
                "Évitez les messages répétitifs, inutiles, les MAJUSCULES abusives ou les mentions excessives.\n\n"
                "6️⃣┃**Contenu interdit** 🔞\n"
                "Les contenus pornographiques, violents, choquants ou illégaux sont interdits.\n\n"
                "7️⃣┃**Respect du staff** 👮\n"
                "Respectez toutes décisions du staff.\n\n"
                "8️⃣┃**Pas de troll** 😈❌\n\n"
                "9️⃣┃**Pas de contournement** 🔄🚫\n"
                "Revenir avec un autre compte après une sanction (mute, kick, ban) est interdit.\n\n"
                "🔟┃**Utiliser les salons correctement** 🗂️\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "⚠️ **En cliquant sur le bouton ci-dessous, tu acceptes de suivre ces règles.**"
            ),
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message("✅ Règlement envoyé !", ephemeral=True)
        await interaction.channel.send(embed=embed, view=RulesView())

async def setup(bot):
    # On enregistre la vue pour qu'elle soit persistante au reboot
    bot.add_view(RulesView())
    await bot.add_cog(Regles(bot))
