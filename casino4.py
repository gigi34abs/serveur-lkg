import discord
from discord.ext import commands
from discord import app_commands
import json
import asyncio
import random

class CasinoJeux(commands.Cog):
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
        return data["users"].get(uid, {"portefeuille": 1000, "banque": 0, "items": {"doubleur": 0}})

    # --- INTERACTION : SYSTÈME DE CREATION DE LOBBY MULTIJOUEUR ---
    async def create_team_lobby(self, interaction, nom_jeu, mise):
        embed = discord.Embed(
            title=f"🎮 Salon de Match : {nom_jeu}",
            description=f"Mise requise : **{mise} €** par joueur\n\n**Équipe 1** (0/5) :\n*Personne*\n\n**Équipe 2** (0/5) :\n*Personne*",
            color=0x3498DB
        )
        
        class LobbyView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.team1 = []
                self.team2 = []
                self.start_game = False

            @discord.ui.button(label="Rejoindre Équipe 1", style=discord.py_button_style if hasattr(discord, 'py_button_style') else discord.ButtonStyle.primary)
            async def join_t1(self, inter, button):
                if inter.user in self.team1 or inter.user in self.team2:
                    return await inter.response.send_message("Tu es déjà inscrit !", ephemeral=True)
                if len(self.team1) >= 5:
                    return await inter.response.send_message("Équipe complète !", ephemeral=True)
                self.team1.append(inter.user)
                await self.update_embed(inter)

            @discord.ui.button(label="Rejoindre Équipe 2", style=discord.py_button_style if hasattr(discord, 'py_button_style') else discord.ButtonStyle.danger)
            async def join_t2(self, inter, button):
                if inter.user in self.team1 or inter.user in self.team2:
                    return await inter.response.send_message("Tu es déjà inscrit !", ephemeral=True)
                if len(self.team2) >= 5:
                    return await inter.response.send_message("Équipe complète !", ephemeral=True)
                self.team2.append(inter.user)
                await self.update_embed(inter)

            @discord.ui.button(label="Lancer la Partie", style=discord.py_button_style if hasattr(discord, 'py_button_style') else discord.ButtonStyle.success)
            async def lancer(self, inter, button):
                if inter.user != interaction.user:
                    return await inter.response.send_message("Seul le créateur peut lancer !", ephemeral=True)
                if len(self.team1) != len(self.team2) or len(self.team1) == 0:
                    return await inter.response.send_message("Les équipes doivent être équilibrées (ex: 1v1 à 5v5) !", ephemeral=True)
                self.start_game = True
                self.stop()
                await inter.response.defer()

            async def update_embed(self, inter):
                t1_text = "\n".join([m.mention for m in self.team1]) if self.team1 else "*Personne*"
                t2_text = "\n".join([m.mention for m in self.team2]) if self.team2 else "*Personne*"
                embed.description = f"Mise requise : **{mise} €** par joueur\n\n**Équipe 1** ({len(self.team1)}/5) :\n{t1_text}\n\n**Équipe 2** ({len(self.team2)}/5) :\n{t2_text}"
                await inter.response.edit_message(embed=embed, view=self)

        view = LobbyView()
        await interaction.response.send_message(embed=embed, view=view)
        await view.wait()
        return view.start_game, view.team1, view.team2

    # --- COMMANDE JEU MULTIJOUEUR : /match tireur, /match des, /match cartes ---
    match_group = app_commands.Group(name="match", description="Jeux de paris en équipe 1v1 à 5v5")

    @match_group.command(name="tireur", description="🔫 Duel de précision stratégique au tour par tour")
    async def match_tireur(self, interaction: discord.Interaction, mise: int):
        if mise < 10 or mise > 10000:
            return await interaction.response.send_message("❌ Paris autorisés de 10 € à 10 000 €.", ephemeral=True)
            
        data = self.load_data()
        # Validation préliminaire du portefeuille de l'hôte
        if self.get_user(interaction.user.id, data)["portefeuille"] < mise:
            return await interaction.response.send_message("❌ Vous n'avez pas l'argent sur vous.", ephemeral=True)

        start, t1, t2 = await self.create_team_lobby(interaction, "Le Stand de Tir", mise)
        if not start:
            return

        # Prélèvement des mises
        data = self.load_data()
        for u in t1 + t2:
            if data["users"].get(str(u.id), {}).get("portefeuille", 0) < mise:
                return await interaction.channel.send(f"❌ Partie annulée, {u.mention} n'a plus assez d'argent.")
            data["users"][str(u.id)]["portefeuille"] -= mise
        self.save_data(data)

        cash_pool = mise * (len(t1) + len(t2))
        hp_t1, hp_t2 = len(t1) * 100, len(t2) * 100
        
        await interaction.channel.send(f"🏁 **Le match commence !** Cagnotte totale : **{cash_pool} €**. 5 minutes max.")
        
        # Déroulement manuel (Tour par tour - 30 secondes max d'action)
        tour = 1
        for _ in range(10): # Limite de tours pour respecter les 5 mins max
            current_team = t1 if tour % 2 != 0 else t2
            target_team_name = "Équipe 2" if tour % 2 != 0 else "Équipe 1"
            
            # Choix d'un joueur actif vivant dans l'équipe
            shooter = current_team[(tour - 1) % len(current_team)]
            
            await interaction.channel.send(f"🎯 {shooter.mention}, c'est à toi de tirer sur l'**{target_team_name}** ! Tape `pan` dans le salon (30 secondes max !)")
            
            def check(m):
                return m.author == shooter and m.content.lower() == "pan" and m.channel == interaction.channel

            try:
                await self.bot.wait_for("message", check=check, timeout=30.0)
                # Succès du tir manuel
                degats = random.randint(25, 50)
                if tour % 2 != 0:
                    hp_t2 -= degats
                else:
                    hp_t1 -= degats
                await interaction.channel.send(f"💥 Tir réussi ! L'⏱️ {target_team_name} perd {degats} PV.")
            except asyncio.TimeoutError:
                # Abandon par timeout -> Attribution des gains à l'autre équipe
                winner_team = t2 if tour % 2 != 0 else t1
                await interaction.channel.send(f"⏱️ {shooter.mention} a arrêté de jouer ! Victoire par forfait.")
                await self._distribute_gains(winner_team, cash_pool)
                return

            if hp_t1 <= 0 or hp_t2 <= 0:
                break
            tour += 1

        # Calcul final de l'équipe gagnante (la plus avantageuse en PV restants)
        gagnants = t1 if hp_t1 > hp_t2 else t2
        await interaction.channel.send(f"🏆 Fin de la partie ! L'équipe gagnante remporte la cagnotte !")
        await self._distribute_gains(gagnants, cash_pool)

    @match_group.command(name="des", description="🎲 Somme de Dés stratégique en équipe")
    async def match_des(self, interaction: discord.Interaction, mise: int):
        if mise < 10 or mise > 10000:
            return await interaction.response.send_message("❌ Paris autorisés de 10 € à 10 000 €.", ephemeral=True)
            
        start, t1, t2 = await self.create_team_lobby(interaction, "La Tour des Dés", mise)
        if not start: return

        data = self.load_data()
        for u in t1 + t2:
            if data["users"].get(str(u.id), {}).get("portefeuille", 0) < mise:
                return await interaction.channel.send(f"❌ Partie annulée, {u.mention} n'a pas les fonds.")
            data["users"][str(u.id)]["portefeuille"] -= mise
        self.save_data(data)

        cash_pool = mise * (len(t1) + len(t2))
        score_t1, score_t2 = 0, 0
        
        # Déroulement du jeu de dés manuel
        for i in range(max(len(t1), len(t2))):
            # Équipe 1 Joue
            if i < len(t1):
                p = t1[i]
                await interaction.channel.send(f"🎲 {p.mention}, tape `lancer` pour jeter ton dé (30s) !")
                try:
                    await self.bot.wait_for("message", check=lambda m: m.author == p and m.content.lower() == "lancer", timeout=30.0)
                    r = random.randint(1, 6)
                    score_t1 += r
                    await interaction.channel.send(f"🎲 Résultat : **{r}** (Total Équipe 1 : {score_t1})")
                except asyncio.TimeoutError:
                    await interaction.channel.send(f"⏱️ Abandon de {p.mention}. L'Équipe 2 gagne le match !")
                    await self._distribute_gains(t2, cash_pool)
                    return
            # Équipe 2 Joue
            if i < len(t2):
                p = t2[i]
                await interaction.channel.send(f"🎲 {p.mention}, tape `lancer` pour jeter ton dé (30s) !")
                try:
                    await self.bot.wait_for("message", check=lambda m: m.author == p and m.content.lower() == "lancer", timeout=30.0)
                    r = random.randint(1, 6)
                    score_t2 += r
                    await interaction.channel.send(f"🎲 Résultat : **{r}** (Total Équipe 2 : {score_t2})")
                except asyncio.TimeoutError:
                    await interaction.channel.send(f"⏱️ Abandon de {p.mention}. L'Équipe 1 gagne le match !")
                    await self._distribute_gains(t1, cash_pool)
                    return

        gagnants = t1 if score_t1 >= score_t2 else t2
        await self._distribute_gains(gagnants, cash_pool)

    @match_group.command(name="cartes", description="🃏 Le Blackjack Collectif")
    async def match_cartes(self, interaction: discord.Interaction, mise: int):
        if mise < 10 or mise > 10000:
            return await interaction.response.send_message("❌ Paris autorisés de 10 € à 10 000 €.", ephemeral=True)
            
        start, t1, t2 = await self.create_team_lobby(interaction, "Le Blackjack des Clans", mise)
        if not start: return

        data = self.load_data()
        for u in t1 + t2:
            data["users"][str(u.id)]["portefeuille"] -= mise
        self.save_data(data)

        cash_pool = mise * (len(t1) + len(t2))
        score_t1, score_t2 = 0, 0

        # Chaque équipe a un capitaine désigné (le premier inscrit) pour tirer des cartes
        for t_idx, team in enumerate([t1, t2], start=1):
            cap = team[0]
            current_score = 0
            await interaction.channel.send(f"🃏 Tour de l'Équipe {t_idx}. Capitaine d'équipe : {cap.mention}")
            
            while current_score < 21:
                await interaction.channel.send(f"Score actuel : **{current_score}**. {cap.mention}, écris `carte` pour piocher ou `stop` pour t'arrêter (30s) :")
                try:
                    msg = await self.bot.wait_for("message", check=lambda m: m.author == cap and m.content.lower() in ["carte", "stop"], timeout=30.0)
                    if msg.content.lower() == "stop":
                        break
                    else:
                        valeur = random.randint(1, 10)
                        current_score += valeur
                        await interaction.channel.send(f"🃏 Carte piochée : +{valeur} ! Nouveau score : **{current_score}**")
                except asyncio.TimeoutError:
                    other_team = t2 if t_idx == 1 else t1
                    await interaction.channel.send(f"⏱️ Timeout du capitaine. L'autre équipe remporte le pot d'or !")
                    await self._distribute_gains(other_team, cash_pool)
                    return
            
            if t_idx == 1: score_t1 = current_score
            else: score_t2 = current_score

        # Vérification élimination (> 21)
        if score_t1 > 21 and score_t2 <= 21: gagnants = t2
        elif score_t2 > 21 and score_t1 <= 21: gagnants = t1
        else: gagnants = t1 if (21 - score_t1) < (21 - score_t2) else t2

        await self._distribute_gains(gagnants, cash_pool)

    # --- MÉTHODE PRIVÉE DE DISTRIBUTION & DE DOUBLEUR ---
    async def _distribute_gains(self, equipe, cash_total):
        data = self.load_data()
        gain_par_tete = int(cash_total / len(equipe))
        
        mentions = []
        for joueur in equipe:
            uid = str(joueur.id)
            final_gain = gain_par_tete
            
            # Application du bonus multiplicateur X2 si possédé
            if data["users"].get(uid, {}).get("items", {}).get("doubleur", 0) > 0:
                data["users"][uid]["items"]["doubleur"] -= 1
                final_gain = gain_par_tete * 2
                mentions.append(f"{joueur.display_name} ⚡ (X2 Activé ! -> +{final_gain}€)")
            else:
                mentions.append(f"{joueur.display_name} (+{final_gain}€)")
                
            data["users"][uid]["portefeuille"] += final_gain

        self.save_data(data)
        await self.bot.get_channel(equipe[0].current_argument if hasattr(equipe[0], 'current_argument') else equipe[0].guild.text_channels[0].id).send(
            f"🎉 **Félicitations !** Les gains ont été distribués aux vainqueurs :\n" + "\n".join(mentions)
        )

async def setup(bot):
    await bot.add_cog(CasinoJeux(bot))
