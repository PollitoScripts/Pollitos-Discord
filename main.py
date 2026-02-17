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
# Nuevas importaciones para la API de tickets
from quart import Quart, request
from quart_cors import cors

# ----------------------------
# Configuración de la API (Tickets)
# ----------------------------
app = Quart(__name__)
app = cors(app) # Permite peticiones desde dominios externos como GitHub Pages

@app.route('/ticket', methods=['POST'])
async def handle_ticket():
    data = await request.get_json()
    
    # Obtenemos el canal de soporte desde config o variables de entorno
    # Usamos la variable ID_CANAL_SOPORTE que configuramos en Render
    canal_id = int(os.getenv('ID_CANAL_SOPORTE', 0))
    canal = bot.get_channel(canal_id)
    
    if canal:
        embed = discord.Embed(
            title="🚀 Nueva Entrada de Soporte (Web)",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="👤 Cliente", value=data.get('nombre', 'Desconocido'), inline=True)
        embed.add_field(name="📧 Email", value=data.get('email', 'N/A'), inline=True)
        embed.add_field(name="🔑 ID Contrato", value=data.get('cliente_id') or "GUEST", inline=True)
        embed.add_field(name="📝 Problema", value=data.get('problema', 'Sin descripción'), inline=False)
        embed.set_footer(text="Blitz Hub System")
        
        # Enviamos el mensaje al canal de soporte
        await canal.send(embed=embed)
        return {"status": "success", "message": "Ticket enviado correctamente"}, 200
    
    return {"status": "error", "message": "Configuración de canal inválida"}, 500

# ----------------------------
# Hilo del Servidor Web
# ----------------------------
def run_web():
    # Iniciamos Quart en el puerto que Render asigna
    port = int(os.getenv("PORT", 8080))
    # Quart requiere su propio loop o ejecutarse de forma específica
    # Usamos app.run para el hilo separado
    app.run(host='0.0.0.0', port=port)

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
# Servicio de streaming (Sin cambios)
# ----------------------------
async def services():
    channel = bot.get_channel(config.channel_id)
    if channel is None:
        print(f"ℹ️ Canal {config.channel_id} no encontrado.")
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
# Autoping
# ----------------------------
async def self_ping():
    await asyncio.sleep(60) 
    url = "https://pollitos-discord.onrender.com/"
    while True:
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, requests.get, url)
            print("🔔 Autoping exitoso.")
        except:
            pass
        await asyncio.sleep(600)

# ----------------------------
# Inicio del Bot
# ----------------------------
async def main():
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("❌ ERROR: No hay DISCORD_TOKEN.")
        return

    # 1. Lanzamos el servidor de tickets y web en el hilo separado
    t = Thread(target=run_web, daemon=True)
    t.start()
    print("🌐 API de Tickets y Webserver iniciados en hilo separado.")

    # 2. Lanzamos el autoping
    asyncio.create_task(self_ping())

    # 3. Arrancamos el bot
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot apagado manualmente.")
