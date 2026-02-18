import discord
from discord.ext import commands
import config
import os
import json
import asyncio
import requests
from threading import Thread
# Importaciones para la API
from quart import Quart, request
from quart_cors import cors
from hypercorn.asyncio import serve
from hypercorn.config import Config

# ----------------------------
# Configuración de la API (Tickets)
# ----------------------------
app = Quart(__name__)
# Permitimos CORS para que tu GitHub Pages pueda hablar con Render
app = cors(app, allow_origin="https://pollitoscripts.github.io")

@app.route('/')
async def index():
    return {"status": "online", "message": "Blitz Hub API is running"}, 200

@app.route('/ticket', methods=['POST'])
async def handle_ticket():
    try:
        data = await request.get_json()
        
        # 1. Identificación de Prioridad
        # Limpiamos el ID por si el usuario pone espacios o minúsculas
        cliente_id_raw = data.get('cliente_id', "GUEST")
        cliente_id = cliente_id_raw.strip().upper() if cliente_id_raw else "GUEST"
        es_vip = cliente_id != "GUEST"
        
        # 2. Selección de Canal (VIP vs GUEST)
        id_canal_guest = os.getenv('ID_CANAL_SOPORTE')
        id_canal_vip = os.getenv('ID_CANAL_VIP')
        
        canal_id_final = int(id_canal_vip) if es_vip and id_canal_vip else int(id_canal_guest)
        canal = bot.get_channel(canal_id_final)
        
        if not canal:
            try:
                canal = await bot.fetch_channel(canal_id_final)
            except:
                return {"status": "error", "message": "Canal de destino no encontrado"}, 500

        # 3. Estética del Embed según rango
        color_final = discord.Color.gold() if es_vip else discord.Color.blue()
        titulo_final = "👑 NUEVA INCIDENCIA VIP" if es_vip else "👤 CONSULTA GUEST"

        embed = discord.Embed(
            title=titulo_final,
            color=color_final,
            timestamp=discord.utils.utcnow()
        )
        
        if es_vip:
            embed.set_author(name="SOPORTE PREMIUM BLITZ", icon_url="https://cdn-icons-png.flaticon.com/512/2533/2533049.png")
        
        embed.add_field(name="👤 Cliente", value=data.get('nombre', 'Desconocido'), inline=True)
        embed.add_field(name="📧 Email", value=data.get('email', 'N/A'), inline=True)
        embed.add_field(name="🔑 ID Contrato", value=f"`{cliente_id}`", inline=True)
        embed.add_field(name="📝 Problema", value=data.get('problema', 'Sin descripción'), inline=False)
        embed.set_footer(text=f"Blitz Hub System • {'PRIORIDAD ALTA' if es_vip else 'PRIORIDAD NORMAL'}")

        # 4. Envío seguro entre hilos
        async def send_msg():
            await bot.wait_until_ready()
            # Mención opcional para VIPs fuera del embed para asegurar notificación
            content = "👑 **NUEVA SOLICITUD VIP RECIBIDA**" if es_vip else None
            await canal.send(content=content, embed=embed)

        bot.loop.create_task(send_msg())
        
        print(f"✅ Ticket de {data.get('nombre')} enviado a {'CANAL VIP 👑' if es_vip else 'Soporte General'}")
        return {"status": "success", "message": "Ticket procesado correctamente"}, 200

    except Exception as e:
        print(f"⚠️ Error en API: {e}")
        return {"status": "error", "message": str(e)}, 500

# ----------------------------
# Hilo del Servidor Web (Hypercorn)
# ----------------------------
def run_web():
    port = int(os.getenv("PORT", 8080))
    config_hyper = Config()
    config_hyper.bind = [f"0.0.0.0:{port}"]
    
    # Creamos un nuevo loop para Quart en este hilo
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    shutdown_event = asyncio.Event()
    print(f"🌐 API activa en puerto: {port}")
    
    try:
        loop.run_until_complete(serve(app, config_hyper, shutdown_trigger=shutdown_event.wait))
    except Exception as e:
        print(f"⚠️ Error servidor web: {e}")

# ----------------------------
# Configuración del bot
# ----------------------------
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

async def load_extensions():
    if not os.path.exists("./cogs"): return
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and filename not in ["__init__.py", "webserver.py"]:
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
            except Exception as e:
                print(f"❌ Error en '{filename}': {e}")

# ----------------------------
# Eventos & Tareas
# ----------------------------
@bot.event
async def on_ready():
    print(f"🤖 BOT ONLINE: {bot.user.name}")
    await load_extensions()

async def self_ping():
    await asyncio.sleep(30)
    # URL de tu app en Render para que no se duerma
    url = "https://pollitos-discord.onrender.com/"
    while True:
        try:
            # Petición asíncrona simple
            await asyncio.get_event_loop().run_in_executor(None, requests.get, url)
            print("🔔 Autoping exitoso.")
        except:
            pass
        await asyncio.sleep(600) # Cada 10 minutos

# ----------------------------
# Inicio Principal
# ----------------------------
async def main():
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("❌ ERROR: No hay DISCORD_TOKEN.")
        return

    # 1. API en hilo separado
    t = Thread(target=run_web, daemon=True)
    t.start()

    # 2. Tarea de autoping
    asyncio.create_task(self_ping())

    # 3. Arrancar Bot
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
