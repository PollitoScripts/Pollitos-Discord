import discord
from discord.ext import commands
import os
import json
import requests
import asyncio
import secrets
import string
from datetime import datetime, timedelta

class CustomerService(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gist_id = os.getenv('GIST_ID')
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.id_rol_dev = int(os.getenv('ID_ROL_DEV', 0))
        self.id_cat_archivados = int(os.getenv('ID_CAT_ARCHIVADOS', 0))
        print("🛠️ Cog CustomerService cargado correctamente")

    # --- COMANDO DE ALTA ---
    @commands.has_role(int(os.getenv('ID_ROL_DEV', 0)))
    @commands.command(name="alta")
    async def alta(self, ctx, empresa: str, miembro: discord.Member):
        """Genera ID, vincula Discord y añade 30 días de suscripción."""
        headers = {"Authorization": f"token {self.github_token}"}
        
        def generar_codigo():
            chars = string.ascii_uppercase + string.digits
            p1 = ''.join(secrets.choice(chars) for _ in range(4))
            p2 = ''.join(secrets.choice(chars) for _ in range(4))
            return f"BLITZ-{p1}-{p2}"

        id_soporte = generar_codigo()
        fecha_inicio = datetime.now()
        fecha_fin = fecha_inicio + timedelta(days=30)
        formato_fecha = "%d/%m/%Y"

        await ctx.send(f"🛡️ Blindando acceso para **{empresa}**...")

        try:
            r = requests.get(f"https://api.github.com/gists/{self.gist_id}", headers=headers)
            gist_data = r.json()

            clientes = json.loads(gist_data['files']['clientes.json']['content'])
            while id_soporte in clientes: 
                id_soporte = generar_codigo()
            
            clientes[id_soporte] = {
                "empresa": empresa,
                "plan": "Full Hub",
                "fecha_alta": fecha_inicio.strftime(formato_fecha),
                "fecha_expiracion": fecha_fin.strftime(formato_fecha),
                "estado": "activo"
            }
            
            mapa_content = gist_data['files'].get('mapa_discord.json', {'content': '{}'})['content']
            mapa = json.loads(mapa_content)
            mapa[str(miembro.id)] = id_soporte

            payload = {
                "files": {
                    "clientes.json": {"content": json.dumps(clientes, indent=4)},
                    "mapa_discord.json": {"content": json.dumps(mapa, indent=4)}
                }
            }
            requests.patch(f"https://api.github.com/gists/{self.gist_id}", headers=headers, json=payload)

            embed = discord.Embed(title="🚀 Activación de Cliente", color=discord.Color.gold())
            embed.add_field(name="🏢 Empresa", value=empresa, inline=False)
            embed.add_field(name="🔑 ID Soporte", value=f"`{id_soporte}`", inline=False)
            embed.add_field(name="👤 Usuario", value=miembro.mention, inline=True)
            embed.add_field(name="📅 Vence el", value=fecha_fin.strftime(formato_fecha), inline=True)
            embed.set_footer(text="Blitz Hub • Gestión de Licencias")
            
            await ctx.send(embed=embed)
            
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

    # --- COMANDO CERRAR (Corregido) ---
    @commands.command(name="cerrar", aliases=["close"])
    async def cerrar_ticket(self, ctx):
        """Cierra el ticket, avisa al usuario y archiva el canal en la categoría de historial de la empresa."""
        usuario_ticket = None
        categoria_actual = ctx.channel.category
        
        # Identificar al usuario del ticket
        for target, overwrite in ctx.channel.overwrites.items():
            if isinstance(target, discord.Member) and not target.bot:
                rol_dev = ctx.guild.get_role(self.id_rol_dev)
                if target != ctx.guild.owner and target != rol_dev:
                    usuario_ticket = target
                    break

        if not usuario_ticket:
            parts = ctx.channel.name.split('-')
            if len(parts) >= 2:
                usuario_ticket = discord.utils.get(ctx.guild.members, name=parts[1])

        if usuario_ticket:
            embed_dm = discord.Embed(
                title="🎫 Ticket Finalizado",
                description=f"Tu consulta en **{ctx.guild.name}** ha sido marcada como resuelta.",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            try:
                await usuario_ticket.send(embed=embed_dm)
            except:
                pass

        try:
            if categoria_actual:
                # Limpiar el nombre de la categoría para el historial
                nombre_limpio = categoria_actual.name.replace('📁 ', '').replace('📜 HISTORIAL ', '')
                nombre_historial = f"📜 HISTORIAL {nombre_limpio}"
                
                cat_archivados = discord.utils.get(ctx.guild.categories, name=nombre_historial)
                
                if not cat_archivados:
                    rol_dev = ctx.guild.get_role(self.id_rol_dev)
                    overwrites_hist = {
                        ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                        ctx.guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True)
                    }
                    if rol_dev:
                        overwrites_hist[rol_dev] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
                    
                    cat_archivados = await ctx.guild.create_category(name=nombre_historial, overwrites=overwrites_hist)

                nuevo_nombre = f"✅-{ctx.channel.name}"[:100]
                
                if usuario_ticket:
                    await ctx.channel.set_permissions(usuario_ticket, overwrite=None)
                
                await ctx.channel.edit(name=nuevo_nombre, category=cat_archivados)
                await ctx.send(f"✅ Ticket archivado en **{cat_archivados.name}**.")

                # Borrar categoría original si queda vacía
                if len(categoria_actual.channels) == 0:
                    await categoria_actual.delete(reason="Categoría de empresa vacía.")
            else:
                nuevo_nombre = f"✅-{ctx.channel.name}"[:100]
                await ctx.channel.edit(name=nuevo_nombre)
                await ctx.send(f"⚠️ Canal renombrado (sin categoría de origen).")
                
        except Exception as e:
            await ctx.send(f"❌ Error al intentar cerrar el canal: {e}")

async def setup(bot):
    await bot.add_cog(CustomerService(bot))
