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
    
    # Check for blocked words
    blocked_words = ['w9', 'zb', '9hba', 'qhba', 'w10', 'zbi', '9lawi', 'qlawi', 'terma', 'zok', 'zebi', 'wld9hba']
    for word in blocked_words:
        if word in message.content.lower():
            await message.channel.send("matkhssrch lhdra a wld 9hba")
            break
    
    if message.content.lower().startswith('aji '):
        if not message.author.guild_permissions.move_members:
            await message.channel.send("❌ You don't have permission to move members!")
            return
        
        parts = message.content.split()
        if len(parts) >= 2:
            # Get first user (to be moved)
            member_to_move = None
            if message.mentions and len(message.mentions) >= 1:
                member_to_move = message.mentions[0]
            else:
                try:
                    user_id = int(parts[1])
                    member_to_move = message.guild.get_member(user_id)
                except ValueError:
                    pass
            
            if not member_to_move:
                await message.channel.send("❌ User not found!")
                return
            
            if not member_to_move.voice:
                await message.channel.send(f"❌ {member_to_move.mention} is not in a voice channel!")
                return
            
            # If only one parameter, move to command author's channel
            if len(parts) == 2:
                if not message.author.voice or not message.author.voice.channel:
                    await message.channel.send("❌ You must be in a voice channel!")
                    return
                
                try:
                    await member_to_move.move_to(message.author.voice.channel)
                    await message.channel.send(f"✅ Moved {member_to_move.mention} to {message.author.voice.channel.mention}")
                except discord.Forbidden:
                    await message.channel.send("❌ I don't have permission to move members!")
                except Exception as e:
                    await message.channel.send(f"❌ Error: {str(e)}")
                return
            
            # Get destination (second user or channel name)
            destination_channel = None
            
            # Check if second parameter is a mentioned user
            if len(message.mentions) >= 2:
                target_user = message.mentions[1]
                if target_user.voice and target_user.voice.channel:
                    destination_channel = target_user.voice.channel
                else:
                    await message.channel.send(f"❌ {target_user.mention} is not in a voice channel!")
                    return
            else:
                # Try to find user by ID or channel by name
                try:
                    user_id = int(parts[2])
                    target_user = message.guild.get_member(user_id)
                    if target_user and target_user.voice and target_user.voice.channel:
                        destination_channel = target_user.voice.channel
                    else:
                        await message.channel.send(f"❌ User with ID {user_id} not found or not in voice channel!")
                        return
                except ValueError:
                    # Not a user ID, try channel name
                    channel_name = ' '.join(parts[2:])
                    for channel in message.guild.voice_channels:
                        if channel.name.lower() == channel_name.lower():
                            destination_channel = channel
                            break
                    
                    if not destination_channel:
                        await message.channel.send(f"❌ Voice channel '{channel_name}' not found!")
                        return
            
            # Move the user
            try:
                await member_to_move.move_to(destination_channel)
                await message.channel.send(f"✅ Moved {member_to_move.mention} to {destination_channel.mention}")
            except discord.Forbidden:
                await message.channel.send("❌ I don't have permission to move members!")
            except Exception as e:
                await message.channel.send(f"❌ Error: {str(e)}")
        else:
            await message.channel.send("❌ Usage: `aji @user` or `aji @user1 @user2` or `aji userID1 userID2` or `aji @user channelname`")
    
    await bot.process_commands(message)

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("ERROR: DISCORD_TOKEN not set!")
        exit(1)
    bot.run(token)