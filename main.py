import discord
from discord.ext import commands
import config
import os
import json
import asyncio
import time
import requests
from cogs import webserver
from threading import Thread

# 1. El servidor web debe ir en un hilo totalmente separado y "daemon"
def run_web():
    webserver.run()

# ----------------------------
# Configuración del bot
# ----------------------------
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# ----------------------------
# Función para cargar cogs
# ----------------------------
async def load_extensions():
    print("📂 Cargando extensiones...")
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and filename not in ["__init__.py", "webserver.py"]:
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"✅ Cog cargado: {filename}")
            except Exception as e:
                print(f"❌ Error en '{filename}': {e}")

# ----------------------------
# Servicio de streaming (Solo manual)
# ----------------------------
async def services():
    channel = bot.get_channel(config.channel_id)
    if channel is None:
        print(f"ℹ️ Canal {config.channel_id} no encontrado. Función 'servicios' disponible solo donde exista el canal.")
        return

    try:
        await channel.purge()
        with open("json/streaming_services.json", "r") as file:
            streaming_services = json.load(file)["streaming_services"]

        for service in streaming_services:
            embed = discord.Embed(title=service["name"], description=service["description"], color=discord.Color.blue())
            embed.set_thumbnail(url=service["image"])
            for plan in service["plans"]:
                details = f"**Precio**: ${plan['price_per_month']}\n" if plan["price_per_month"] != 0 else ""
                details += f"**Resolución**: {plan['resolution']}\n" if plan["resolution"] != "N/A" else ""
                embed.add_field(name=plan["name"], value=details if details else "Información no disponible", inline=True)
            await channel.send(embed=embed)
        print("✅ Mensajes de servicios actualizados.")
    except Exception as e:
        print(f"❌ Error en services: {e}")

# ----------------------------
# Eventos
# ----------------------------
@bot.event
async def on_ready():
    print(f"🤖 BOT ONLINE: {bot.user.name}")
    print(f"🌍 Conectado a {len(bot.guilds)} servidores.")
    await load_extensions()

@bot.command()
async def servicios(ctx):
    await services()
    await ctx.send("Servicios enviados.")

# ----------------------------
# Autoping (Corregido para no saturar)
# ----------------------------
async def self_ping():
    await asyncio.sleep(60) # Espera 1 minuto a que todo estabilice
    url = "https://pollitos-discord.onrender.com/"
    while True:
        try:
            # Usamos un hilo para el request de red para no bloquear el bot
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, requests.get, url)
            print("🔔 Autoping exitoso.")
        except:
            pass
        await asyncio.sleep(600)

# ----------------------------
# Inicio del Bot
# ----------------------------
# --- Al final de tu archivo main.py ---

async def main():
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("❌ ERROR: No hay DISCORD_TOKEN.")
        return

    # 1. Lanzamos el webserver en un hilo separado (Thread)
    # Esto es vital para que no bloquee el inicio del bot
    t = Thread(target=run_web, daemon=True)
    t.start()
    print("🌐 Webserver iniciado en hilo separado.")

    # 2. Lanzamos el autoping como tarea de fondo
    asyncio.create_task(self_ping())

    # 3. Arrancamos el bot (Esta debe ser la ÚLTIMA línea)
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
