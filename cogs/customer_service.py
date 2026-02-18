import discord
from discord.ext import commands
import os
import json
import requests
import asyncio

class CustomerService(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gist_id = os.getenv('GIST_ID')
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.id_rol_dev = int(os.getenv('ID_ROL_DEV', 0))

    # --- COMANDO DE ALTA (REVISADO Y COMPLETO) ---
  @commands.has_role(int(os.getenv('ID_ROL_DEV', 0)))
    @commands.command(name="alta")
    async def alta(self, ctx, empresa: str, miembro: discord.Member):
        """Genera ID, vincula Discord y añade 30 días de suscripción."""
        headers = {"Authorization": f"token {self.github_token}"}
        
        # 1. GENERAR CÓDIGO BLITZ-XXXX-XXXX
        def generar_codigo():
            chars = string.ascii_uppercase + string.digits
            return f"BLITZ-{''.join(secrets.choice(chars) for _ in range(4))}-{''.join(secrets.choice(chars) for _ in range(4))}"

        id_soporte = generar_codigo()
        
        # 2. CALCULAR FECHAS
        fecha_inicio = datetime.now()
        fecha_fin = fecha_inicio + timedelta(days=30) # Aquí puedes cambiar los días
        formato_fecha = "%d/%m/%Y"

        await ctx.send(f"🛡️ Blindando acceso para **{empresa}**...")

        try:
            # 3. Obtener datos actuales del Gist
            r = requests.get(f"https://api.github.com/gists/{self.gist_id}", headers=headers)
            gist_data = r.json()

            # 4. Actualizar clientes.json con FECHA DE EXPIRACIÓN
            clientes = json.loads(gist_data['files']['clientes.json']['content'])
            while id_soporte in clientes: id_soporte = generar_codigo()
            
            clientes[id_soporte] = {
                "empresa": empresa,
                "plan": "Full Hub",
                "fecha_alta": fecha_inicio.strftime(formato_fecha),
                "fecha_expiracion": fecha_fin.strftime(formato_fecha),
                "estado": "activo"
            }
            
            # 5. Actualizar mapa_discord.json
            mapa_content = gist_data['files'].get('mapa_discord.json', {'content': '{}'})['content']
            mapa = json.loads(mapa_content)
            mapa[str(miembro.id)] = id_soporte

            # 6. Subir a GitHub
            payload = {
                "files": {
                    "clientes.json": {"content": json.dumps(clientes, indent=4)},
                    "mapa_discord.json": {"content": json.dumps(mapa, indent=4)}
                }
            }
            requests.patch(f"https://api.github.com/gists/{self.gist_id}", headers=headers, json=payload)

            # 7. Embed de éxito detallado
            embed = discord.Embed(title="🚀 Activación de Cliente", color=discord.Color.gold())
            embed.add_field(name="🏢 Empresa", value=empresa, inline=False)
            embed.add_field(name="🔑 ID Soporte", value=f"`{id_soporte}`", inline=False)
            embed.add_field(name="👤 Usuario", value=miembro.mention, inline=True)
            embed.add_field(name="📅 Vence el", value=fecha_fin.strftime(formato_fecha), inline=True)
            embed.set_footer(text="Blitz Hub • Sistema de Gestión de Licencias")
            
            await ctx.send(embed=embed)
            
            # Mensaje privado al cliente
            msg = (f"🎊 **¡Bienvenido a Blitz Hub!**\n\n"
                   f"Tu acceso ha sido activado para: **{empresa}**\n"
                   f"Tu ID único es: `{id_soporte}`\n"
                   f"Suscripción válida hasta el: **{fecha_fin.strftime(formato_fecha)}**")
            try:
                await miembro.send(msg)
            except:
                await ctx.send("⚠️ No pude enviar DM (DMs cerrados).")

        except Exception as e:
            await ctx.send(f"❌ Error en el proceso: {e}")

    # --- COMANDO CERRAR (CON IDENTIFICACIÓN MEJORADA) ---
    @commands.command(name="cerrar", aliases=["close"])
    async def cerrar_ticket(self, ctx):
        """Cierra el ticket y envía un mensaje al usuario identificado."""
        
        # 1. Intentar identificar al usuario propietario
        usuario_ticket = None
        
        # A. Por permisos del canal
        for target, overwrite in ctx.channel.overwrites.items():
            if isinstance(target, discord.Member) and not target.bot:
                if target.id != ctx.author.id or len(ctx.channel.overwrites) <= 3: 
                    usuario_ticket = target
                    break
        
        # B. Por nombre del canal (backup)
        if not usuario_ticket:
            parts = ctx.channel.name.split('-')
            if len(parts) >= 2:
                usuario_ticket = discord.utils.get(ctx.guild.members, name=parts[1])

        if not usuario_ticket:
            return await ctx.send("❌ No he podido identificar al dueño del ticket para avisarle.")

        # 2. Notificar al usuario
        embed_dm = discord.Embed(
            title="🎫 Ticket Finalizado",
            description=f"Tu consulta en **{ctx.guild.name}** ha sido marcada como resuelta.",
            color=discord.Color.green()
        )
        try:
            await usuario_ticket.send(embed=embed_dm)
        except:
            pass

        # 3. Mover a categoría de archivos y renombrar
        cat_archivados = discord.utils.get(ctx.guild.categories, name="ARCHIVADOS")
        await ctx.channel.edit(name=f"fixed-{ctx.channel.name}", category=cat_archivados)
        await ctx.send("✅ Ticket cerrado y archivado.")

async def setup(bot):
    await bot.add_cog(CustomerService(bot))
