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
intents.members = True  # メンバー関連のイベントを有効化
intents.message_content = True  # メッセージ内容を取得可能に
bot = commands.Bot(command_prefix="!", intents=intents)

# 非活動日数のデフォルト設定
DEFAULT_INACTIVITY_DAYS = 30
inactivity_days = DEFAULT_INACTIVITY_DAYS


class InactivityManager(commands.Cog):
    """非活動メンバーを管理するコグ"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set_inactivity_days", description="非活動日数を設定します")
    async def set_inactivity_days(self, interaction: discord.Interaction, days: int):
        """非活動日数を設定するスラッシュコマンド"""
        global inactivity_days
        inactivity_days = days
        await interaction.response.send_message(f"非活動日数を {days} 日に設定しました！", ephemeral=True)

    @app_commands.command(name="get_inactivity_days", description="現在の非活動日数を確認します")
    async def get_inactivity_days(self, interaction: discord.Interaction):
        """現在の非活動日数を確認するスラッシュコマンド"""
        await interaction.response.send_message(f"現在の非活動日数は {inactivity_days} 日です。", ephemeral=True)

    @app_commands.command(name="check_inactive_members", description="非活動メンバーを確認します")
    async def check_inactive_members(self, interaction: discord.Interaction):
        """非活動メンバーを確認するスラッシュコマンド"""
        await interaction.response.defer(thinking=True)  # 処理中の応答を送信

        guild = interaction.guild
        now = datetime.now(timezone.utc)  # 現在時刻（UTC）
        inactive_threshold = now - timedelta(days=inactivity_days)  # 非活動判定の閾値
        inactive_members = []

        try:
            # 全メンバーを取得
            async for member in guild.fetch_members(limit=None):
                if member.bot:
                    continue  # BOT は無視

                is_active = False

                # メンバーのテキストアクティビティ確認
                for channel in guild.text_channels:
                    try:
                        async for message in channel.history(limit=100):  # 取得件数を制限
                            if message.author == member and message.created_at > inactive_threshold:
                                is_active = True
                                break
                        if is_active:
                            break
                    except discord.Forbidden:
                        continue  # 権限がないチャンネルはスキップ

                # メンバーの VC アクティビティ確認
                if not is_active and member.voice and member.voice.channel:
                    is_active = True

                # 非活動メンバーをリストに追加
                if not is_active:
                    inactive_members.append(member)

            # 結果を作成
            if inactive_members:
                message = "以下のメンバーが非活動です:\n" + "\n".join(
                    [member.display_name for member in inactive_members]
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


async def setup_hook():
    """Bot のセットアップ時に Cog を登録"""
    await bot.add_cog(InactivityManager(bot))


# Bot にセットアップフックを登録
bot.setup_hook = setup_hook

bot.run(TOKEN)
