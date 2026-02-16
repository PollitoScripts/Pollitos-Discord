import discord
from discord.ext import commands
from deep_translator import GoogleTranslator
import asyncio
import logging

# Configuración de logs para que aparezcan en la consola de Render
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('TranslatorCog')

LANG_CHANNELS = {
    "spanish": "es",
    "english": "en",
    "français": "fr"
}

class Translator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.webhook_cache = {}
        self.message_map = {}

    async def get_webhook(self, channel: discord.TextChannel):
        if channel.id in self.webhook_cache:
            return self.webhook_cache[channel.id]

        try:
            webhooks = await channel.webhooks()
            for wh in webhooks:
                if wh.name == "translator_webhook":
                    self.webhook_cache[channel.id] = wh
                    return wh

            logger.info(f"Creando nuevo webhook en canal: {channel.name}")
            webhook = await channel.create_webhook(name="translator_webhook")
            self.webhook_cache[channel.id] = webhook
            return webhook
        except discord.Forbidden:
            logger.error(f"¡ERROR! No tengo permisos para gestionar webhooks en {channel.name}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado en get_webhook: {e}")
            return None

    def translate_text(self, text: str, target: str) -> str:
        try:
            # Usamos auto para evitar conflictos de detección en Render
            result = GoogleTranslator(source='auto', target=target).translate(text)
            return result
        except Exception as e:
            logger.error(f"Fallo de GoogleTranslator: {e}")
            return None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.webhook_id or not message.content:
            return

        canal_orig = message.channel.name.lower()
        if canal_orig not in LANG_CHANNELS:
            return

        logger.info(f"Detectado mensaje en #{canal_orig}: {message.content[:20]}...")
        
        source_lang = LANG_CHANNELS[canal_orig]
        translated_msgs = []

        for ch_name, target_lang in LANG_CHANNELS.items():
            if target_lang == source_lang:
                continue

            target_channel = discord.utils.get(message.guild.text_channels, name=ch_name)
            if not target_channel:
                logger.warning(f"No se encontró el canal de destino: {ch_name}")
                continue

            # Traducir
            translated_text = await asyncio.to_thread(self.translate_text, message.content, target_lang)
            
            if not translated_text:
                continue

            webhook = await self.get_webhook(target_channel)
            if not webhook:
                continue

            try:
                sent = await webhook.send(
                    content=translated_text,
                    username=f"{message.author.display_name} ({target_lang.upper()})",
                    avatar_url=message.author.display_avatar.url,
                    wait=True
                )
                translated_msgs.append(sent)
                logger.info(f"Traducción enviada a #{ch_name}")
            except Exception as e:
                logger.error(f"Error al enviar mensaje vía Webhook: {e}")

        if translated_msgs:
            self.message_map[message.id] = translated_msgs

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.id not in self.message_map or before.content == after.content:
            return

        logger.info(f"Editando traducciones para mensaje {after.id}")
        for msg in self.message_map[after.id]:
            target_lang = LANG_CHANNELS.get(msg.channel.name.lower())
            if not target_lang: continue

            new_text = await asyncio.to_thread(self.translate_text, after.content, target_lang)
            if new_text:
                try:
                    await msg.edit(content=new_text)
                except Exception as e:
                    logger.error(f"No se pudo editar la traducción: {e}")

async def setup(bot):
    await bot.add_cog(Translator(bot))
