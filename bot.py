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
    
    # Clear command
    if message.content.lower().startswith('clear'):
        if not message.author.guild_permissions.manage_messages:
            await message.channel.send("❌ You don't have permission to manage messages!")
            return
        
        parts = message.content.split()
        amount = 10
        if len(parts) >= 2:
            try:
                amount = int(parts[1])
                if amount > 100:
                    amount = 100
            except:
                amount = 10
        
        try:
            deleted = await message.channel.purge(limit=amount + 1)
            msg = await message.channel.send(f"✅ Deleted {len(deleted) - 1} messages")
            await msg.delete(delay=3)
        except discord.Forbidden:
            await message.channel.send("❌ I don't have permission to delete messages!")
        except Exception as e:
            await message.channel.send(f"❌ Error: {str(e)}")
        return
    
    if message.content.lower().startswith('aji '):
        if not message.author.guild_permissions.move_members:
            await message.channel.send("❌ You don't have permission to move members!")
            return
        
        parts = message.content.split()
        if len(parts) >= 2:
            member = None
            target_channel = None
            
            # Get first member
            if message.mentions:
                member = message.mentions[0]
            else:
                try:
                    user_id = int(parts[1])
                    member = message.guild.get_member(user_id)
                except:
                    pass
            
            if not member:
                await message.channel.send("❌ User not found!")
                return
            
            if not member.voice:
                await message.channel.send(f"❌ {member.mention} is not in a voice channel!")
                return
            
            # Check if second parameter exists
            if len(parts) >= 3:
                # Try second user by mention
                if len(message.mentions) >= 2:
                    target_user = message.mentions[1]
                    if target_user.voice and target_user.voice.channel:
                        target_channel = target_user.voice.channel
                    else:
                        await message.channel.send(f"❌ {target_user.mention} is not in a voice channel!")
                        return
                else:
                    # Try second user by ID
                    try:
                        user_id2 = int(parts[2])
                        target_user = message.guild.get_member(user_id2)
                        if target_user:
                            if target_user.voice and target_user.voice.channel:
                                target_channel = target_user.voice.channel
                            else:
                                await message.channel.send(f"❌ <@{user_id2}> is not in a voice channel!")
                                return
                        else:
                            await message.channel.send(f"❌ User with ID {user_id2} not found!")
                            return
                    except:
                        # Try channel by name
                        channel_name = ' '.join(parts[2:])
                        for vc in message.guild.voice_channels:
                            if vc.name.lower() == channel_name.lower():
                                target_channel = vc
                                break
                        if not target_channel:
                            await message.channel.send(f"❌ Channel '{channel_name}' not found!")
                            return
            
            # If no target specified, use author's channel
            if not target_channel:
                if not message.author.voice or not message.author.voice.channel:
                    await message.channel.send("❌ You must be in a voice channel!")
                    return
                target_channel = message.author.voice.channel
            
            try:
                await member.move_to(target_channel)
                await message.channel.send(f"✅ Moved {member.mention} to {target_channel.mention}")
            except discord.Forbidden:
                await message.channel.send("❌ I don't have permission to move members!")
            except Exception as e:
                await message.channel.send(f"❌ Error: {str(e)}")
        return
    
    await bot.process_commands(message)

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("ERROR: DISCORD_TOKEN not set!")
        exit(1)
    bot.run(token)
