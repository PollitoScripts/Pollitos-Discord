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
        """Detecta al nuevo miembro y le crea SU canal privado automáticamente"""
        gist_id = os.getenv('GIST_ID')
        github_token = os.getenv('GITHUB_TOKEN')
        
        try:
            headers = {"Authorization": f"token {github_token}"}
            r = requests.get(f"https://api.github.com/gists/{gist_id}", headers=headers)
            if r.status_code != 200: return

            gist_data = r.json()
            # Cargar el mapa de Discord
            mapa = json.loads(gist_data['files']['mapa_discord.json']['content'])
            
            # 1. ¿Está este usuario en nuestra base de datos (vía web)?
            blitz_id = mapa.get(str(member.id))
            if not blitz_id:
                return 

            # 2. Obtener info de la empresa
            db = json.loads(gist_data['files']['clientes.json']['content'])
            cliente_info = db.get(blitz_id, {"empresa": "GUEST", "plan": "Essential"})
            
            empresa = cliente_info.get('empresa', 'GUEST').upper()
            plan = cliente_info.get('plan', 'Essential')
            is_vip = plan in ["Full Hub", "Enterprise"]

            # 3. Nombre de canal ÚNICO
            nombre_canal = f"{empresa.lower()}-{member.name.lower()}".replace(" ", "-")

            # 4. Evitar duplicados
            existente = discord.utils.get(member.guild.text_channels, name=nombre_canal)
            if existente: return

            # 5. Definir Categoría y Permisos
            cat_id = self.CAT_VIP_ID if is_vip else self.CAT_ESTANDAR_ID
            category = member.guild.get_channel(cat_id)
            
            overwrites = {
                member.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                member.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }
            
            rol_dev = member.guild.get_role(self.ID_ROL_DEV)
            if rol_dev:
                overwrites[rol_dev] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

            # 6. Crear el canal
            channel = await member.guild.create_text_channel(
                name=nombre_canal,
                category=category,
                overwrites=overwrites,
                topic=f"Soporte privado: {member.name} ({empresa})"
            )

            # 7. Bienvenida
            embed = discord.Embed(
                title=f"⚡ Blitz Hub: Conexión Exitosa",
                description=f"Hola {member.mention}, se ha generado tu entorno de soporte privado.",
                color=discord.Color.gold() if is_vip else discord.Color.green()
            )
            embed.add_field(name="🏢 Empresa", value=empresa, inline=True)
            embed.add_field(name="📦 Plan", value=plan, inline=True)
            
            await channel.send(embed=embed)
            if is_vip and rol_dev:
                await channel.send(f"{rol_dev.mention} 🔔 **Nuevo empleado VIP conectado.**")

        except Exception as e:
            print(f"❌ Error en automatización entrada: {e}")

    @commands.command(name="cerrar", aliases=["close"])
    async def cerrar_ticket(self, ctx, *, solucion: str = "No se ha especificado una descripción detallada."):
        """Archiva el ticket y envía la solución al usuario por DM"""
        
        # Verificar rol de desarrollador
        rol_dev = ctx.guild.get_role(self.ID_ROL_DEV)
        if rol_dev not in ctx.author.roles:
            return await ctx.send("❌ No tienes permiso para cerrar tickets.")

        ID_CAT_ARCHIVADOS = 1473689333964738633
        categoria_archivo = ctx.guild.get_channel(ID_CAT_ARCHIVADOS)

        if not categoria_archivo:
            return await ctx.send("❌ Error: No se encuentra la categoría de archivos.")

        # 1. Identificar al usuario del ticket
        usuario_ticket = None
        for target, overwrite in ctx.channel.overwrites.items():
            if isinstance(target, discord.Member) and not target.bot:
                # Evitar que el propio autor (el admin) sea el detectado como usuario del ticket
                if target.id != ctx.author.id or len(ctx.channel.overwrites) <= 3:
                     usuario_ticket = target
                     if target.id != ctx.author.id: break

        if not usuario_ticket:
            return await ctx.send("❌ No he podido identificar al usuario propietario de este ticket.")

        # 2. Enviar DM con la solución
        embed_dm = discord.Embed(
            title="✅ Ticket Finalizado - Blitz Hub",
            description=f"Tu incidencia en el canal **{ctx.channel.name}** ha sido resuelta.",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed_dm.add_field(name="🛠️ Solución Aplicada", value=solucion)
        embed_dm.set_footer(text="Blitz Hub Support System")

        try:
            await usuario_ticket.send(embed=embed_dm)
            dm_status = "✅ Solución enviada por DM."
        except:
            dm_status = "⚠️ No pude enviar DM (Usuario con DMs cerrados)."

        # 3. Archivar canal
        new_overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            ctx.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        if rol_dev:
            new_overwrites[rol_dev] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        fecha_cierre = discord.utils.utcnow().strftime("%d-%m")
        nuevo_nombre = f"fixed-{ctx.channel.name}-{fecha_cierre}"
        
        await ctx.channel.edit(
            name=nuevo_nombre[:100], # Discord limita a 100 caracteres
            category=categoria_archivo,
            overwrites=new_overwrites
        )
        
        await ctx.send(f"🔒 **Ticket Archivado.**\n{dm_status}")

async def setup(bot):
    await bot.add_cog(CustomerService(bot))
