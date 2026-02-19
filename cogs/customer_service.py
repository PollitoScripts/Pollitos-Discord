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
        print("🛠️ Cog CustomerService Integrado cargado")

    def _get_clientes(self):
        headers = {"Authorization": f"token {self.github_token}"}
        r = requests.get(f"https://api.github.com/gists/{self.gist_id}", headers=headers)
        r.raise_for_status() 
        return json.loads(r.json()['files']['clientes.json']['content'])

    # --- COMANDO ALTA ---
# --- COMANDO ALTA (Actualizado con campo de vencimiento) ---
    @commands.has_role(int(os.getenv('ID_ROL_DEV', 0)))
    @commands.command(name="alta")
    async def alta(self, ctx, empresa: str, miembro: discord.Member, plan: str = "Full Hub"):
        """Registra empresa, vincula Discord y activa 30 días."""
        headers = {"Authorization": f"token {self.github_token}"}
        
        def generar_codigo():
            chars = string.ascii_uppercase + string.digits
            return f"BLITZ-{''.join(secrets.choice(chars) for _ in range(4))}-{''.join(secrets.choice(chars) for _ in range(4))}"

        id_soporte = generar_codigo()
        fecha_fin = datetime.now() + timedelta(days=30)
        formato = "%d/%m/%Y"

        await ctx.send(f"🛡️ Generando acceso para **{empresa}**...")

        try:
            r = requests.get(f"https://api.github.com/gists/{self.gist_id}", headers=headers)
            gist_data = r.json()
            clientes = json.loads(gist_data['files']['clientes.json']['content'])
            
            clientes[id_soporte] = {
                "empresa": empresa,
                "plan": plan,
                "fecha_alta": datetime.now().strftime(formato),
                "fecha_expiracion": fecha_fin.strftime(formato),
                "estado": "activo"
            }
            
            mapa = json.loads(gist_data['files'].get('mapa_discord.json', {'content': '{}'})['content'])
            mapa[str(miembro.id)] = id_soporte

            payload = {"files": {
                "clientes.json": {"content": json.dumps(clientes, indent=4)},
                "mapa_discord.json": {"content": json.dumps(mapa, indent=4)}
            }}
            requests.patch(f"https://api.github.com/gists/{self.gist_id}", headers=headers, json=payload)

            # --- EMBED VISUAL CORREGIDO ---
            embed = discord.Embed(
                title="🚀 Activación Blitz Hub", 
                color=discord.Color.gold(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="🏢 Empresa", value=f"**{empresa}**", inline=False)
            embed.add_field(name="🔑 ID Soporte", value=f"`{id_soporte}`", inline=False)
            embed.add_field(name="👤 Usuario", value=miembro.mention, inline=True)
            embed.add_field(name="📦 Plan Activo", value=plan, inline=True)
            
            # Nuevo campo destacado para la fecha de vencimiento
            embed.add_field(name="📅 Fecha de Vencimiento", value=f"**{fecha_fin.strftime(formato)}**", inline=False)
            
            # Mantenemos el footer como respaldo visual
            embed.set_footer(text=f"Blitz Hub • Vence el {fecha_fin.strftime(formato)}") 
            
            await ctx.send(embed=embed)
            
            # --- DM AL USUARIO ---
            try: 
                mensaje_dm = (f"🎊 ¡Acceso Activo!\n\n"
                              f"🔑 **ID:** `{id_soporte}`\n"
                              f"🏢 **Empresa:** **{empresa}**\n"
                              f"📅 **Vence el:** `{fecha_fin.strftime(formato)}`")
                await miembro.send(mensaje_dm)
            except: 
                pass

        except Exception as e: 
            await ctx.send(f"❌ Error: {e}")
            # --- DM AL USUARIO (Actualizado) ---
            try: 
                mensaje_dm = (f"🎊 ¡Acceso Activo!\n\n"
                              f"🔑 **ID:** `{id_soporte}`\n"
                              f"🏢 **Empresa:** **{empresa}**\n"
                              f"📅 **Vence el:** `{fecha_fin.strftime(formato)}`")
                await miembro.send(mensaje_dm)
            except: 
                pass

        except Exception as e: 
            await ctx.send(f"❌ Error: {e}")

    # --- COMANDO CERRAR ---
    @commands.command(name="cerrar", aliases=["close"])
    async def cerrar_ticket(self, ctx):
        """Archiva el ticket y limpia categorías."""
        # (Lógica de cierre que ya funciona perfectamente)
        categoria_actual = ctx.channel.category
        if not categoria_actual: return await ctx.send("Canal sin categoría.")
        
        nombre_historial = f"📜 HISTORIAL {categoria_actual.name.replace('📁 ', '')}"
        cat_archivados = discord.utils.get(ctx.guild.categories, name=nombre_historial)
        
        if not cat_archivados:
            cat_archivados = await ctx.guild.create_category(name=nombre_historial)

        await ctx.channel.edit(name=f"✅-{ctx.channel.name}"[:100], category=cat_archivados)
        await ctx.send(f"✅ Archivado en {cat_archivados.name}")
        if len(categoria_actual.channels) == 0: await categoria_actual.delete()

    # --- COMANDO DIAGNÓSTICO (Rescatado) ---
    @commands.command(name="check_hub")
    async def check_hub(self, ctx):
        """Verifica conexión con GitHub."""
        try:
            clientes = self._get_clientes()
            await ctx.send(f"✅ Conexión OK. Clientes en base de datos: `{len(clientes)}`")
        except Exception as e:
            await ctx.send(f"❌ Error de conexión: {e}")

    # --- LISTENER WEBHOOKS (Rescatado) ---
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot and "Blitz Web Intake" in message.author.name:
            if not message.embeds: return
            id_proporcionado = "GUEST"
            for field in message.embeds[0].fields:
                if "ID Contrato" in field.name:
                    id_proporcionado = field.value.replace("`", "").strip()
            
            try:
                clientes = self._get_clientes()
                if id_proporcionado in clientes:
                    emp = clientes[id_proporcionado]['empresa']
                    await message.channel.send(f"🛡️ **VERIFICADO:** Cliente `{emp}` confirmado. @everyone")
            except: pass

async def setup(bot):
    await bot.add_cog(CustomerService(bot))
