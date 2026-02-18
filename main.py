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
# Configuración de la API (Tickets & Empresa)
# ----------------------------
app = Quart(__name__)
app = cors(app, allow_origin="https://pollitoscripts.github.io")

# Cargamos las IDs desde variables de entorno de Render
CAT_VIP = int(os.getenv('CAT_VIP_ID', 0))
CAT_ESTANDAR = int(os.getenv('CAT_ESTANDAR_ID', 0))
ID_ROL_DEV = int(os.getenv('ID_ROL_DEV', 0))

@app.route('/')
async def index():
    return {"status": "online", "message": "Blitz Hub API is running"}, 200

@app.route('/ticket', methods=['POST'])
async def handle_ticket():
    try:
        data = await request.get_json()
        
        # 1. Recogida de datos
        cliente_id_raw = data.get('cliente_id', "").strip().upper()
        nombre_usuario = data.get('nombre', 'Desconocido')
        nombre_empresa_web = data.get('empresa', '').strip().upper() 
        discord_id_web = data.get('discord_id', '').strip()
        problema = data.get('problema', 'Sin descripción')
        
        es_vip = False
        gist_id = os.getenv('GIST_ID')
        github_token = os.getenv('GITHUB_TOKEN')
        
        # 2. Lógica de Gist y VIP
        if gist_id and github_token:
            try:
                headers = {"Authorization": f"token {github_token}"}
                r = requests.get(f"https://api.github.com/gists/{gist_id}", headers=headers)
                if r.status_code == 200:
                    gist_content = r.json()
                    db = json.loads(gist_content['files']['clientes.json']['content'])
                    if cliente_id_raw in db:
                        es_vip = True
                        nombre_final = db[cliente_id_raw].get('empresa', nombre_empresa_web)
                    else:
                        nombre_final = nombre_empresa_web if nombre_empresa_web else "GUEST"
            except: nombre_final = nombre_empresa_web

        # 3. Función interna para enviar/crear canal
        async def process_discord_side():
            await bot.wait_until_ready()
            
            ID_CAT_ARCHIVADOS = 1473689333964738633
            cat_id_activa = int(os.getenv('CAT_VIP_ID')) if es_vip else int(os.getenv('CAT_ESTANDAR_ID'))
            
            guild = bot.guilds[0] # El bot asume que está en tu servidor principal
            member = guild.get_member(int(discord_id_web)) if discord_id_web.isdigit() else None

            # Generamos un nombre único basado en tiempo o ID para que no colisione con el archivado
            # Ejemplo: apple-pepe-1422
            from datetime import datetime
            suffix = datetime.now().strftime("%H%M")
            nombre_nuevo_canal = f"{nombre_final.lower()}-{nombre_usuario.lower()}-{suffix}".replace(" ", "-")

            # Definir Embed
            embed = discord.Embed(title=f"🎫 Nueva Incidencia: {nombre_final}", color=discord.Color.gold() if es_vip else discord.Color.blue())
            embed.add_field(name="👤 Usuario", value=nombre_usuario, inline=True)
            embed.add_field(name="🔑 ID Soporte", value=f"`{cliente_id_raw if cliente_id_raw else 'GUEST'}`", inline=True)
            embed.add_field(name="📝 Problema", value=problema, inline=False)

            if member:
                # EL USUARIO YA ESTÁ EN EL DISCORD -> CREAMOS CANAL DIRECTO
                category = guild.get_channel(cat_id_activa)
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                    guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
                }
                # Dar acceso al Dev
                rol_dev = guild.get_role(int(os.getenv('ID_ROL_DEV')))
                if rol_dev: overwrites[rol_dev] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

                nuevo_canal = await guild.create_text_channel(name=nombre_nuevo_canal, category=category, overwrites=overwrites)
                await nuevo_canal.send(content=f"{member.mention} Bienvenido a tu nuevo ticket de soporte.", embed=embed)
                if es_vip and rol_dev: await nuevo_canal.send(f"{rol_dev.mention} 🚨 Ticket VIP Urgente.")
            else:
                # EL USUARIO NO ESTÁ -> Mandamos al canal de Staff general
                canal_staff_id = int(os.getenv('ID_CANAL_VIP' if es_vip else 'ID_CANAL_SOPORTE'))
                canal_staff = bot.get_channel(canal_staff_id)
                await canal_staff.send(content=f"⚠️ Usuario fuera del server: <@{discord_id_web}>", embed=embed)

        bot.loop.create_task(process_discord_side())
        return {"status": "success", "message": "Ticket procesado"}, 200

    except Exception as e:
        print(f"Error: {e}")
        return {"status": "error", "message": str(e)}, 500

# ----------------------------
# Servidor Web & Bot Setup
# ----------------------------
def run_web():
    port = int(os.getenv("PORT", 8080))
    config_hyper = Config()
    config_hyper.bind = [f"0.0.0.0:{port}"]
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(serve(app, config_hyper, shutdown_trigger=asyncio.Event().wait))
    except Exception as e:
        print(f"⚠️ Error Hypercorn: {e}")

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

async def load_extensions():
    if not os.path.exists("./cogs"): return
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and filename not in ["__init__.py", "webserver.py"]:
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"✅ Cog cargado: {filename}")
            except Exception as e:
                print(f"❌ Error cog {filename}: {e}")

@bot.event
async def on_ready():
    print(f"🤖 BOT ONLINE: {bot.user.name}")
    await load_extensions()

@bot.command()
async def servicios(ctx):
    await services()
    await ctx.send("✅ Lista de servicios actualizada.")

async def self_ping():
    await asyncio.sleep(30)
    url = "https://pollitos-discord.onrender.com/"
    while True:
        try:
            await asyncio.get_event_loop().run_in_executor(None, requests.get, url)
        except: pass
        await asyncio.sleep(600)

async def main():
    TOKEN = os.getenv("DISCORD_TOKEN")
    Thread(target=run_web, daemon=True).start()
    asyncio.create_task(self_ping())
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
