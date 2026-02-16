import discord
from discord.ext import commands
from discord.ui import Select, View
import config
import os
import json
import asyncio
import time
import requests  # <-- necesario para el autoping
from threading import Thread

# Importa tu webserver desde cogs
from cogs import webserver  # Ahora apunta a cogs/webserver.py

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

####    Inicio del Bot      ####

async def load_extensions():
    print("Cargando extensiones")
    for filename in os.listdir("./cogs"):
        try:
            if filename.endswith(".py") and filename != "__init__.py" and filename != "webserver.py":
                await bot.load_extension(f"cogs.{filename[:-3]}")
        except Exception as e:
            print(f"No se pudo cargar la extensión '{filename[:-3]}': {e}")
    print("Extensiones cargadas.")

async def services():
    channel = bot.get_channel(config.channel_id)
    
    if channel is None:
        retries = 0
        while channel is None and retries < 5:
            print(f'⚠️ No se encontró el canal {config.channel_id}, reintentando en 5s...')
            await asyncio.sleep(5)
            channel = bot.get_channel(config.channel_id)
            retries += 1

    if channel is None:
        print(f'❌ No se pudo acceder al canal después de varios intentos.')
        return

    print(f'Enviando mensajes al canal {channel.name}.')

    try:
        await channel.purge()

        with open('json/streaming_services.json', 'r') as file:
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
                if plan['resolution'] != 'N/A':
                    plan_details += f"**Resolución**: {plan['resolution']}\n"
                if "ads" in plan and plan['ads'] != "No Ads":
                    plan_details += f"**Anuncios**: {plan['ads']}\n"

                embed.add_field(name=plan["name"], value=plan_details, inline=True)

            message = await channel.send(embed=embed)
            await message.add_reaction('✅')

        print('Mensajes enviados correctamente.')

    except Exception as e:
        print(f'Error al enviar mensajes: {e}')

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user.name}')
    await load_extensions()

@bot.command()
async def servicios(ctx):
    await services()
    await ctx.send("Servicios enviados.")

#### Token ####

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("No se encontró el token de Discord. Asegúrate de configurar DISCORD_TOKEN en Render.")

# ----------------------------
# Arrancar Flask en paralelo desde cogs/webserver.py
# ----------------------------
Thread(target=webserver.run).start()

# ----------------------------
# Autoping para mantener activo el Web Service
# ----------------------------
def self_ping():
    url = "https://pollitos-discord.onrender.com/"  # <--- Cambia esto por tu URL real
    while True:
        try:
            print("🔔 Ping al Web Service para mantenerlo activo...")
            requests.get(url)
        except Exception as e:
            print(f"⚠️ Error en ping: {e}")
        time.sleep(10 * 60)  # cada 10 minutos

Thread(target=self_ping).start()

# ----------------------------
# Watchdog para reinicio automático
# ----------------------------
def start_bot():
    while True:
        try:
            print("⚡ Iniciando bot...")
            bot.run(TOKEN)
        except Exception as e:
            print(f"❌ Bot crasheó: {e}")
            print("⏳ Reiniciando en 5 segundos...")
            time.sleep(5)

# ----------------------------
# Ejecutar
# ----------------------------
if __name__ == "__main__":
    start_bot()
