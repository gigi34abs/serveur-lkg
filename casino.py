import discord
from discord.ext import commands
from discord import app_commands
import json
import os

class CasinoPrincipal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.file_path = "casino_data.json"
        self._ensure_database()

    def _ensure_database(self):
        if not os.path.exists(self.file_path):
            initial_data = {
                "users": {},
                "shop": {
                    "protecteur": {"nom": "Protecteur de compte", "prix": 1500, "desc": "Protège contre 1 vol"},
                    "doubleur": {"nom": "Doubleur de gains", "prix": 5000, "desc": "Double le prochain gain de jeu"}
                }
            }
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=4, ensure_ascii=False)

    def load_data(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_data(self, data):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def get_user(self, user_id, data):
        uid = str(user_id)
        if uid not in data["users"]:
            data["users"][uid] = {
                "portefeuille": 1000,
                "banque": 0,
                "items": {"protecteur": 0, "doubleur": 0}
            }
        return data["users"][uid]

    # --- SANS TIRETS : SYSTÈME DE GAIN PAR MESSAGE (5€) ---
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        data = self.load_data()
        user = self.get_user(message.author.id, data)
        user["portefeuille"] += 5
        self.save_data(data)

    # --- GROUPE BANQUE (Commandes : /banque solde, /banque deposer, /banque retirer) ---
    banque_group = app_commands.Group(name="banque", description="Gestion de vos finances")

    @banque_group.command(name="solde", description="Afficher votre solde et votre inventaire")
    async def banque_solde(self, interaction: discord.Interaction):
        data = self.load_data()
        user = self.get_user(interaction.user.id, data)
        
        embed = discord.Embed(title=f"🏦 Compte de {interaction.user.display_name}", color=0x2F3136)
        embed.add_field(name="👛 Portefeuille", value=f"**{user['portefeuille']:,} €**".replace(",", " "), inline=True)
        embed.add_field(name="🏦 Banque", value=f"**{user['banque']:,} €**".replace(",", " "), inline=True)
        
        prod = user["items"].get("protecteur", 0)
        doub = user["items"].get("doubleur", 0)
        embed.add_field(name="📦 Inventaire", value=f"🛡️ Protecteurs : {prod}\n⚡ Doubleurs : {doub}", inline=False)
        
        await interaction.response.send_message(embed=embed)

    @banque_group.command(name="deposer", description="Déposer de l'argent du portefeuille vers la banque")
    async def banque_deposer(self, interaction: discord.Interaction, montant: int):
        if montant <= 0:
            return await interaction.response.send_message("❌ Montant invalide.", ephemeral=True)
        
        data = self.load_data()
        user = self.get_user(interaction.user.id, data)
        
        if user["portefeuille"] < montant:
            return await interaction.response.send_message("❌ Vous n'avez pas assez d'argent sur vous.", ephemeral=True)
            
        user["portefeuille"] -= montant
        user["banque"] += montant
        self.save_data(data)
        
        await interaction.response.send_message(f"✅ Vous avez déposé **{montant:,} €** dans votre banque !".replace(",", " "))

    @banque_group.command(name="retirer", description="Retirer de l'argent de la banque vers le portefeuille")
    async def banque_retirer(self, interaction: discord.Interaction, montant: int):
        if montant <= 0:
            return await interaction.response.send_message("❌ Montant invalide.", ephemeral=True)
        
        data = self.load_data()
        user = self.get_user(interaction.user.id, data)
        
        if user["banque"] < montant:
            return await interaction.response.send_message("❌ Vous n'avez pas assez d'argent en banque.", ephemeral=True)
            
        user["banque"] -= montant
        user["portefeuille"] += montant
        self.save_data(data)
        
        await interaction.response.send_message(f"✅ Vous avez retiré **{montant:,} €** de votre banque !".replace(",", " "))

    # --- SANS TIRETS : COMMANDE CLASSEMENT ---
    @app_commands.command(name="classement", description="🏆 Voir les plus riches du casino")
    async def classement(self, interaction: discord.Interaction):
        data = self.load_data()
        
        leaderboard = []
        for uid, udata in data["users"].items():
            total = udata["portefeuille"] + udata["banque"]
            leaderboard.append((uid, total))
            
        leaderboard.sort(key=lambda x: x[1], reverse=True)
        
        embed = discord.Embed(title="🏆 CLASSEMENT DES MILLIONNAIRES", color=0xF1C40F)
        
        top_10 = leaderboard[:10]
        desc = ""
        for i, (uid, total) in enumerate(top_10, start=1):
            member = interaction.guild.get_member(int(uid))
            name = member.display_name if member else f"Utilisateur {uid}"
            desc += f"**#{i}** | {name} : `{total:,} €`\n".replace(",", " ")
            
        embed.description = desc if desc else "Aucun joueur enregistré."
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(CasinoPrincipal(bot))
