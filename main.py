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

Thread(target=webserver.run, daemon=True).start()


# ----------------------------
# Configuración del bot
# ----------------------------
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# ----------------------------
# Función para cargar cogs
# ----------------------------
async def load_extensions():
    print("Cargando extensiones...")
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and filename != "__init__.py" and filename != "webserver.py":
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"Cog cargado: {filename}")
            except Exception as e:
                print(f"No se pudo cargar '{filename}': {e}")
    print("Extensiones cargadas.")

# ----------------------------
# Servicio de ejemplo: enviar mensajes con embeds
# ----------------------------
async def services():
    channel = bot.get_channel(config.channel_id)
    if channel is None:
        for _ in range(5):
            print(f"⚠️ No se encontró el canal {config.channel_id}, reintentando en 5s...")
            await asyncio.sleep(5)
            channel = bot.get_channel(config.channel_id)
            if channel:
                break
    if channel is None:
        print("❌ No se pudo acceder al canal después de varios intentos.")
        return

    print(f"Enviando mensajes al canal {channel.name}...")

    try:
        await channel.purge()
        with open("json/streaming_services.json", "r") as file:
            streaming_services = json.load(file)["streaming_services"]

        for service in streaming_services:
            embed = discord.Embed(
                title=service["name"],
                description=service["description"],
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=service["image"])

            for plan in service["plans"]:
                plan_details = ""
                if plan["price_per_month"] != 0:
                    plan_details += f"**Precio**: ${plan['price_per_month']}\n"
                if plan["resolution"] != "N/A":
                    plan_details += f"**Resolución**: {plan['resolution']}\n"
                if "ads" in plan and plan["ads"] != "No Ads":
                    plan_details += f"**Anuncios**: {plan['ads']}\n"

                embed.add_field(name=plan["name"], value=plan_details, inline=True)

            message = await channel.send(embed=embed)
            await message.add_reaction("✅")

        print("Mensajes enviados correctamente.")
    except Exception as e:
        print(f"Error al enviar mensajes: {e}")

# ----------------------------
# Eventos del bot
# ----------------------------
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user.name}")
    await load_extensions()

# Comando de prueba para enviar servicios
@bot.command()
async def servicios(ctx):
    await services()
    await ctx.send("Servicios enviados.")

# ----------------------------
# Webserver en paralelo
# ----------------------------
def start_webserver():
    Thread(target=webserver.run).start()

# ----------------------------
# Autoping para Render
# ----------------------------
async def self_ping():
    url = "https://pollitos-discord.onrender.com/"
    while True:
        try:
            print("🔔 Ping al Web Service para mantenerlo activo...")
            requests.get(url)
        except Exception as e:
            print(f"⚠️ Error en ping: {e}")
        await asyncio.sleep(10 * 60)  # 10 minutos

# ----------------------------
# Watchdog para reiniciar el bot
# ----------------------------
async def start_bot_loop():
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        raise ValueError("No se encontró DISCORD_TOKEN en Render.")

    while True:
        try:
            print("⚡ Iniciando bot...")
            await bot.start(TOKEN)
        except Exception as e:
            print(f"❌ Bot crasheó: {e}")
            print("⏳ Reiniciando en 5 segundos...")
            await asyncio.sleep(5)

# ----------------------------
# Función principal
# ----------------------------
async def main():
    start_webserver()                # Levanta Flask
    asyncio.create_task(self_ping()) # Arranca autoping
    await start_bot_loop()           # Arranca bot con watchdog

# ----------------------------
# Ejecutar
# ----------------------------
if __name__ == "__main__":
    asyncio.run(main())
