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
            mapa = json.loads(gist_data['files']['mapa_discord.json']['content'])
            
            # 1. ¿Está este usuario en nuestra base de datos (vía web)?
            blitz_id = mapa.get(str(member.id))
            if not blitz_id:
                return # Si no ha rellenado la web, no le creamos nada aún

            # 2. Obtener info de la empresa
            db = json.loads(gist_data['files']['clientes.json']['content'])
            # Si el blitz_id es GUEST, usamos valores genéricos
            cliente_info = db.get(blitz_id, {"empresa": "GUEST", "plan": "Essential"})
            
            empresa = cliente_info.get('empresa', 'GUEST').upper()
            plan = cliente_info.get('plan', 'Essential')
            is_vip = plan in ["Full Hub", "Enterprise"]

            # 3. Nombre de canal ÚNICO (Privacidad Total)
            # Ejemplo: apple-pepe, apple-maria...
            nombre_canal = f"{empresa.lower()}-{member.name.lower()}".replace(" ", "-")

            # 4. Evitar duplicados (por si sale y vuelve a entrar)
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
            
            # Dar acceso al Dev (Tú)
            rol_dev = member.guild.get_role(self.ID_ROL_DEV)
            if rol_dev:
                overwrites[rol_dev] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

            # 6. Crear el canal
            channel = await member.guild.create_text_channel(
                name=nombre_canal,
                category=category,
                overwrites=overwrites,
                topic=f"Canal de soporte privado para {member.name} (Empresa: {empresa})"
            )

            # 7. Bienvenida automática
            embed = discord.Embed(
                title=f"⚡ Blitz Hub: Conexión Exitosa",
                description=f"Hola {member.mention}, se ha generado tu entorno de soporte privado.",
                color=discord.Color.gold() if is_vip else discord.Color.green()
            )
            embed.add_field(name="🏢 Empresa", value=empresa, inline=True)
            embed.add_field(name="📦 Plan", value=plan, inline=True)
            embed.set_footer(text="Privacidad garantizada: Solo tú y el equipo técnico veis este canal.")
            
            await channel.send(embed=embed)
            if is_vip and rol_dev:
                await channel.send(f"{rol_dev.mention} 🔔 **Nuevo empleado VIP conectado.**")

        except Exception as e:
            print(f"❌ Error en automatización: {e}")

@commands.command(name="cerrar", aliases=["close"])
    @commands.has_role(int(os.getenv('ID_ROL_DEV', 0)))
    async def cerrar_ticket(self, ctx, *, solucion: str = "No se ha especificado una descripción detallada."):
        """Archiva el ticket y envía la solución al usuario por DM"""
        
        ID_CAT_ARCHIVADOS = 1473689333964738633
        categoria_archivo = ctx.guild.get_channel(ID_CAT_ARCHIVADOS)

        # 1. Identificar al usuario del ticket antes de cambiar nada
        usuario_ticket = None
        for target, overwrite in ctx.channel.overwrites.items():
            if isinstance(target, discord.Member) and not target.bot:
                usuario_ticket = target
                break

        if not usuario_ticket:
            return await ctx.send("❌ No he podido identificar al usuario propietario de este ticket.")

        # 2. Intentar enviar el DM con el Fix
        embed_dm = discord.Embed(
            title="✅ Ticket Finalizado - Blitz Hub",
            description=f"Tu incidencia en el canal **{ctx.channel.name}** ha sido marcada como resuelta.",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed_dm.add_field(name="🛠️ Solución Aplicada", value=solucion)
        embed_dm.set_footer(text="Si necesitas más ayuda, puedes abrir un nuevo ticket desde nuestra web.")

        try:
            await usuario_ticket.send(embed=embed_dm)
            dm_status = "✅ Solución enviada por DM."
        except discord.Forbidden:
            dm_status = "⚠️ No pude enviar DM (el usuario tiene los mensajes cerrados)."

        # 3. Archivar el canal
        new_overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            ctx.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        
        rol_dev = ctx.guild.get_role(self.ID_ROL_DEV)
        if rol_dev:
            new_overwrites[rol_dev] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        # Movemos y renombramos
        fecha_cierre = discord.utils.utcnow().strftime("%d-%m")
        await ctx.channel.edit(
            name=f"fixed-{ctx.channel.name}-{fecha_cierre}",
            category=categoria_archivo,
            overwrites=new_overwrites
        )

        # 4. Confirmación en el canal (para tu registro)
        await ctx.send(f"🔒 **Ticket Archivado.**\n{dm_status}")

async def setup(bot):
    await bot.add_cog(CustomerService(bot))
