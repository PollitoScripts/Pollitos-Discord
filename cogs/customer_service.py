import discord
from discord.ext import commands
import os
import json
import requests

class CustomerService(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.CAT_VIP_ID = int(os.getenv('CAT_VIP_ID', 0))
        self.CAT_ESTANDAR_ID = int(os.getenv('CAT_ESTANDAR_ID', 0))
        self.ID_ROL_DEV = int(os.getenv('ID_ROL_DEV', 0))

    @commands.Cog.listener()
    async def on_member_join(self, member):
        gist_id = os.getenv('GIST_ID')
        github_token = os.getenv('GITHUB_TOKEN')
        
        try:
            headers = {"Authorization": f"token {github_token}"}
            r = requests.get(f"https://api.github.com/gists/{gist_id}", headers=headers)
            
            if r.status_code == 200:
                gist_data = r.json()
                
                # 1. Buscamos en el mapa
                if 'mapa_discord.json' not in gist_data['files']: return
                mapa = json.loads(gist_data['files']['mapa_discord.json']['content'])
                blitz_id = mapa.get(str(member.id))

                if not blitz_id: return # Si no rellenó el formulario nunca, no hacemos nada

                # 2. Obtener info del cliente (si existe)
                db = json.loads(gist_data['files']['clientes.json']['content'])
                cliente_info = db.get(blitz_id, {})
                
                # Si es GUEST, le asignamos valores por defecto
                if blitz_id == "GUEST":
                    plan = "Essential"
                    empresa = "GUEST-USER"
                else:
                    plan = cliente_info.get('plan', 'Essential')
                    empresa = cliente_info.get('empresa', 'Empresa').upper()
                
                # 3. Elección de Categoría
                cat_id = self.CAT_VIP_ID if plan in ["Full Hub", "Enterprise"] else self.CAT_ESTANDAR_ID
                category = member.guild.get_channel(cat_id)
                
                if not category: return

                # 4. Permisos
                overwrites = {
                    member.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                    member.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
                }
                
                rol_dev = member.guild.get_role(self.ID_ROL_DEV)
                if rol_dev:
                    overwrites[rol_dev] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

                # 5. Crear Canal (Nombre: guest-nombre o id-empresa)
                nombre_limpio = empresa.lower().replace(" ", "-")
                nombre_canal = f"{blitz_id}-{nombre_limpio}"
                
                channel = await member.guild.create_text_channel(
                    name=nombre_canal,
                    category=category,
                    overwrites=overwrites
                )

                # 6. Bienvenida diferenciada
                is_vip = plan in ["Full Hub", "Enterprise"]
                color = discord.Color.gold() if is_vip else discord.Color.blue()
                
                embed = discord.Embed(
                    title=f"Ecosistema Blitz Hub: {empresa}",
                    description=f"Hola {member.mention}, este es tu canal privado de soporte.",
                    color=color
                )
                
                if is_vip:
                    embed.add_field(name="🚀 Nivel de Servicio", value="SLA Prioritario (< 4h)")
                    await channel.send(embed=embed)
                    if rol_dev:
                        await channel.send(f"{rol_dev.mention} 🚨 Cliente VIP activo.")
                else:
                    embed.add_field(name="🛡️ Nivel de Servicio", value="Soporte Estándar (Sin SLA)")
                    await channel.send(embed=embed)

        except Exception as e:
            print(f"❌ Error en CustomerService: {e}")

async def setup(bot):
    await bot.add_cog(CustomerService(bot))
