import discord
from discord.ext import commands
import os
import json
import requests

class CustomerService(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # IDs que sacaste de tu servidor
        self.CAT_VIP = 1473688902442287105
        self.CAT_ESTANDAR = 1473689289434075197
        self.ID_ROL_DEV = 1473366087390331094

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Blindaje automático: Crea el canal cuando el cliente entra al server"""
        
        gist_id = os.getenv('GIST_ID')
        github_token = os.getenv('GITHUB_TOKEN')
        
        # 1. Buscamos en el Gist de Seguridad (El mapa DiscordID -> BlitzID)
        # NOTA: Asegúrate de tener un archivo llamado 'mapa_discord.json' en tu Gist
        blitz_id = None
        try:
            headers = {"Authorization": f"token {github_token}"}
            r = requests.get(f"https://api.github.com/gists/{gist_id}", headers=headers)
            if r.status_code == 200:
                gist_data = r.json()
                
                # Buscamos al usuario en el mapa de Discord
                # Si aún no tienes este archivo, el bot ignorará la entrada (seguridad)
                if 'mapa_discord.json' in gist_data['files']:
                    mapa = json.loads(gist_data['files']['mapa_discord.json']['content'])
                    blitz_id = mapa.get(str(member.id))

                if not blitz_id: return # No es un cliente pre-registrado

                # 2. Si es cliente, sacamos sus datos del archivo 'clientes.json' (el que ya usas en la API)
                db = json.loads(gist_data['files']['clientes.json']['content'])
                cliente_info = db.get(blitz_id)
                
                if not cliente_info: return

                # 3. Preparar creación de canal
                plan = cliente_info.get('plan', 'Essential')
                empresa = cliente_info.get('empresa', 'Empresa').upper()
                
                # Elegir categoría
                cat_id = self.CAT_VIP if plan in ["Full Hub", "Enterprise"] else self.CAT_ESTANDAR
                category = member.guild.get_channel(cat_id)
                
                # Permisos de Blindaje
                overwrites = {
                    member.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                    member.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
                }
                
                # Añadir tu rol de DEV
                rol_dev = member.guild.get_role(self.ID_ROL_DEV)
                if rol_dev:
                    overwrites[rol_dev] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

                # 4. Crear Canal
                nombre_canal = f"{blitz_id}-{empresa}".lower().replace(" ", "-")
                channel = await member.guild.create_text_channel(
                    name=nombre_canal,
                    category=category,
                    overwrites=overwrites
                )

                # 5. Bienvenida profesional
                color = discord.Color.gold() if plan != "Essential" else discord.Color.blue()
                embed = discord.Embed(
                    title=f"Ecosistema Blitz Hub: {empresa}",
                    description=f"Hola {member.mention}, se ha desplegado tu canal de soporte **{plan}**.",
                    color=color
                )
                await channel.send(embed=embed)
                if plan != "Essential":
                    await channel.send(f"<@&{self.ID_ROL_DEV}> 🚨 Cliente VIP activo.")

        except Exception as e:
            print(f"❌ Error en CustomerService: {e}")

async def setup(bot):
    await bot.add_cog(CustomerService(bot))
