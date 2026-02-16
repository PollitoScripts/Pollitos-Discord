import discord
from discord.ext import commands

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot or reaction.emoji != '✅':
            return
        
        message = reaction.message
        if not message.embeds:
            return
        
        guild = message.guild
        member = guild.get_member(user.id)
        if not member:
            return

        # Verificamos cada embed en el mensaje
        for embed in message.embeds:
            if embed.title:  # Título obligatorio
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    member: discord.PermissionOverwrite(read_messages=True),
                }

                category = discord.utils.get(guild.categories, name='Tickets')
                if category is None:
                    category = await guild.create_category('Tickets')

                ticket_channel_name = f'ticket-{user.display_name}'
                existing_channel = discord.utils.get(guild.channels, name=ticket_channel_name)
                if existing_channel:
                    await user.send(f'Ya tienes un ticket abierto en {existing_channel.mention}.')
                    return

                ticket_channel = await category.create_text_channel(ticket_channel_name, overwrites=overwrites)
                await user.send(f'Se ha creado un ticket para ti en {ticket_channel.mention}.')
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

        # Notificamos al usuario
        await member.send(f'Se ha cerrado el ticket {ctx.channel.mention}.')

        # Aseguramos permisos de admins
        for admin in ctx.guild.members:
            if admin.guild_permissions.administrator:
                await ctx.channel.set_permissions(admin, read_messages=True, send_messages=True)

async def setup(bot):
    await bot.add_cog(Tickets(bot))
