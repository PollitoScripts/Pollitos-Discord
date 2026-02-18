import discord
from discord.ext import commands
import config
import os
import json
import asyncio
import requests
from threading import Thread
from datetime import datetime
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
ID_SERVIDOR_BLITZ = int(os.getenv('ID_SERVIDOR_BLITZ', 0))

@app.route('/')
async def index():
    return {"status": "online", "message": "Blitz Hub API is running"}, 200

@app.route('/ticket', methods=['POST'])
async def handle_ticket():
    try:
        data = await request.get_json()
        cliente_id_raw = data.get('cliente_id', "").strip().upper()
        nombre_usuario = data.get('nombre', 'Desconocido')
        nombre_empresa_web = data.get('empresa', '').strip().upper() 
        discord_id_web = data.get('discord_id', '').strip()
        problema = data.get('problema', 'Sin descripción')
        
        es_vip = False
        gist_id = os.getenv('GIST_ID')
        github_token = os.getenv('GITHUB_TOKEN')
        nombre_final = nombre_empresa_web if nombre_empresa_web else "GUEST"

        # 1. Lógica de Gist para verificar VIP y ACTUALIZAR MAPA
        if gist_id and github_token:
            try:
                headers = {"Authorization": f"token {github_token}"}
                r = requests.get(f"https://api.github.com/gists/{gist_id}", headers=headers)
                if r.status_code == 200:
                    gist_data = r.json()
                    
                    # Verificar VIP en clientes.json
                    db = json.loads(gist_data['files']['clientes.json']['content'])
                    if cliente_id_raw in db:
                        es_vip = True
                        nombre_final = db[cliente_id_raw].get('empresa', nombre_final)
                    
                    # ACTUALIZAR mapa_discord.json inmediatamente
                    if discord_id_web:
                        mapa_content = gist_data['files'].get('mapa_discord.json', {'content': '{}'})['content']
                        mapa = json.loads(mapa_content)
                        mapa[str(discord_id_web)] = cliente_id_raw if cliente_id_raw else "GUEST"
                        
                        update_data = {
                            "files": {
                                "mapa_discord.json": {
                                    "content": json.dumps(mapa, indent=4)
                                }
                            }
                        }
                        requests.patch(f"https://api.github.com/gists/{gist_id}", headers=headers, json=update_data)
                        print(f"✅ Gist actualizado para ID: {discord_id_web}")

            except Exception as e:
                print(f"⚠️ Error procesando Gist: {e}")

        # 2. Función interna para Discord
        async def process_discord():
            await bot.wait_until_ready()
            guild = bot.get_guild(ID_SERVIDOR_BLITZ)
            if not guild: return

            member = guild.get_member(int(discord_id_web)) if discord_id_web.isdigit() else None
            
            # Registro para Staff
            id_canal_staff = int(os.getenv('ID_CANAL_VIP' if es_vip else 'ID_CANAL_SOPORTE', 0))
            canal_staff = bot.get_channel(id_canal_staff)

            embed = discord.Embed(title=f"🎫 Ticket: {nombre_final}", color=discord.Color.gold() if es_vip else discord.Color.blue(), timestamp=discord.utils.utcnow())
            embed.add_field(name="🏢 Empresa", value=f"**{nombre_final}**", inline=False)
            embed.add_field(name="👤 Usuario", value=nombre_usuario, inline=True)
            embed.add_field(name="🆔 Discord ID", value=f"<@{discord_id_web}>" if discord_id_web else "`No provisto`", inline=True)
            embed.add_field(name="📝 Problema", value=problema, inline=False)
            embed.set_footer(text="Blitz Hub System")

            if canal_staff:
                await canal_staff.send(embed=embed)

            # Crear canal privado
            if member:
                suffix = datetime.now().strftime("%H%M")
                nombre_canal = f"{nombre_final[:10].lower()}-{nombre_usuario[:10].lower()}-{suffix}".replace(" ", "-")
                cat_id = CAT_VIP if es_vip else CAT_ESTANDAR
                category = guild.get_channel(cat_id)

                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                    guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
                }
                rol_dev = guild.get_role(ID_ROL_DEV)
                if rol_dev: overwrites[rol_dev] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

                nuevo_canal = await guild.create_text_channel(name=nombre_canal, category=category, overwrites=overwrites)
                await nuevo_canal.send(content=f"Hola {member.mention}, atenderemos tu incidencia aquí.", embed=embed)

        bot.loop.create_task(process_discord())
        return {"status": "success"}, 200

    except Exception as e:
        print(f"Error en handle_ticket: {e}")
        return {"status": "error", "message": str(e)}, 500

# --- EL RESTO DEL CÓDIGO (run_web, bot, main) SE MANTIENE IGUAL ---
def run_web():
    port = int(os.getenv("PORT", 8080))
    config_hyper = Config()
    config_hyper.bind = [f"0.0.0.0:{port}"]
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(serve(app, config_hyper, shutdown_trigger=asyncio.Event().wait))
    except Exception as e: print(f"⚠️ Error Hypercorn: {e}")

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

async def load_extensions():
    if not os.path.exists("./cogs"): return
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and filename not in ["__init__.py", "webserver.py"]:
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"✅ Cog cargado: {filename}")
            except Exception as e: print(f"❌ Error cog {filename}: {e}")

@bot.event
async def on_ready():
    print(f"🤖 BOT ONLINE: {bot.user.name}")
    await load_extensions()

async def self_ping():
    await asyncio.sleep(30)
    url = "https://pollitos-discord.onrender.com/"
    while True:
        try: await asyncio.get_event_loop().run_in_executor(None, requests.get, url)
        except: pass
        await asyncio.sleep(600)

async def main():
    TOKEN = os.getenv("DISCORD_TOKEN")
    Thread(target=run_web, daemon=True).start()
    asyncio.create_task(self_ping())
    async with bot: await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
