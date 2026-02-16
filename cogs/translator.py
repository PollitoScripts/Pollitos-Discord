import discord
from discord.ext import commands
from deep_translator import GoogleTranslator
import asyncio

# Canales y sus idiomas
LANG_CHANNELS = {
    "spanish": "es",
    "english": "en",
    "français": "fr"
}

class Translator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.webhook_cache = {}  # cache de webhooks por canal
        self.message_map = {}    # map de mensajes originales a traducidos

    # Obtener o crear webhook para un canal
    async def get_webhook(self, channel: discord.TextChannel):
        if channel.id in self.webhook_cache:
            return self.webhook_cache[channel.id]

        webhooks = await channel.webhooks()
        for wh in webhooks:
            if wh.name == "translator_webhook":
                self.webhook_cache[channel.id] = wh
                return wh

        webhook = await channel.create_webhook(name="translator_webhook")
        self.webhook_cache[channel.id] = webhook
        return webhook

    # Función de traducción bloqueante, se ejecutará en un hilo aparte
    def translate(self, text: str, source: str, target: str) -> str:
        return GoogleTranslator(source=source, target=target).translate(text)

    # Listener de mensajes nuevos
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.webhook_id:
            return

        if message.channel.name.lower() not in LANG_CHANNELS:
            return

        source_lang = LANG_CHANNELS[message.channel.name.lower()]
        translated_ids = []

        for ch_name, target_lang in LANG_CHANNELS.items():
            if target_lang == source_lang:
                continue

            target_channel = discord.utils.get(message.guild.text_channels, name=ch_name)
            if not target_channel:
                continue

            # Traduce en un hilo aparte para no bloquear el bot
            translated_text = await asyncio.to_thread(
                self.translate, message.content, source_lang, target_lang
            )

            webhook = await self.get_webhook(target_channel)

            # Referencia si el mensaje es una respuesta
            reply_to = None
            if message.reference and message.reference.message_id:
                original_id = message.reference.message_id
                if original_id in self.message_map:
                    for m in self.message_map[original_id]:
                        if m.channel.id == target_channel.id:
                            reply_to = await target_channel.fetch_message(m.id)

            sent = await webhook.send(
                translated_text,
                username=message.author.display_name,
                avatar_url=message.author.display_avatar.url,
                wait=True,
                reference=reply_to
            )

            translated_ids.append(sent)

        self.message_map[message.id] = translated_ids

    # Listener de edición de mensajes
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.id not in self.message_map:
            return

        source_lang = LANG_CHANNELS.get(after.channel.name.lower())
        if not source_lang:
            return

        for translated_msg in self.message_map[after.id]:
            target_lang = LANG_CHANNELS[translated_msg.channel.name.lower()]

            # Traduce en un hilo aparte para no bloquear
            new_text = await asyncio.to_thread(
                self.translate, after.content, source_lang, target_lang
            )

            await translated_msg.edit(content=new_text)

# Función de setup para cargar el cog
async def setup(bot):
    await bot.add_cog(Translator(bot))
