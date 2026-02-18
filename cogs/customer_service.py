import discord
from discord.ext import commands
import requests

class CustomerService(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # --- CONFIGURACIÓN DE IDs DEL SERVIDOR DE CLIENTES ---
        self.ID_ROL_DEV = 1473366087390331094  # Tu ID de rol en este server
        self.CAT_VIP_NAME = '📁 SOPORTE VIP (SLA < 4h)'
        self.CAT_ESTANDAR_NAME = '📁 SOPORTE ESTÁNDAR'

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Blindaje y creación automática solo para clientes registrados"""
        
        # 1. Conexión con tus Gists
        # Aquí es donde el bot decide si el que entra es un cliente o no
        # Por ahora lo dejamos listo para conectar con tu JSON
        datos_cliente = self.obtener_datos_de_gists(member.id)
        
        if not datos_cliente:
            # Si no es cliente, se queda solo viendo #bienvenida
            print(f"Usuario no registrado entró: {member.name}")
            return

        # 2. Extraer info del Gist
        blitz_id = datos_cliente['blitz_id']
        empresa = datos_cliente['empresa']
        plan = datos_cliente['plan']

        # 3. Lógica de Categoría
        guild = member.guild
        nombre_categoria = self.CAT_VIP_NAME if plan != "Essential" else self.CAT_ESTANDAR_NAME
        
        category = discord.utils.get(guild.categories, name=nombre_categoria)
        if not category:
            category = await guild.create_category(nombre_categoria)

        # 4. Blindaje de canal (Permission Overwrites)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        
        rol_dev = guild.get_role(self.ID_ROL_DEV)
        if rol_dev:
            overwrites[rol_dev] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        # 5. Crear el canal privado
        # Limpiamos el nombre para que Discord no dé error
        clean_name = f"{blitz_id}-{empresa}".lower().replace(" ", "-").replace(".", "")
        canal_soporte = await category.create_text_channel(name=clean_name, overwrites=overwrites)

        # 6. Mensaje de bienvenida profesional
        color = discord.Color.gold() if plan != "Essential" else discord.Color.blue()
        embed = discord.Embed(
            title=f"Ecosistema de Soporte: {empresa}",
            description=f"Hola {member.mention}, se ha desplegado tu canal privado de soporte **{plan}**.",
            color=color
        )
        embed.set_footer(text="Blitz Hub - Sistema de Gestión de Incidencias")
        
        await canal_soporte.send(embed=embed)
        
        # Notificación proactiva para ti
        if plan != "Essential":
            await canal_soporte.send(f"<@&{self.ID_ROL_DEV}> 🚨 **CLIENTE FULL HUB DETECTADO**")

    def obtener_datos_de_gists(self, discord_id):
        """Función puente para leer tus Gists A y B"""
        # Aquí es donde pegaremos la lógica de requests.get() que vimos antes
        # Por ahora, puedes devolver un None o un dict de prueba para testear
        return None 

async def setup(bot):
    await bot.add_cog(CustomerService(bot))
