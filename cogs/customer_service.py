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
        print("🛠️ Cog CustomerService (Versión Unificada) cargado")

    # --- COMANDO DE ALTA ÚNICO (Sin Email) ---
    @commands.has_role(int(os.getenv('ID_ROL_DEV', 0)))
    @commands.command(name="alta")
    async def alta(self, ctx, empresa: str, miembro: discord.Member, plan: str = "Full Hub"):
        """Registra empresa, vincula Discord y activa 30 días de suscripción."""
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

        await ctx.send(f"🛡️ Generando acceso maestro para **{empresa}**...")

        try:
            # 1. Obtener datos del Gist
            r = requests.get(f"https://api.github.com/gists/{self.gist_id}", headers=headers)
            r.raise_for_status()
            gist_data = r.json()

            # 2. Actualizar clientes.json
            clientes = json.loads(gist_data['files']['clientes.json']['content'])
            while id_soporte in clientes: 
                id_soporte = generar_codigo()
            
            clientes[id_soporte] = {
                "empresa": empresa,
                "plan": plan,
                "fecha_alta": fecha_inicio.strftime(formato_fecha),
                "fecha_expiracion": fecha_fin.strftime(formato_fecha),
                "estado": "activo"
            }
            
            # 3. Actualizar mapa_discord.json
            mapa_content = gist_data['files'].get('mapa_discord.json', {'content': '{}'})['content']
            mapa = json.loads(mapa_content)
            mapa[str(miembro.id)] = id_soporte

            # 4. Subir cambios
            payload = {
                "files": {
                    "clientes.json": {"content": json.dumps(clientes, indent=4)},
                    "mapa_discord.json": {"content": json.dumps(mapa, indent=4)}
                }
            }
            requests.patch(f"https://api.github.com/gists/{self.gist_id}", headers=headers, json=payload)

            # 5. Respuesta visual
            embed = discord.Embed(title="🚀 Activación Blitz Hub", color=discord.Color.gold())
            embed.add_field(name="🏢 Empresa", value=f"**{empresa}**", inline=False)
            embed.add_field(name="🔑 ID Soporte", value=f"`{id_soporte}`", inline=False)
            embed.add_field(name="👤 Usuario", value=miembro.mention, inline=True)
            embed.add_field(name="📅 Vence el", value=fecha_fin.strftime(formato_fecha), inline=True)
            embed.set_footer(text="ID lista para usar en el formulario web")
            
            await ctx.send(embed=embed)
            
            # 6. DM al cliente
            msg = (f"🎊 **¡Acceso Activado!**\n\n"
                   f"Tu ID para soporte es: `{id_soporte}`\n"
                   f"Empresa vinculada: **{empresa}**\n"
                   f"Válido hasta: **{fecha_fin.strftime(formato_fecha)}**")
            try:
                await miembro.send(msg)
            except:
                await ctx.send("⚠️ No pude enviar DM.")

        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    # --- COMANDO CERRAR ---
    @commands.command(name="cerrar", aliases=["close"])
    async def cerrar_ticket(self, ctx):
        """Archiva el canal y gestiona el historial por empresa."""
        usuario_ticket = None
        categoria_actual = ctx.channel.category
        
        for target, overwrite in ctx.channel.overwrites.items():
            if isinstance(target, discord.Member) and not target.bot:
                rol_dev = ctx.guild.get_role(self.id_rol_dev)
                if target != ctx.guild.owner and target != rol_dev:
                    usuario_ticket = target
                    break

        if usuario_ticket:
            try:
                embed_dm = discord.Embed(
                    title="🎫 Ticket Finalizado",
                    description=f"Tu consulta en **{ctx.guild.name}** ha sido resuelta.",
                    color=discord.Color.green()
                )
                await usuario_ticket.send(embed=embed_dm)
            except: pass

        try:
            if categoria_actual:
                nombre_base = categoria_actual.name.replace('📁 ', '').replace('📜 HISTORIAL ', '')
                nombre_historial = f"📜 HISTORIAL {nombre_base}"
                
                cat_archivados = discord.utils.get(ctx.guild.categories, name=nombre_historial)
                if not cat_archivados:
                    overwrites_hist = {
                        ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                        ctx.guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True)
                    }
                    rol_dev = ctx.guild.get_role(self.id_rol_dev)
                    if rol_dev: overwrites_hist[rol_dev] = discord.PermissionOverwrite(view_channel=True)
                    cat_archivados = await ctx.guild.create_category(name=nombre_historial, overwrites=overwrites_hist)

                if usuario_ticket:
                    await ctx.channel.set_permissions(usuario_ticket, overwrite=None)
                
                await ctx.channel.edit(name=f"✅-{ctx.channel.name}"[:100], category=cat_archivados)
                await ctx.send(f"✅ Archivado en **{cat_archivados.name}**.")

                if len(categoria_actual.channels) == 0:
                    await categoria_actual.delete()
            else:
                await ctx.channel.edit(name=f"✅-{ctx.channel.name}"[:100])
                await ctx.send("⚠️ Solo renombrado (sin categoría).")
                
        except Exception as e:
            await ctx.send(f"❌ Error al cerrar: {e}")

async def setup(bot):
    await bot.add_cog(CustomerService(bot))
