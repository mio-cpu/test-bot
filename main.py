import os
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import logging

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数を読み込み
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN が設定されていません。環境変数を確認してください。")

# 必要なインテントの設定
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 非活動日数のデフォルト設定
DEFAULT_INACTIVITY_DAYS = 30
inactivity_days = DEFAULT_INACTIVITY_DAYS


class InactivityManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set_inactivity_days", description="非活動日数を設定します")
    async def set_inactivity_days(self, interaction: discord.Interaction, days: int):
        global inactivity_days
        inactivity_days = days
        await interaction.response.send_message(f"非活動日数を {days} 日に設定しました！", ephemeral=True)

    @app_commands.command(name="get_inactivity_days", description="現在の非活動日数を確認します")
    async def get_inactivity_days(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"現在の非活動日数は {inactivity_days} 日です。", ephemeral=True)

    @app_commands.command(name="check_inactive_members", description="非活動メンバーを確認します")
    async def check_inactive_members(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        guild = interaction.guild
        now = datetime.now(timezone.utc)
        inactive_threshold = now - timedelta(days=inactivity_days)
        inactive_members = []

        try:
            # キャッシュされたメンバーを利用
            for member in guild.members:
                if member.bot:
                    continue

                last_message = None
                async for message in interaction.channel.history(limit=100):  # チャネル履歴を制限
                    if message.author == member:
                        last_message = message.created_at
                        break

                if not last_message or last_message.replace(tzinfo=timezone.utc) < inactive_threshold:
                    inactive_members.append(member)

            if inactive_members:
                message = "以下のメンバーが非活動です:\n" + "\n".join([member.mention for member in inactive_members])
            else:
                message = "非活動のメンバーはいません。"

            await interaction.followup.send(message)

        except Exception as e:
            logger.error(f"Error occurred while checking inactive members: {e}")
            await interaction.followup.send("非活動メンバーの確認中にエラーが発生しました。", ephemeral=True)


@bot.event
async def on_ready():
    logger.info("Bot is ready")
    logger.info(f"Connected to the following guilds: {[guild.name for guild in bot.guilds]}")

    try:
        synced = await bot.tree.sync()
        logger.info(f"グローバルにスラッシュコマンドを同期しました: {len(synced)} 個")
    except Exception as e:
        logger.error(f"スラッシュコマンドの同期中にエラーが発生しました: {e}")


async def setup_hook():
    await bot.add_cog(InactivityManager(bot))


bot.setup_hook = setup_hook

bot.run(TOKEN)
