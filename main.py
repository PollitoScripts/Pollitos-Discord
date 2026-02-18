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
        # Si no pone empresa, por defecto es PARTICULAR
        nombre_empresa = data.get('empresa', '').strip().upper() or "PARTICULAR"
        
        es_vip = False
        gist_id = os.getenv('GIST_ID')
        github_token = os.getenv('GITHUB_TOKEN')
        
        # 2. Validación Real contra Gist
        if gist_id and github_token and cliente_id_raw and cliente_id_raw != "GUEST":
            try:
                headers = {"Authorization": f"token {github_token}"}
                response_gist = requests.get(f"https://api.github.com/gists/{gist_id}", headers=headers)
                if response_gist.status_code == 200:
                    gist_data = response_gist.json()
                    for file in gist_data['files'].values():
                        if cliente_id_raw in file['content'].upper():
                            es_vip = True
                            break
            except Exception as ge:
                print(f"⚠️ Error Gist: {ge}")

        # 3. Selección de canal según el resultado de la validación
        id_canal_guest = os.getenv('ID_CANAL_SOPORTE')
        id_canal_vip = os.getenv('ID_CANAL_VIP')
        canal_id_final = int(id_canal_vip) if es_vip and id_canal_vip else int(id_canal_guest)
        canal = bot.get_channel(canal_id_final)
        
        if not canal:
            canal = await bot.fetch_channel(canal_id_final)

        # 4. Estética DINÁMICA
        # Si es VIP: Dorado y Corona. Si no: Azul y nombre de empresa normal.
        color_final = discord.Color.gold() if es_vip else discord.Color.blue()
        
        if es_vip:
            titulo_final = f"👑 VIP: {nombre_empresa}"
            status_footer = "EMPRESA VERIFICADA ✅"
        else:
            # Aquí está el cambio: mantiene el nombre de empresa pero avisa que NO es verificado
            titulo_final = f"👤 CONSULTA: {nombre_empresa}"
            status_footer = "ID NO VÁLIDO / GUEST ⚠️"

        embed = discord.Embed(title=titulo_final, color=color_final, timestamp=discord.utils.utcnow())
        
        if es_vip:
            embed.set_author(name="SOPORTE PREMIUM BLITZ", icon_url="https://cdn-icons-png.flaticon.com/512/2533/2533049.png")

        embed.add_field(name="🏢 Empresa/Origen", value=f"**{nombre_empresa}**", inline=False)
        embed.add_field(name="👤 Empleado", value=nombre_usuario, inline=True)
        embed.add_field(name="🔑 ID Contrato", value=f"`{cliente_id_raw if cliente_id_raw else 'GUEST'}`", inline=True)
        embed.add_field(name="📝 Problema", value=data.get('problema', 'Sin descripción'), inline=False)
        embed.set_footer(text=f"Blitz Hub System • {status_footer}")

        async def send_msg():
            await bot.wait_until_ready()
            content = f"👑 **¡ALERTA VIP!** {nombre_empresa}" if es_vip else None
            await canal.send(content=content, embed=embed)

        bot.loop.create_task(send_msg())
        return {"status": "success", "message": "Ticket enviado"}, 200

    except Exception as e:
        print(f"⚠️ Error: {e}")
        return {"status": "error", "message": str(e)}, 500

# ----------------------------
# Función de Servicios de Streaming (Recuperada)
# ----------------------------
async def services():
    # Usamos la ID del canal desde tu config
    channel = bot.get_channel(config.channel_id)
    
    if channel is None:
        print(f'⚠️ No se encontró el canal {config.channel_id}, reintentando...')
        await asyncio.sleep(5)
        channel = bot.get_channel(config.channel_id)

    if channel is None: return

    try:
        await channel.purge() # Limpia el canal

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
                    plan_details += f"**Precio**: {plan['price_per_month']}\n"
                if plan.get('resolution') and plan['resolution'] != 'N/A':
                    plan_details += f"**Resolución**: {plan['resolution']}\n"
                if plan.get('ads') and plan['ads'] != "No Ads":
                    plan_details += f"**Anuncios**: {plan['ads']}\n"

                embed.add_field(name=plan["name"], value=plan_details, inline=True)

            message = await channel.send(embed=embed)
            await message.add_reaction('✅')
        print('✅ Servicios de streaming actualizados en el canal.')
    except Exception as e:
        print(f'❌ Error en services: {e}')

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
    # API en hilo separado
    Thread(target=run_web, daemon=True).start()
    # Autoping
    asyncio.create_task(self_ping())
    # Arrancar Bot
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
