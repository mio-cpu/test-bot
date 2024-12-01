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
    logger.critical("DISCORD_BOT_TOKEN が設定されていません。環境変数を確認してください。")
    exit(1)

# 必要なインテントの設定
intents = discord.Intents.default()
intents.members = True  # メンバー関連のイベントを有効化
bot = commands.Bot(command_prefix="!", intents=intents)

# 非活動日数のデフォルト設定
DEFAULT_INACTIVITY_DAYS = 30
inactivity_days = DEFAULT_INACTIVITY_DAYS


class InactivityManager(commands.Cog):
    """非活動メンバーを管理するコグ"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        """Cog がロードされたときにスラッシュコマンドを登録"""
        self.bot.tree.add_command(self.set_inactivity_days)
        self.bot.tree.add_command(self.get_inactivity_days)
        self.bot.tree.add_command(self.check_inactive_members)

    @app_commands.command(name="set_inactivity_days", description="非活動日数を設定します")
    async def set_inactivity_days(self, interaction: discord.Interaction, days: int):
        """非活動日数を設定するスラッシュコマンド"""
        try:
            global inactivity_days
            inactivity_days = days
            await interaction.response.send_message(f"非活動日数を {days} 日に設定しました！", ephemeral=True)
        except Exception as e:
            logger.error(f"非活動日数設定中にエラー: {e}")
            await interaction.response.send_message("非活動日数の設定中にエラーが発生しました。", ephemeral=True)

    @app_commands.command(name="get_inactivity_days", description="現在の非活動日数を確認します")
    async def get_inactivity_days(self, interaction: discord.Interaction):
        """現在の非活動日数を確認するスラッシュコマンド"""
        try:
            await interaction.response.send_message(f"現在の非活動日数は {inactivity_days} 日です。", ephemeral=True)
        except Exception as e:
            logger.error(f"非活動日数取得中にエラー: {e}")
            await interaction.response.send_message("非活動日数の確認中にエラーが発生しました。", ephemeral=True)

    @app_commands.command(name="check_inactive_members", description="非活動メンバーを確認します")
    async def check_inactive_members(self, interaction: discord.Interaction):
        """非活動メンバーを確認するスラッシュコマンド"""
        await interaction.response.defer(thinking=True)  # 処理中の応答を送信
        guild = interaction.guild
        now = datetime.now(timezone.utc)  # 現在時刻（UTC）
        inactive_threshold = now - timedelta(days=inactivity_days)  # 非活動判定の閾値
        inactive_members = []

        try:
            accessible_channels = [
                ch for ch in guild.text_channels if ch.permissions_for(guild.me).read_messages
            ]
            async for member in guild.fetch_members(limit=None):
                if member.bot:
                    continue  # BOT は無視

                is_active = False

                # テキストチャンネルのアクティビティ確認
                for channel in accessible_channels:
                    async for message in channel.history(limit=100, after=inactive_threshold):
                        if message.author == member:
                            is_active = True
                            break
                    if is_active:
                        break

                # VC ログのアクティビティ確認
                if not is_active and member.voice and member.voice.channel:
                    vc_join_time = member.voice.request_to_speak_timestamp or now  # VC 参加時刻
                    if vc_join_time > inactive_threshold:
                        is_active = True

                # 非活動メンバーをリストに追加
                if not is_active:
                    inactive_members.append(member)

            # 結果を作成（メンション形式）
            if inactive_members:
                message = "以下のメンバーが非活動です:\n" + "\n".join(
                    [member.mention for member in inactive_members]
                )
            else:
                message = "非活動のメンバーはいません。"

            await interaction.followup.send(message)  # 結果を送信

        except Exception as e:
            logger.error(f"非活動メンバーの確認中にエラーが発生しました: {e}")
            await interaction.followup.send("非活動メンバーの確認中にエラーが発生しました。", ephemeral=True)


@bot.event
async def on_ready():
    """Bot の準備完了時の処理"""
    logger.info("Bot is ready")
    logger.info(f"Connected to the following guilds: {[guild.name for guild in bot.guilds]}")

    # スラッシュコマンドを同期
    try:
        for guild in bot.guilds:
            synced = await bot.tree.sync(guild=guild)
            logger.info(f"スラッシュコマンドが {len(synced)} 個同期されました (ギルド: {guild.name})")
    except Exception as e:
        logger.error(f"スラッシュコマンドの同期中にエラーが発生しました: {e}")


async def setup(bot):
    """Bot のセットアップ時に Cog を登録"""
    await bot.add_cog(InactivityManager(bot))


bot.run(TOKEN)
