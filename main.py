import discord
from discord.ext import commands
import os
import traceback
import json

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents, reconnect=True)

TOKEN = os.getenv('DISCORD_TOKEN')
INTRO_CHANNEL_ID = None
SECRET_ROLE_NAME = None
introductions = {}

# 設定ファイルから情報を読み込む
def load_settings():
    global INTRO_CHANNEL_ID, SECRET_ROLE_NAME
    try:
        with open("settings.json", "r") as file:
            settings = json.load(file)
            INTRO_CHANNEL_ID = settings.get("INTRO_CHANNEL_ID")
            SECRET_ROLE_NAME = settings.get("SECRET_ROLE_NAME")
    except FileNotFoundError:
        print("settings.json が見つかりません。設定を保存してください。")

# 設定ファイルに情報を保存する
def save_settings():
    settings = {
        "INTRO_CHANNEL_ID": INTRO_CHANNEL_ID,
        "SECRET_ROLE_NAME": SECRET_ROLE_NAME
    }
    with open("settings.json", "w") as file:
        json.dump(settings, file)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    load_settings()
    try:
        synced = await bot.tree.sync()  
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.event
async def on_voice_state_update(member, before, after):
    try:
        if member.bot or before.channel == after.channel:
            return

        if any(role.name == SECRET_ROLE_NAME for role in member.roles):
            return

        intro_channel = bot.get_channel(INTRO_CHANNEL_ID)

        if after.channel and before.channel is None:
            intro_text = await fetch_introduction(member, intro_channel)
            if after.channel.id not in introductions:
                introductions[after.channel.id] = {}
            introductions[after.channel.id][member.id] = intro_text
            await update_introduction_messages(after.channel)

        elif before.channel and after.channel is None:
            if before.channel.id in introductions and member.id in introductions[before.channel.id]:
                del introductions[before.channel.id][member.id]
            await update_introduction_messages(before.channel)

        elif before.channel and after.channel:
            if before.channel.id in introductions and member.id in introductions[before.channel.id]:
                del introductions[before.channel.id][member.id]
            intro_text = await fetch_introduction(member, intro_channel)
            if after.channel.id not in introductions:
                introductions[after.channel.id] = {}
            introductions[after.channel.id][member.id] = intro_text
            await update_introduction_messages(before.channel)
            await update_introduction_messages(after.channel)

    except Exception as e:
        print(f"Error in on_voice_state_update: {e}")
        traceback.print_exc()

async def fetch_introduction(member, intro_channel):
    async for message in intro_channel.history(limit=500):
        if message.author == member:
            return message.content
    return "自己紹介が見つかりませんでした。"

async def update_introduction_messages(channel):
    await channel.purge(limit=100, check=lambda m: m.author == bot.user)
    if channel.id not in introductions:
        return

    for user_id, intro_text in introductions[channel.id].items():
        user = bot.get_user(user_id)
        if user and channel.guild.get_member(user.id).voice.channel == channel:
            embed = discord.Embed(title=f"{user.display_name}の自己紹介", color=discord.Color.blue())
            embed.add_field(name="自己紹介", value=intro_text, inline=False)
            embed.set_thumbnail(url=user.avatar.url)
            await channel.send(embed=embed)

# スラッシュコマンドでINTRO_CHANNEL_IDとSECRET_ROLE_NAMEを設定
@bot.tree.command(name="設定", description="自己紹介チャンネルIDと秘密のロール名を設定します")
async def set_config(interaction: discord.Interaction, intro_channel_id: str, secret_role_name: str):
    global INTRO_CHANNEL_ID, SECRET_ROLE_NAME
    try:
        INTRO_CHANNEL_ID = int(intro_channel_id)
        SECRET_ROLE_NAME = secret_role_name
        save_settings()
        await interaction.response.send_message("設定が保存されました。", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("無効なIDが入力されました。", ephemeral=True)

bot.run(TOKEN)
