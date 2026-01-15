import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if message.content.lower().startswith('w9') or message.content.lower().startswith('zb') or message.content.lower().startswith('9hba') or message.content.lower().startswith('qhba') or message.content.lower().startswith('w10') or message.content.lower().startswith('zbi') or message.content.lower().startswith('9lawi') or message.content.lower().startswith('qlawi') or message.content.lower().startswith('terma') or message.content.lower().startswith('zok') or message.content.lower().startswith('zebi') or message.content.lower().startswith('wld9hba'):
        await message.channel.send("matkhssrch lhdra a wld 9hba")
    
    if message.content.lower().startswith('aji '):
        if not message.author.guild_permissions.move_members:
            await message.channel.send("❌ You don't have permission to move members!")
            return
        
        if not message.author.voice or not message.author.voice.channel:
            await message.channel.send("❌ You must be in a voice channel!")
            return
        
        parts = message.content.split()
        if len(parts) >= 2:
            member = None
            if message.mentions:
                member = message.mentions[0]
            else:
                try:
                    user_id = int(parts[1])
                    member = message.guild.get_member(user_id)
                except ValueError:
                    # Invalid user ID format
                    pass
            
            if not member:
                await message.channel.send("❌ User not found!")
                return
            
            if not member.voice:
                await message.channel.send(f"❌ {member.mention} is not in a voice channel!")
                return
            
            try:
                await member.move_to(message.author.voice.channel)
                await message.channel.send(f"✅ Moved {member.mention} to {message.author.voice.channel.mention}")
            except discord.Forbidden:
                await message.channel.send("❌ I don't have permission to move members!")
            except Exception as e:
                await message.channel.send(f"❌ Error: {str(e)}")
    
    await bot.process_commands(message)

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("ERROR: DISCORD_TOKEN not set!")
        exit(1)
    bot.run(token)
