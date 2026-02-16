import discord
import config 
import json
from discord.ext import commands

class embed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        # Verificamos que la reacción sea del usuario y del emoji correcto
        if user.bot or reaction.emoji != '✅':
            return
        
        message = reaction.message
        embeds = message.embeds
        
        for embed in embeds:
            if embed.title:  # Asegúrate de que el embed tenga un título
                # Aquí podrías agregar más validaciones si es necesario
                guild = message.guild
                member = guild.get_member(user.id)
                
                # Lógica para crear el canal privado
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    member: discord.PermissionOverwrite(read_messages=True),
                }
                category = discord.utils.get(guild.categories, name='Tickets')
                if category is None:
                    category = await guild.create_category('Tickets')
                
                # Asegurémonos de que el nombre del canal sea único
                ticket_channel_name = f'ticket-{user.display_name}'
                existing_channel = discord.utils.get(guild.channels, name=ticket_channel_name)
                if existing_channel:
                    await user.send(f'Ya tienes un ticket abierto en {existing_channel.mention}.')
                    return
                
                ticket_channel = await category.create_text_channel(ticket_channel_name, overwrites=overwrites)
                await user.send(f'Se ha creado un ticket para ti en {ticket_channel.mention}.')
                return
            
    @commands.command()
    async def closeTicket(self, ctx):
        # Verificamos que el comando sea ejecutado en un canal de ticket
        category_name = 'Tickets'
        closed_category_name = 'Tickets cerrados'
        
        if ctx.channel.category.name != category_name:
            await ctx.send('Este comando solo puede ser usado en un canal de ticket.')
            return
        
        # Movemos el canal a la categoría de Tickets cerrados
        closed_category = discord.utils.get(ctx.guild.categories, name=closed_category_name)
        if not closed_category:
            closed_category = await ctx.guild.create_category(closed_category_name)
        
        await ctx.channel.edit(category=closed_category, sync_permissions=True)
        
        # Sacamos al usuario del canal
        member = ctx.author
        await ctx.channel.set_permissions(member, overwrite=None)
        
        # Notificamos al usuario y a los administradores
        await member.send(f'Se ha cerrado el ticket {ctx.channel.mention}.')
        
        admins = [admin for admin in ctx.guild.members if admin.guild_permissions.administrator]
        for admin in admins:
            await ctx.channel.set_permissions(admin, read_messages=True, send_messages=True)

async def setup(bot):
    await bot.add_cog(embed(bot))


