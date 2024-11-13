import os
import discord
import asyncio
from discord.ext import commands, tasks
from datetime import datetime, timedelta

# 環境変数からトークンを取得
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True  # ボイスチャンネルのイベントを取得するために必要

bot = commands.Bot(command_prefix="!", intents=intents)

# 最終活動記録用の辞書
last_active = {}

# 低浮上と判定するまでの日数
inactive_days = 30

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    check_inactivity.start()  # タスクの開始

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    # メッセージが送られたら最終活動日時を記録
    last_active[message.author.id] = datetime.now()
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    """ボイスチャンネルへの入退室を監視"""
    if member.bot:
        return
    
    # ボイスチャンネルに参加した場合
    if after.channel is not None:
        last_active[member.id] = datetime.now()
    
    # ボイスチャンネルから退出した場合
    elif before.channel is not None:
        last_active[member.id] = datetime.now()

@tasks.loop(hours=24)  # 24時間ごとにチェック
async def check_inactivity():
    now = datetime.now()
    for member in bot.get_all_members():
        if member.bot:
            continue
        last_seen = last_active.get(member.id, None)
        if last_seen and (now - last_seen).days >= inactive_days:
            try:
                await member.send(f"{member.name}さん、しばらくサーバーで活動がないようです。またの参加をお待ちしています！")
            except discord.Forbidden:
                print(f"Cannot send DM to {member.name}")

# Botの起動
if TOKEN:
    bot.run(TOKEN)
else:
    print("DISCORD_TOKEN環境変数が設定されていません。")
