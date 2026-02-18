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
        """Crea un canal PRIVADO único para este empleado específico"""
        gist_id = os.getenv('GIST_ID')
        github_token = os.getenv('GITHUB_TOKEN')
        
        try:
            headers = {"Authorization": f"token {github_token}"}
            r = requests.get(f"https://api.github.com/gists/{gist_id}", headers=headers)
            if r.status_code != 200: return

            gist_data = r.json()
            mapa = json.loads(gist_data['files']['mapa_discord.json']['content'])
            
            # Buscamos el ID de empresa asociado a este Discord ID
            blitz_id = mapa.get(str(member.id))
            if not blitz_id: return 

            db = json.loads(gist_data['files']['clientes.json']['content'])
            cliente_info = db.get(blitz_id, {})
            
            plan = cliente_info.get('plan', 'Essential')
            empresa = cliente_info.get('empresa', 'Empresa').upper()
            is_vip = plan in ["Full Hub", "Enterprise"]
            
            # Nombre del canal: [Empresa]-[NombreUsuario]
            # Esto garantiza que sea único para cada persona aunque sean de la misma empresa
            nombre_usuario_limpio = member.name.lower().replace(" ", "-")
            empresa_limpia = empresa.lower().replace(" ", "-")
            nombre_canal = f"{empresa_limpia}-{nombre_usuario_limpio}"
            
            # Elección de Categoría
            cat_id = self.CAT_VIP_ID if is_vip else self.CAT_ESTANDAR_ID
            category = member.guild.get_channel(cat_id)
            if not category: return

            # Permisos: Solo el empleado, el bot y tú (Dev)
            overwrites = {
                member.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                member.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }
            
            rol_dev = member.guild.get_role(self.ID_ROL_DEV)
            if rol_dev: 
                overwrites[rol_dev] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

            # Creamos el canal individual
            channel = await member.guild.create_text_channel(
                name=nombre_canal, 
                category=category, 
                overwrites=overwrites
            )
            
            embed = discord.Embed(
                title=f"Soporte Individual: {empresa}",
                description=f"Hola {member.mention}, este es tu canal privado de soporte Blitz.",
                color=discord.Color.gold() if is_vip else discord.Color.blue()
            )
            embed.add_field(name="🏢 Organización", value=empresa, inline=True)
            embed.add_field(name="👤 Usuario", value=member.name, inline=True)
            embed.add_field(name="🚀 Nivel SLA", value="Prioritario (< 4h)" if is_vip else "Estándar", inline=False)
            
            await channel.send(embed=embed)
            if is_vip and rol_dev: 
                await channel.send(f"{rol_dev.mention} 🚨 Nueva incidencia de empleado VIP.")

        except Exception as e:
            print(f"❌ Error en on_member_join individual: {e}")

    @commands.command(name="vincular")
    @commands.has_role(int(os.getenv('ID_ROL_DEV', 0)))
    async def vincular(self, ctx, member: discord.Member, blitz_id: str):
        """Asocia un ID de Discord a un Blitz ID de Empresa en el Gist"""
        gist_id = os.getenv('GIST_ID')
        github_token = os.getenv('GITHUB_TOKEN')
        headers = {"Authorization": f"token {github_token}"}
        
        try:
            r = requests.get(f"https://api.github.com/gists/{gist_id}", headers=headers)
            gist_data = r.json()
            
            mapa = json.loads(gist_data['files']['mapa_discord.json']['content'])
            mapa[str(member.id)] = blitz_id.upper()
            
            updated_files = {"mapa_discord.json": {"content": json.dumps(mapa, indent=2)}}
            requests.patch(f"https://api.github.com/gists/{gist_id}", headers=headers, json={"files": updated_files})
            
            await ctx.send(f"✅ Vinculación completada.\n👤 Usuario: {member.mention}\n🏢 ID Empresa: `{blitz_id.upper()}`\n\n*La próxima vez que entre al servidor, se le creará su canal privado.*")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

async def setup(bot):
    await bot.add_cog(CustomerService(bot))
