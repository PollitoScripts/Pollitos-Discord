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

        # Lógica de Gist para verificar VIP
        if gist_id and github_token:
            try:
                headers = {"Authorization": f"token {github_token}"}
                r = requests.get(f"https://api.github.com/gists/{gist_id}", headers=headers)
                if r.status_code == 200:
                    db = json.loads(r.json()['files']['clientes.json']['content'])
                    if cliente_id_raw in db:
                        es_vip = True
                        nombre_final = db[cliente_id_raw].get('empresa', nombre_final)
            except: pass

       async def process_discord():
            await bot.wait_until_ready()
            
            # 1. Selección del servidor por ID
            guild = bot.get_guild(ID_SERVIDOR_BLITZ)
            if not guild:
                print(f"❌ Error: No se encontró el servidor con ID {ID_SERVIDOR_BLITZ}")
                return

            member = guild.get_member(int(discord_id_web)) if discord_id_web.isdigit() else None
            
            # 2. Preparar IDs de canales de registro (Staff)
            id_canal_staff = int(os.getenv('ID_CANAL_VIP' if es_vip else 'ID_CANAL_SOPORTE'))
            canal_staff = bot.get_channel(id_canal_staff)

            # 3. Preparar el Embed de Registro
            color_embed = discord.Color.gold() if es_vip else discord.Color.blue()
            embed = discord.Embed(title=f"🎫 Ticket: {nombre_final}", color=color_embed, timestamp=discord.utils.utcnow())
            if es_vip:
                embed.set_author(name="SOPORTE PREMIUM BLITZ", icon_url="https://cdn-icons-png.flaticon.com/512/2533/2533049.png")
            
            embed.add_field(name="🏢 Empresa", value=f"**{nombre_final}**", inline=False)
            embed.add_field(name="👤 Usuario", value=nombre_usuario, inline=True)
            embed.add_field(name="🆔 Discord ID", value=f"<@{discord_id_web}>" if discord_id_web else "`No provisto`", inline=True)
            embed.add_field(name="🔑 ID Soporte", value=f"`{cliente_id_raw or 'GUEST'}`", inline=True)
            embed.add_field(name="📝 Problema", value=problema, inline=False)
            embed.set_footer(text=f"Blitz Hub System • {'EMPRESA VERIFICADA ✅' if es_vip else 'GUEST ⚠️'}")

            # --- ACCIÓN A: ENVIAR SIEMPRE AL CANAL DE REGISTRO (Staff) ---
            if canal_staff:
                alerta = f"👑 **¡ALERTA VIP!** {nombre_final}" if es_vip else None
                await canal_staff.send(content=alerta, embed=embed)

            # --- ACCIÓN B: CREAR CANAL PRIVADO SI EL USUARIO ESTÁ EN EL SERVER ---
            if member:
                from datetime import datetime
                suffix = datetime.now().strftime("%H%M")
                nombre_canal_privado = f"{nombre_final[:10].lower()}-{nombre_usuario[:10].lower()}-{suffix}".replace(" ", "-")
                
                cat_id_activa = int(os.getenv('CAT_VIP_ID')) if es_vip else int(os.getenv('CAT_ESTANDAR_ID'))
                category = guild.get_channel(cat_id_activa)

                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                    guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
                }
                rol_dev = guild.get_role(ID_ROL_DEV)
                if rol_dev: 
                    overwrites[rol_dev] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

                # Crear el canal en la categoría correspondiente
                nuevo_canal = await guild.create_text_channel(name=nombre_canal_privado, category=category, overwrites=overwrites)
                
                # Mensaje de bienvenida en el nuevo canal privado
                await nuevo_canal.send(content=f"Hola {member.mention}, hemos recibido tu incidencia. Un desarrollador te atenderá aquí mismo.", embed=embed)
                if es_vip and rol_dev:
                    await nuevo_canal.send(f"{rol_dev.mention} 🚨 **ATENCIÓN: Ticket VIP iniciado.**")
            else:
                # Si no está en el servidor, ya enviamos el log arriba, pero podemos dejar un aviso extra
                print(f"ℹ️ El usuario {nombre_usuario} no está en el servidor, solo se envió log a staff.")

        bot.loop.create_task(process_discord())
        return {"status": "success"}, 200

    except Exception as e:
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
    # Nota: Asegúrate de tener la función services() definida o importada si usas este comando
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
