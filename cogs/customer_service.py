import discord
from discord.ext import commands
import os
import json
import requests

class CustomerService(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Leemos los IDs desde las variables de entorno de Render
        # El segundo valor es un "fallback" por si olvidas configurarlo (opcional)
        self.CAT_VIP_ID = int(os.getenv('CAT_VIP_ID', 0))
        self.CAT_ESTANDAR_ID = int(os.getenv('CAT_ESTANDAR_ID', 0))
        self.ID_ROL_DEV = int(os.getenv('ID_ROL_DEV', 0))

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Blindaje automático: Crea el canal cuando el cliente entra al server"""
        
        gist_id = os.getenv('GIST_ID')
        github_token = os.getenv('GITHUB_TOKEN')
        
        try:
            headers = {"Authorization": f"token {github_token}"}
            r = requests.get(f"https://api.github.com/gists/{gist_id}", headers=headers)
            
            if r.status_code == 200:
                gist_data = r.json()
                blitz_id = None
                
                # 1. Mapa de Discord
                if 'mapa_discord.json' in gist_data['files']:
                    mapa = json.loads(gist_data['files']['mapa_discord.json']['content'])
                    blitz_id = mapa.get(str(member.id))

                if not blitz_id: return 

                # 2. Datos del cliente
                db = json.loads(gist_data['files']['clientes.json']['content'])
                cliente_info = db.get(blitz_id)
                
                if not cliente_info: return

                # 3. Lógica de Plan y Categoría
                plan = cliente_info.get('plan', 'Essential')
                empresa = cliente_info.get('empresa', 'Empresa').upper()
                
                # Usamos la ID que viene de Render
                cat_id = self.CAT_VIP_ID if plan in ["Full Hub", "Enterprise"] else self.CAT_ESTANDAR_ID
                category = member.guild.get_channel(cat_id)
                
                if not category:
                    print(f"⚠️ Error: No se encontró la categoría con ID {cat_id}")
                    return

                # 4. Permisos de Blindaje
                overwrites = {
                    member.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                    member.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
                }
                
                rol_dev = member.guild.get_role(self.ID_ROL_DEV)
                if rol_dev:
                    overwrites[rol_dev] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

                # 5. Crear Canal
                nombre_canal = f"{blitz_id}-{empresa}".lower().replace(" ", "-")
                channel = await member.guild.create_text_channel(
                    name=nombre_canal,
                    category=category,
                    overwrites=overwrites
                )

                # 6. Bienvenida
                color = discord.Color.gold() if plan != "Essential" else discord.Color.blue()
                embed = discord.Embed(
                    title=f"Ecosistema Blitz Hub: {empresa}",
                    description=f"Hola {member.mention}, se ha desplegado tu canal de soporte **{plan}**.",
                    color=color
                )
                await channel.send(embed=embed)
                
                if plan != "Essential" and rol_dev:
                    await channel.send(f"{rol_dev.mention} 🚨 Cliente VIP activo.")

        except Exception as e:
            print(f"❌ Error en CustomerService: {e}")

async def setup(bot):
    await bot.add_cog(CustomerService(bot))
