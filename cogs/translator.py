import discord
from discord.ext import commands
from deep_translator import GoogleTranslator

# Canales de idiomas
LANG_CHANNELS = {
    "spanish": "es",
    "english": "en",
    "français": "fr"
}

class Translator(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.webhook_cache = {}
        self.message_map = {}  # Map de mensajes originales -> traducidos

    async def get_webhook(self, channel):
        """Obtiene o crea un webhook por canal."""
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

    def translate(self, text, source, target):
        """Función de traducción sincrónica."""
        return GoogleTranslator(source=source, target=target).translate(text)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.webhook_id:
            return

        if message.channel.name.lower() not in LANG_CHANNELS:
            return

        source_lang = LANG_CHANNELS[message.channel.name.lower()]
        translated_ids = []

        for ch_name, target_lang in LANG_CHANNELS.items():
            if target_lang == source_lang:
                continue

            target_channel = discord.utils.get(
                message.guild.text_channels,
                name=ch_name
            )
            if not target_channel:
                continue

            # Ejecuta la traducción sin bloquear el loop de discord
            translated_text = await self.bot.loop.run_in_executor(
                None,
                lambda: self.translate(message.content, source_lang, target_lang)
            )

            webhook = await self.get_webhook(target_channel)
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

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if after.id not in self.message_map:
            return

        source_lang = LANG_CHANNELS.get(after.channel.name.lower())
        if not source_lang:
            return

        for translated_msg in self.message_map[after.id]:
            target_lang = LANG_CHANNELS[translated_msg.channel.name.lower()]
            new_text = await self.bot.loop.run_in_executor(
                None,
                lambda: self.translate(after.content, source_lang, target_lang)
            )
            await translated_msg.edit(content=new_text)


async def setup(bot):
    await bot.add_cog(Translator(bot))
