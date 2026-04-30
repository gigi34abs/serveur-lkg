import requests
import threading
import time

# L'URL de ton bot
BOT_URL = "http://discord-bot--gigzi34.replit.app:5000/"

def keep_alive():
    """Ping le bot toutes les 3 minutes"""
    while True:
        try:
            requests.get(BOT_URL)
            print("✅ Ping envoyé au bot")
        except Exception as e:
            print(f"❌ Erreur lors du ping: {e}")
        
        # Attendre 3 minutes (180 secondes)
        time.sleep(180)

# Lancer en arrière-plan
thread = threading.Thread(target=keep_alive, daemon=True)
thread.start()
