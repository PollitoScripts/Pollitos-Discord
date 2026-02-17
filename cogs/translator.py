import discord
from discord.ext import commands
from deep_translator import GoogleTranslator
import asyncio
import logging

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
            webhook = await channel.create_webhook(name="translator_webhook")
            self.webhook_cache[channel.id] = webhook
            return webhook
        except Exception as e:
            logger.error(f"Error webhooks: {e}")
            return None

    def translate_text(self, text: str, target: str) -> str:
        try:
            return GoogleTranslator(source='auto', target=target).translate(text)
        except Exception as e:
            logger.error(f"Error traducción: {e}")
            return None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.webhook_id or not message.content:
            return

        prefijos = ("!", ".", "/", "$", ">") 
        if message.content.startswith(prefijos):
            return

        canal_orig = message.channel.name.lower()
        if canal_orig not in LANG_CHANNELS:
            return

        source_lang = LANG_CHANNELS[canal_orig]
        translated_msgs = []

        for ch_name, target_lang in LANG_CHANNELS.items():
            if target_lang == source_lang: continue
            target_channel = discord.utils.get(message.guild.text_channels, name=ch_name)
            if not target_channel: continue

            text = await asyncio.to_thread(self.translate_text, message.content, target_lang)
            if not text: continue

            webhook = await self.get_webhook(target_channel)
            if not webhook: continue

            sent = await webhook.send(
                content=text,
                username=f"{message.author.display_name} ({target_lang.upper()})",
                avatar_url=message.author.display_avatar.url,
                wait=True
            )
            translated_msgs.append(sent)

        if translated_msgs:
            self.message_map[message.id] = translated_msgs

    # --- REPLICAR AÑADIR REACCIÓN ---
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        if payload.message_id in self.message_map:
            for translated_msg in self.message_map[payload.message_id]:
                try:
                    channel = self.bot.get_channel(translated_msg.channel.id)
                    msg = await channel.fetch_message(translated_msg.id)
                    await msg.add_reaction(payload.emoji)
                except Exception:
                    pass

    # --- NUEVO: REPLICAR QUITAR REACCIÓN ---
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        if payload.message_id in self.message_map:
            for translated_msg in self.message_map[payload.message_id]:
                try:
                    channel = self.bot.get_channel(translated_msg.channel.id)
                    msg = await channel.fetch_message(translated_msg.id)
                    # El bot quita SU reacción (la que replicó antes)
                    await msg.remove_reaction(payload.emoji, self.bot.user)
                except Exception:
                    pass

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        prefijos = ("!", ".", "/", "$", ">")
        if after.id not in self.message_map or before.content == after.content or after.content.startswith(prefijos):
            return

        for msg in self.message_map[after.id]:
            target_lang = LANG_CHANNELS.get(msg.channel.name.lower())
            if not target_lang: continue
            new_text = await asyncio.to_thread(self.translate_text, after.content, target_lang)
            if new_text:
                try: await msg.edit(content=new_text)
                except: pass

async def setup(bot):
    await bot.add_cog(Translator(bot))
