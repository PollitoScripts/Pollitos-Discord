import os
import requests
import json
import random
import string
import discord
import datetime
from discord.ext import commands

class ClientesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gist_id = os.getenv('GIST_ID')
        self.github_token = os.getenv('GITHUB_TOKEN')

    # --- MÉTODOS PRIVADOS (Sin cambios) ---
    def _get_clientes(self):
        """Lee los clientes desde GitHub Gist"""
        headers = {"Authorization": f"token {self.github_token}"}
        r = requests.get(f"https://api.github.com/gists/{self.gist_id}", headers=headers)
        r.raise_for_status() 
        gist = r.json()
        content = gist['files']['clientes.json']['content']
        return json.loads(content)

    def _update_clientes(self, data):
        """Actualiza el archivo en GitHub Gist"""
        headers = {"Authorization": f"token {self.github_token}"}
        payload = {"files": {"clientes.json": {"content": json.dumps(data, indent=4)}}}
        r = requests.patch(f"https://api.github.com/gists/{self.gist_id}", headers=headers, json=payload)
        r.raise_for_status()

    # --- COMANDO: ALTA CLIENTE (Mejorado con Email y Plan) ---
    @commands.command(name="alta")
    @commands.has_permissions(administrator=True)
    async def alta_cliente(self, ctx, empresa: str, email: str, plan: str = "Full Hub"):
        """Genera un ID único, registra email/plan y guarda en el Gist"""
        try:
            # 1. Generación de ID estilo Blitz
            suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            year = datetime.date.today().year
            nuevo_id = f"BLITZ-{year}-{suffix}"
            
            # 2. Obtener datos actuales y añadir nuevo
            clientes = self._get_clientes()
            clientes[nuevo_id] = {
                "empresa": empresa,
                "email": email,
                "plan": plan,
                "fecha_alta": datetime.date.today().strftime("%d/%m/%Y")
            }
            
            # 3. Guardar en Gist
            self._update_clientes(clientes)
            
            # 4. Presentación visual del alta
            embed = discord.Embed(
                title="🚀 Registro Exitoso: Hub de Clientes",
                color=discord.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="🏢 Empresa", value=empresa, inline=True)
            embed.add_field(name="📧 Email", value=email, inline=True)
            embed.add_field(name="🔑 ID SOPORTE", value=f"`{nuevo_id}`", inline=False)
            embed.add_field(name="📦 Plan Contratado", value=plan, inline=True)
            embed.set_footer(text="ID lista para usar en el formulario web")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error al procesar el alta: {e}")

    # --- COMANDO: DIAGNÓSTICO (Sin cambios) ---
    @commands.command(name="check_hub")
    @commands.has_permissions(administrator=True)
    async def check_hub(self, ctx):
        """Verifica la conexión con el Gist de GitHub"""
        await ctx.send("🔍 Iniciando diagnóstico de conexión...")
        try:
            headers = {"Authorization": f"token {self.github_token}"}
            r = requests.get(f"https://api.github.com/gists/{self.gist_id}", headers=headers)
            
            if r.status_code == 200:
                clientes = self._get_clientes()
                num_clientes = len(clientes)
                await ctx.send(f"✅ **Conexión Exitosa.**\n📂 Archivo: `clientes.json` detectado.\n👥 Clientes activos: `{num_clientes}`")
            elif r.status_code == 404:
                await ctx.send("❌ **Error 404:** Gist no encontrado.")
            elif r.status_code == 401:
                await ctx.send("❌ **Error 401:** Token inválido.")
            else:
                await ctx.send(f"⚠️ **Error inesperado:** {r.status_code}")
        except Exception as e:
            await ctx.send(f"💀 **Fallo crítico:** {str(e)}")

    # --- LISTENER: VERIFICADOR DE WEBHOOKS (Sin cambios) ---
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot and message.author.name == "Blitz Web Intake":
            if not message.embeds:
                return

            embed = message.embeds[0]
            id_proporcionado = "GUEST"

            for field in embed.fields:
                if "ID Contrato" in field.name:
                    id_proporcionado = field.value.replace("`", "").strip()
            
            try:
                clientes = self._get_clientes()
                if id_proporcionado in clientes:
                    empresa_nombre = clientes[id_proporcionado]['empresa']
                    plan_cliente = clientes[id_proporcionado].get('plan', 'N/A')
                    await message.channel.send(f"🛡️ **VERIFICADO:** Cliente `{empresa_nombre}` ({plan_cliente}) confirmado. @everyone")
                else:
                    await message.channel.send("⚠️ **AVISO:** Ticket de invitado o ID no válido.")
            except Exception as e:
                print(f"Error verificando ID: {e}")

async def setup(bot):
    await bot.add_cog(ClientesCog(bot))
