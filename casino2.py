import discord
from discord.ext import commands
from discord import app_commands
import json
import random

class CasinoBoutique(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.file_path = "casino_data.json"

    def load_data(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_data(self, data):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def get_user(self, user_id, data):
        uid = str(user_id)
        if uid not in data["users"]:
            data["users"][uid] = {"portefeuille": 1000, "banque": 0, "items": {"protecteur": 0, "doubleur": 0}}
        return data["users"][uid]

    boutique_group = app_commands.Group(name="boutique", description="Acheter des bonus uniques")

    @boutique_group.command(name="voir", description="🛍️ Afficher les articles de la boutique")
    async def boutique_voir(self, interaction: discord.Interaction):
        data = self.load_data()
        embed = discord.Embed(title="🛍️ BOUTIQUE DU PALAIS", color=0x9B59B6)
        
        for item_id, info in data["shop"].items():
            embed.add_field(
                name=f"🔹 {info['nom']} — {info['prix']:,} €".replace(",", " "),
                value=f"*{info['desc']}*\nID à utiliser : `{item_id}`",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

    @boutique_group.command(name="acheter", description="🛒 Acheter un article de la boutique")
    async def boutique_acheter(self, interaction: discord.Interaction, item_id: str):
        data = self.load_data()
        if item_id not in data["shop"]:
            return await interaction.response.send_message("❌ Cet article n'existe pas.", ephemeral=True)
            
        user = self.get_user(interaction.user.id, data)
        prix = data["shop"][item_id]["prix"]
        
        if user["portefeuille"] < prix:
            return await interaction.response.send_message("❌ Vous n'avez pas assez d'argent liquide.", ephemeral=True)
            
        user["portefeuille"] -= prix
        user["items"][item_id] = user["items"].get(item_id, 0) + 1
        self.save_data(data)
        
        await interaction.response.send_message(f"🛒 Achat réussi : Vous possédez un **{data['shop'][item_id]['nom']}** !")

    @app_commands.command(name="voler", description="🥷 Tenter de dérober de l'argent (1/3 chance de réussite)")
    async def voler(self, interaction: discord.Interaction, cible: discord.Member, montant: int):
        if montant < 10 or montant > 10000:
            return await interaction.response.send_message("❌ Le montant du vol doit être entre 10 € et 10 000 €.", ephemeral=True)
        if cible == interaction.user:
            return await interaction.response.send_message("❌ Impossible de se voler soi-même !", ephemeral=True)
            
        data = self.load_data()
        voleur = self.get_user(interaction.user.id, data)
        victime = self.get_user(cible.id, data)
        
        if voleur["portefeuille"] < montant:
            return await interaction.response.send_message("❌ Vous devez posséder la somme en liquide sur vous pour couvrir les risques d'échec !", ephemeral=True)
        if victime["portefeuille"] < montant:
            return await interaction.response.send_message("❌ La cible n'a pas cette somme en liquide sur elle.", ephemeral=True)
            
        # Vérification protecteur
        if victime["items"].get("protecteur", 0) > 0:
            victime["items"]["protecteur"] -= 1
            self.save_data(data)
            return await interaction.response.send_message(f"🛡️ Le **Protecteur de compte** de {cible.display_name} s'est activé ! Le vol a échoué sans perte pour vous.")

        # Tirage : 1 chance sur 3 (ex: si random vaut 1)
        if random.randint(1, 3) == 1:
            voleur["portefeuille"] += montant
            victime["portefeuille"] -= montant
            embed = discord.Embed(title="✅ BRAQUAGE RÉUSSI", color=0x2ECC71, description=f"Vous avez volé `{montant:,} €` à {cible.mention} !".replace(",", " "))
        else:
            voleur["portefeuille"] -= montant
            embed = discord.Embed(title="🚨 BRAQUAGE ÉCHOUÉ", color=0xE74C3C, description=f"La cible s'est défendue ! Vous perdez `{montant:,} €`.".replace(",", " "))
            
        self.save_data(data)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(CasinoBoutique(bot))
