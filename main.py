import os
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import json

# ボットの初期設定
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, reconnect=True)

# 環境変数とグローバル設定
TOKEN = os.getenv('DISCORD_TOKEN')
DEFAULT_INACTIVITY_DAYS = 30
inactivity_days = DEFAULT_INACTIVITY_DAYS

# 設定ファイルの読み書き
def load_settings():
    global inactivity_days
    try:
        with open("settings.json", "r") as file:
            settings = json.load(file)
            inactivity_days = settings.get("INACTIVITY_DAYS", DEFAULT_INACTIVITY_DAYS)
    except FileNotFoundError:
        print("settings.json が見つかりません。設定を保存してください。")

def save_settings():
    settings = {
        "INACTIVITY_DAYS": inactivity_days
    }
    with open("settings.json", "w") as file:
        json.dump(settings, file)

# ボット起動時の処理
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    load_settings()
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# 非活動メンバー管理クラス
class InactivityManager(commands.Cog):
    """非活動メンバーを管理するコグ"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set_inactivity_days", description="非活動日数を設定します")
    async def set_inactivity_days(self, interaction: discord.Interaction, days: int):
        """非活動日数を設定するスラッシュコマンド"""
        global inactivity_days
        inactivity_days = days
        save_settings()
        await interaction.response.send_message(f"非活動日数を {days} 日に設定しました！", ephemeral=True)

    @app_commands.command(name="get_inactivity_days", description="現在の非活動日数を確認します")
    async def get_inactivity_days(self, interaction: discord.Interaction):
        """現在の非活動日数を確認するスラッシュコマンド"""
        await interaction.response.send_message(f"現在の非活動日数は {inactivity_days} 日です。", ephemeral=True)

    @app_commands.command(name="check_inactive_members", description="非活動メンバーを確認します")
    async def check_inactive_members(self, interaction: discord.Interaction):
        """非活動メンバーを確認するスラッシュコマンド"""
        guild = interaction.guild
        now = datetime.utcnow()
        inactive_threshold = now - timedelta(days=inactivity_days)
        inactive_members = []

        for member in guild.members:
            if member.bot:
                continue

            last_message_time = await self.get_last_message_time(member, guild)
            if last_message_time is None or last_message_time < inactive_threshold:
                inactive_members.append(member)

        if inactive_members:
            message = "以下のメンバーが非活動です:\n" + "\n".join([f"{member.name}#{member.discriminator}" for member in inactive_members])
        else:
            message = "非活動のメンバーはいません。"
        await interaction.response.send_message(message)

    @staticmethod
    async def get_last_message_time(member: discord.Member, guild: discord.Guild):
        """メンバーの最後のメッセージ時刻を取得"""
        for channel in guild.text_channels:
            try:
                async for message in channel.history(limit=1000):
                    if message.author == member:
                        return message.created_at
            except discord.Forbidden:
                continue
        return None

# Cogの登録
async def setup_hook():
    await bot.add_cog(InactivityManager(bot))

bot.setup_hook = setup_hook

# ボットを実行
bot.run(TOKEN)
