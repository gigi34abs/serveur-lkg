import discord
from discord.ext import commands
from discord import app_commands
import json

class CasinoAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.file_path = "casino_data.json"
        self.allowed_role_id = 1454933872142979215

    def check_role(self, interaction: discord.Interaction):
        return any(role.id == self.allowed_role_id for role in interaction.user.roles)

    def load_data(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_data(self, data):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    # --- GROUPE ADMIN ECO (/casino donner, /casino retirer, /casino inspecter, /casino vider) ---
    casino_group = app_commands.Group(name="casino", description="Administration globale de l'économie")

    @casino_group.command(name="donner", description="Donner du cash à un joueur")
    async def casino_donner(self, interaction: discord.Interaction, joueur: discord.Member, montant: int):
        if not self.check_role(interaction):
            return await interaction.response.send_message("❌ Rôle requis manquant.", ephemeral=True)
            
        data = self.load_data()
        uid = str(joueur.id)
        if uid not in data["users"]:
            data["users"][uid] = {"portefeuille": 1000, "banque": 0, "items": {"protecteur": 0, "doubleur": 0}}
            
        data["users"][uid]["portefeuille"] += montant
        self.save_data(data)
        await interaction.response.send_message(f"🪙 **{montant:,} €** ajoutés au portefeuille de {joueur.display_name}.".replace(",", " "))

    @casino_group.command(name="retirer", description="Prendre du cash à un joueur")
    async def casino_retirer(self, interaction: discord.Interaction, joueur: discord.Member, montant: int):
        if not self.check_role(interaction):
            return await interaction.response.send_message("❌ Rôle requis manquant.", ephemeral=True)
            
        data = self.load_data()
        uid = str(joueur.id)
        if uid or uid in data["users"]:
            data["users"][uid]["portefeuille"] = max(0, data["users"][uid]["portefeuille"] - montant)
            self.save_data(data)
            await interaction.response.send_message(f"📉 **{montant:,} €** retirés du portefeuille de {joueur.display_name}.".replace(",", " "))

    @casino_group.command(name="inspecter", description="Inspecter complètement le profil d'un joueur")
    async def casino_inspecter(self, interaction: discord.Interaction, joueur: discord.Member):
        if not self.check_role(interaction):
            return await interaction.response.send_message("❌ Rôle requis manquant.", ephemeral=True)
            
        data = self.load_data()
        uid = str(joueur.id)
        user = data["users"].get(uid, {"portefeuille": 1000, "banque": 0, "items": {}})
        
        embed = discord.Embed(title=f"🔍 Inspection : {joueur.display_name}", color=0xE67E22)
        embed.add_field(name="Cash", value=f"{user['portefeuille']} €", inline=True)
        embed.add_field(name="Banque", value=f"{user['banque']} €", inline=True)
        embed.add_field(name="Inventaire", value=str(user.get("items", {})), inline=False)
        await interaction.response.send_message(embed=embed)

    @casino_group.command(name="vider", description="Supprimer les objets de l'inventaire d'un joueur")
    async def casino_vider(self, interaction: discord.Interaction, joueur: discord.Member):
        if not self.check_role(interaction):
            return await interaction.response.send_message("❌ Rôle requis manquant.", ephemeral=True)
            
        data = self.load_data()
        uid = str(joueur.id)
        if uid in data["users"]:
            data["users"][uid]["items"] = {"protecteur": 0, "doubleur": 0}
            self.save_data(data)
        await interaction.response.send_message(f"🧹 Inventaire vidé pour {joueur.display_name}.")

    # --- GROUPE ADMIN BOUTIQUE (/gestionboutique ajouter) ---
    g_boutique = app_commands.Group(name="gestionboutique", description="Gérer les produits de la boutique")

    @g_boutique.command(name="ajouter", description="Ajouter ou modifier un article dans la boutique")
    async def g_boutique_ajouter(self, interaction: discord.Interaction, item_id: str, nom: str, prix: int, description: str):
        if not self.check_role(interaction):
            return await interaction.response.send_message("❌ Rôle requis manquant.", ephemeral=True)
            
        data = self.load_data()
        data["shop"][item_id] = {"nom": nom, "prix": prix, "desc": description}
        self.save_data(data)
        await interaction.response.send_message(f"✅ L'article **{nom}** (`{item_id}`) a été ajouté/modifié dans la boutique !")

async def setup(bot):
    await bot.add_cog(CasinoAdmin(bot))
