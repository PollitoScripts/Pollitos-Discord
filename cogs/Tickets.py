import discord
from discord.ext import commands

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # 1. Ignorar si el que reacciona es el bot
        if payload.user_id == self.bot.user.id:
            return

        # 2. Verificar que sea el emoji correcto
        if str(payload.emoji) != '✅':
            return

        # 3. Obtener el canal y el mensaje (Raw no los trae directamente)
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
            
        channel = guild.get_channel(payload.channel_id)
        try:
            message = await channel.fetch_message(payload.message_id)
        except Exception:
            return

        # 4. Verificaciones de seguridad (igual que tu código original)
        if not message.embeds:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            return

        # 5. Lógica de creación de ticket
        for embed in message.embeds:
            if embed.title:  
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }

                category = discord.utils.get(guild.categories, name='Tickets')
                if category is None:
                    category = await guild.create_category('Tickets')

                # Usamos el nombre de usuario limpio para evitar errores de caracteres
                ticket_channel_name = f'ticket-{member.name}'.lower()
                existing_channel = discord.utils.get(guild.channels, name=ticket_channel_name)
                
                if existing_channel:
                    try:
                        await member.send(f'Ya tienes un ticket abierto en {existing_channel.mention}.')
                    except:
                        pass
                    return

                # Crear el canal
                ticket_channel = await category.create_text_channel(ticket_channel_name, overwrites=overwrites)
                
                # Mensaje de bienvenida en el ticket
                welcome_embed = discord.Embed(
                    title="Ticket Abierto",
                    description=f"Hola {member.mention}, un administrador te atenderá pronto.\nServicio interesado: **{embed.title}**",
                    color=discord.Color.green()
                )
                await ticket_channel.send(embed=welcome_embed)
                
                try:
                    await member.send(f'Se ha creado un ticket para ti en {ticket_channel.mention}.')
                except:
                    pass
                return

    @commands.command(name="close_ticket")
    async def close_ticket(self, ctx):
        category_name = 'Tickets'
        closed_category_name = 'Tickets cerrados'

        if ctx.channel.category is None or ctx.channel.category.name != category_name:
            await ctx.send('Este comando solo puede ser usado en un canal de ticket.')
            return

        closed_category = discord.utils.get(ctx.guild.categories, name=closed_category_name)
        if not closed_category:
            closed_category = await ctx.guild.create_category(closed_category_name)

        await ctx.channel.edit(category=closed_category, sync_permissions=True)

        member = ctx.author
        await ctx.channel.set_permissions(member, overwrite=None)
        await ctx.send(f'Ticket cerrado por {member.mention}.')

        # Permisos para admins al cerrar
        for role in ctx.guild.roles:
            if role.permissions.administrator:
                await ctx.channel.set_permissions(role, read_messages=True, send_messages=True)

async def setup(bot):
    await bot.add_cog(Tickets(bot))
