import discord
from discord.ext import commands, tasks

USER_COUNT_CHANNEL_ID = 1258162209612365877

class UserCountChannel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = USER_COUNT_CHANNEL_ID  
        self.update_user_count_channel.start() 

    @tasks.loop(minutes=1)
    async def update_user_count_channel(self):
        """Actualiza el nombre del canal de usuarios cada minuto."""
        if self.channel_id:
            for guild in self.bot.guilds:
                channel = guild.get_channel(int(self.channel_id))
                if channel:
                    member_count = guild.member_count
                    new_name = f"Usuarios: {member_count}"
                    if channel.name != new_name:
                        await channel.edit(name=new_name)

    @commands.Cog.listener()
    async def on_ready(self):
        """Evento que se ejecuta cuando el bot está listo."""
        print(f'{self.bot.user} ha iniciado sesión.')
        # Ejecutar la actualización del canal inmediatamente al iniciar el bot
        await self.update_user_count_channel()

async def setup(bot):
    await bot.add_cog(UserCountChannel(bot))
