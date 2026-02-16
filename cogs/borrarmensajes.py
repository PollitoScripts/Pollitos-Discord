import discord
import config 
from discord.ext import commands

class clean(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    async def clean(self,ctx, cantidad:int):
        await ctx.message.delete()
        await ctx.channel.purge(limit=cantidad+1)

    @commands.command()
    async def cleanUser(self, ctx, usuario: commands.MemberConverter, cantidad: int):
        await ctx.message.delete()
        def check(m):
            return m.author == usuario
        await ctx.channel.purge(limit=cantidad + 1, check=check)

async def setup(bot):
    await bot.add_cog(clean(bot))


