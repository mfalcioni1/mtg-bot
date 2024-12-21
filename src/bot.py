import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

# Intents are required to manage certain events
intents = discord.Intents.default()
intents.messages = True  # Enables message-related events

# Load environment variables from .env file
load_dotenv()

# Create a bot instance
bot = commands.Bot(command_prefix=commands.when_mentioned_or("\drafty"), intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

# Run the bot with token from .env
bot.run(os.getenv('DISCORD_BOT_TOKEN'))
