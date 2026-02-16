import discord
from discord.ext import commands
from discord.ui import Select, View
import config
import os
import json

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())


####    Inicio del Bot      ####

async def load_extensions():
    # Imprime un mensaje indicando que se están cargando las extensiones
    print("Cargando extensiones")
    # Itera sobre los archivos en el directorio "cogs"
    for filename in os.listdir("./cogs"):
        try:
            if filename.endswith(".py") and filename != "__init__.py":
                await bot.load_extension(f"cogs.{filename[:-3]}")
        except Exception as e:
            print(f"No se pudo cargar la extensión '{filename[:-3]}': {e}")
    # Indica que todas las extensiones se han cargado correctamente
    print("Extensiones cargadas.")
    

async def services():
        channel = bot.get_channel(config.channel_id)
        
        if channel is None:
            print(f'No se encontró el canal con ID {config.channel_id}.')
            return
        
        print(f'Enviando mensajes al canal {channel.name}.')

        try:
            # Eliminamos los mensajes antiguos del canal
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
                    if plan["price_per_month"]!=0:
                        plan_details = f"**Precio**: ${plan.get('price_per_month')}\n"
                    else:
                        plan_details =""
                    if plan['resolution']!='N/A':
                        plan_details += f"**Resolución**: {plan['resolution']}\n"
                    if "ads" in plan:
                        if plan['ads']!="No Ads":
                            plan_details += f"**Anuncios**: {plan['ads']}\n"
                    embed.add_field(name=plan["name"], value=plan_details, inline=True)

                message = await channel.send(embed=embed)
                await message.add_reaction('✅')

            print('Mensajes enviados correctamente.')

        except Exception as e:
            print(f'Error al enviar mensajes: {e}')

@bot.event
async def on_ready():
    # Imprime en la consola el nombre del bot una vez que está conectado
    print(f'Bot conectado como {bot.user.name}')
    await load_extensions()  # Carga todas las extensiones al iniciar el bot
    
@bot.command()
async def servicios(ctx):
    await services()
    await ctx.send("Servicios enviados.")




#### Token ####

# Ejecuta el bot con el token proporcionado en el archivo de configuración
bot.run(config.TOKEN)
