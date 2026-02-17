import os
import requests
import json
import random
import string
import discord
from discord.ext import commands

class ClientesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gist_id = os.getenv('GIST_ID')
        self.github_token = os.getenv('GITHUB_TOKEN')

    # --- MÉTODOS PRIVADOS ---
    def _get_clientes(self):
        """Lee los clientes desde GitHub Gist"""
        headers = {"Authorization": f"token {self.github_token}"}
        r = requests.get(f"https://api.github.com/gists/{self.gist_id}", headers=headers)
        r.raise_for_status() # Lanza error si la petición falla
        gist = r.json()
        content = gist['files']['clientes.json']['content']
        return json.loads(content)

    def _update_clientes(self, data):
        """Actualiza el archivo en GitHub Gist"""
        headers = {"Authorization": f"token {self.github_token}"}
        payload = {"files": {"clientes.json": {"content": json.dumps(data, indent=4)}}}
        r = requests.patch(f"https://api.github.com/gists/{self.gist_id}", headers=headers, json=payload)
        r.raise_for_status()

    # --- COMANDO: ALTA CLIENTE ---
    @commands.command(name="alta")
    @commands.has_permissions(administrator=True)
    async def alta_cliente(self, ctx, empresa: str):
        """Genera un ID único y lo guarda en el Gist"""
        try:
            suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            nuevo_id = f"BLITZ-{empresa[:3].upper()}-{suffix}"
            
            clientes = self._get_clientes()
            clientes[nuevo_id] = {"empresa": empresa, "plan": "Full Hub"}
            self._update_clientes(clientes)
            
            await ctx.send(f"✅ **Cliente Registrado**\nEmpresa: {empresa}\nID Soporte: `{nuevo_id}`")
        except Exception as e:
            await ctx.send(f"❌ Error al procesar el alta: {e}")

    # --- COMANDO: DIAGNÓSTICO ---
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
                await ctx.send(f"✅ **Conexión Exitosa.**\n📂 Archivo: `clientes.json` detectado.\n👥 Clientes en base de datos: `{num_clientes}`")
            elif r.status_code == 404:
                await ctx.send("❌ **Error 404:** No se encontró el Gist. Revisa el `GIST_ID`.")
            elif r.status_code == 401:
                await ctx.send("❌ **Error 401:** Token no válido. Revisa el `GITHUB_TOKEN`.")
            else:
                await ctx.send(f"⚠️ **Error inesperado:** Código {r.status_code}")
                
        except Exception as e:
            await ctx.send(f"💀 **Fallo crítico:** {str(e)}")

    # --- LISTENER: VERIFICADOR DE WEBHOOKS ---
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
                    await message.channel.send(f"🛡️ **VERIFICADO:** Cliente `{empresa_nombre}` VIP confirmado. @everyone")
                else:
                    await message.channel.send("⚠️ **AVISO:** Ticket de invitado o ID no válido.")
            except Exception as e:
                print(f"Error verificando ID: {e}")

# Función necesaria para cargar el cog
async def setup(bot):
    await bot.add_cog(ClientesCog(bot))
