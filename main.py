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

# Iniciamos el webserver antes que nada
Thread(target=webserver.run, daemon=True).start()

# ----------------------------
# Configuración del bot
# ----------------------------
# Asegúrate de tener activados los 3 Intents en el Discord Developer Portal
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
    # Buscamos el canal definido en config
    channel = bot.get_channel(config.channel_id)
    
    # CAMBIO CRÍTICO: Si el canal no existe (como en tu nuevo servidor),
    # el bot simplemente avisa y sale de la función sin quedarse atrapado.
    if channel is None:
        print(f"ℹ️ Canal {config.channel_id} no encontrado. Saltando servicios de streaming (esto es normal en servidores nuevos).")
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
    # Cargamos los cogs primero para que el sistema de clientes esté listo
    await load_extensions()
    
    # Lanzamos la actualización de servicios como una tarea de fondo
    # para que si falla o no encuentra el canal, no afecte al bot.
    

# Comando de prueba para enviar servicios
@bot.command()
async def servicios(ctx):
    await services()
    await ctx.send("Servicios enviados.")

# ----------------------------
# Webserver en paralelo
# ----------------------------
def start_webserver():
    # Nota: webserver.run ya se inicia arriba con daemon=True, 
    # mantenemos esto por compatibilidad con tu función main()
    pass

# ----------------------------
# Autoping para Render
# ----------------------------
async def self_ping():
    url = "https://pollitos-discord.onrender.com/"
    while True:
        try:
            # Esperamos a que el bot esté listo antes del primer ping
            await asyncio.sleep(60) 
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
    # start_webserver() se omite aquí porque ya corre al inicio del script
    asyncio.create_task(self_ping()) # Arranca autoping
    await start_bot_loop()           # Arranca bot con watchdog

# ----------------------------
# Ejecutar
# ----------------------------
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot apagado manualmente.")
