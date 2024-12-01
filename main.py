import discord
from discord.ext import commands
import logging

# ログの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Botのトークン
TOKEN = "YOUR_BOT_TOKEN"

# intents設定
intents = discord.Intents.default()
intents.message_content = True  # 必要な場合のみ有効化

# Botのインスタンス作成
bot = commands.Bot(command_prefix="!", intents=intents)

# スラッシュコマンド
@bot.tree.command(name="get_inactivity_days", description="非活動期間を取得します")
async def get_inactivity_days(interaction: discord.Interaction):
    """非活動期間を取得するスラッシュコマンド"""
    await interaction.response.send_message("非活動期間を確認します！")

# Bot準備完了時の処理
@bot.event
async def on_ready():
    """Bot の準備完了時の処理"""
    logger.info("Bot is ready")
    logger.info(f"Connected to the following guilds: {[guild.name for guild in bot.guilds]}")

    # スラッシュコマンドを同期
    try:
        # 全てのギルドに対して個別に同期
        for guild in bot.guilds:
            synced = await bot.tree.sync(guild=guild)
            logger.info(f"スラッシュコマンドが {len(synced)} 個同期されました (ギルド: {guild.name})")
    except discord.errors.Forbidden:
        logger.error("スラッシュコマンドを同期する権限がありません。")
    except Exception as e:
        logger.error(f"スラッシュコマンドの同期中にエラーが発生しました: {e}")

# Botを実行
bot.run(TOKEN)
