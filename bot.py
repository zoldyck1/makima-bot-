import discord
from discord.ext import commands, tasks
import json
import asyncio
from datetime import datetime, timedelta
import aiohttp
from PIL import Image, ImageDraw, ImageFont
import io
import os
from dotenv import load_dotenv

load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

# XP configuration
CHAT_XP_MIN = 15
CHAT_XP_MAX = 25
VC_XP_PER_MINUTE = 10
XP_COOLDOWN = 60  # seconds

# Data storage
user_data = {}
voice_sessions = {}

def load_data():
    global user_data
    try:
        with open('user_data.json', 'r') as f:
            user_data = json.load(f)
    except FileNotFoundError:
        user_data = {}

def save_data():
    with open('user_data.json', 'w') as f:
        json.dump(user_data, f, indent=2)

def get_user_data(user_id):
    user_id = str(user_id)
    if user_id not in user_data:
        user_data[user_id] = {
            'chat_xp': 0,
            'vc_xp': 0,
            'total_xp': 0,
            'level': 1,
            'last_message': 0
        }
    return user_data[user_id]

def calculate_level(xp):
    return int((xp / 100) ** 0.5) + 1

def xp_for_next_level(level):
    return (level ** 2) * 100

async def create_rank_card(user, user_stats):
    # Download user avatar
    async with aiohttp.ClientSession() as session:
        async with session.get(str(user.display_avatar.url)) as resp:
            avatar_data = await resp.read()
    
    # Create card with modern design
    width, height = 900, 350
    card = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    
    # Keep original background unchanged
    try:
        background = Image.open('background.jpg').convert('RGBA')
        background = background.resize((width, height))
        card.paste(background, (0, 0))
        
        # Add dark overlay for better text readability
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 120))
        card = Image.alpha_composite(card, overlay)
    except:
        # Original gradient background
        for y in range(height):
            r = int(25 + (y / height) * 30)
            g = int(25 + (y / height) * 20)
            b = int(50 + (y / height) * 40)
            for x in range(width):
                card.putpixel((x, y), (r, g, b, 255))
    
    # Load and process avatar with neon glow
    avatar = Image.open(io.BytesIO(avatar_data)).convert('RGBA')
    avatar = avatar.resize((120, 120))
    
    # Create circular mask
    mask = Image.new('L', (120, 120), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, 120, 120), fill=255)
    
    # Create neon glow border
    glow_size = 5
    glow_avatar = Image.new('RGBA', (120 + glow_size * 2, 120 + glow_size * 2), (0, 255, 255, 180))
    glow_mask = Image.new('L', (120 + glow_size * 2, 120 + glow_size * 2), 0)
    draw_glow = ImageDraw.Draw(glow_mask)
    draw_glow.ellipse((0, 0, 120 + glow_size * 2, 120 + glow_size * 2), fill=255)
    
    # Apply masks
    avatar.putalpha(mask)
    glow_avatar.putalpha(glow_mask)
    
    # Paste avatar with glow
    card.paste(glow_avatar, (40, 40), glow_avatar)
    card.paste(avatar, (40 + glow_size, 40 + glow_size), avatar)
    
    draw = ImageDraw.Draw(card)
    
    # Load fonts
    try:
        font_username = ImageFont.truetype("arial.ttf", 72)  # 150% larger
        font_handle = ImageFont.truetype("arial.ttf", 36)    # 50% of username
        font_label = ImageFont.truetype("arial.ttf", 42)     # 60% of username
        font_xp = ImageFont.truetype("arial.ttf", 30)        # 42% of username
    except:
        font_username = ImageFont.load_default()
        font_handle = ImageFont.load_default()
        font_label = ImageFont.load_default()
        font_xp = ImageFont.load_default()
    
    # Username - top-left next to avatar, bold white
    username_x = 180
    draw.text((username_x, 50), user.display_name.upper(), fill=(255, 255, 255), font=font_username)
    
    # User handle (optional)
    draw.text((username_x, 110), f"#{user.discriminator}" if user.discriminator != '0' else f"@{user.name}", 
              fill=(200, 200, 200, 200), font=font_handle)
    
    # Level text
    level_text = f"LEVEL {user_stats['level']}"
    draw.text((username_x, 140), level_text, fill=(255, 215, 0), font=font_label)
    
    # Progress bars setup
    bar_width = int(width * 0.75)  # 75% of card width
    bar_height = 20
    bar_x = username_x
    
    # TEXT XP Progress Bar
    text_y = 190
    draw.text((bar_x, text_y - 25), "TEXT XP", fill=(100, 200, 255), font=font_label)
    
    # Background bar
    draw.rounded_rectangle([bar_x, text_y, bar_x + bar_width, text_y + bar_height], 
                          radius=bar_height//2, fill=(40, 40, 50))
    
    # Progress fill - blue gradient
    chat_progress = min(user_stats['chat_xp'] / max(1000, user_stats['chat_xp']), 1.0)
    progress_width = int(chat_progress * bar_width)
    if progress_width > 0:
        for i in range(progress_width):
            intensity = i / bar_width
            color = (int(50 + intensity * 100), int(150 + intensity * 100), 255)
            draw.rectangle([bar_x + i, text_y, bar_x + i + 1, text_y + bar_height], fill=color)
    
    # XP text
    draw.text((bar_x, text_y + 25), f"{user_stats['chat_xp']:,} XP", fill=(180, 180, 180), font=font_xp)
    
    # VOICE XP Progress Bar
    voice_y = 250
    draw.text((bar_x, voice_y - 25), "VOICE XP", fill=(255, 100, 200), font=font_label)
    
    # Background bar
    draw.rounded_rectangle([bar_x, voice_y, bar_x + bar_width, voice_y + bar_height], 
                          radius=bar_height//2, fill=(40, 40, 50))
    
    # Progress fill - purple gradient
    voice_progress = min(user_stats['vc_xp'] / max(1000, user_stats['vc_xp']), 1.0)
    progress_width = int(voice_progress * bar_width)
    if progress_width > 0:
        for i in range(progress_width):
            intensity = i / bar_width
            color = (int(150 + intensity * 100), int(50 + intensity * 100), 255)
            draw.rectangle([bar_x + i, voice_y, bar_x + i + 1, voice_y + bar_height], fill=color)
    
    # XP text
    draw.text((bar_x, voice_y + 25), f"{user_stats['vc_xp']:,} XP", fill=(180, 180, 180), font=font_xp)
    
    # Total XP at bottom right
    total_text = f"TOTAL: {user_stats['total_xp']:,} XP"
    draw.text((width - 200, height - 40), total_text, fill=(255, 215, 0), font=font_label)
    
    # Save to bytes
    img_bytes = io.BytesIO()
    card.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    load_data()
    voice_xp_tracker.start()
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Failed to sync commands: {e}')

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Move command with 'aji @user' or 'aji userid'
    if message.content.lower().startswith('aji'):
        if not message.author.guild_permissions.move_members:
            await message.channel.send("❌ You don't have permission to move members!")
            return
        
        if not message.author.voice or not message.author.voice.channel:
            await message.channel.send("❌ You must be in a voice channel to use this command!")
            return
        
        parts = message.content.split()
        if len(parts) >= 2:
            # Try to get member from mention or ID
            member = None
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
            
            try:
                await member.move_to(message.author.voice.channel)
                await message.channel.send(f"✅ Moved {member.mention} to {message.author.voice.channel.mention}")
            except discord.Forbidden:
                await message.channel.send("❌ I don't have permission to move members!")
            except Exception as e:
                await message.channel.send(f"❌ Error: {str(e)}")
        return
    
    # Quick rank command with 'r' or 'r @user' or 'r userid'
    if message.content.lower().startswith('r'):
        parts = message.content.split()
        if len(parts) == 1 and parts[0].lower() == 'r':
            # Just 'r' - show own rank
            target_user = message.author
        elif len(parts) == 2:
            # 'r @user' or 'r userid'
            if message.mentions:
                target_user = message.mentions[0]
            else:
                try:
                    user_id = int(parts[1])
                    target_user = bot.get_user(user_id) or await bot.fetch_user(user_id)
                except:
                    return  # Invalid user ID, ignore
        else:
            return  # Invalid format, ignore
        
        user_stats = get_user_data(target_user.id)
        try:
            card_image = await create_rank_card(target_user, user_stats)
            file = discord.File(card_image, filename='rank_card.png')
            await message.channel.send(file=file)
        except Exception as e:
            embed = discord.Embed(title=f"{target_user.display_name}'s Rank", color=0x00ff00)
            embed.add_field(name="Level", value=user_stats['level'], inline=True)
            embed.add_field(name="Total XP", value=f"{user_stats['total_xp']:,}", inline=True)
            embed.add_field(name="Chat XP", value=f"{user_stats['chat_xp']:,}", inline=True)
            embed.add_field(name="Voice XP", value=f"{user_stats['vc_xp']:,}", inline=True)
            embed.set_thumbnail(url=target_user.display_avatar.url)
            await message.channel.send(embed=embed)
        return
    
    user_stats = get_user_data(message.author.id)
    current_time = datetime.now().timestamp()
    
    # Check cooldown
    if current_time - user_stats['last_message'] >= XP_COOLDOWN:
        import random
        xp_gain = random.randint(CHAT_XP_MIN, CHAT_XP_MAX)
        user_stats['chat_xp'] += xp_gain
        user_stats['total_xp'] = user_stats['chat_xp'] + user_stats['vc_xp']
        
        old_level = user_stats['level']
        user_stats['level'] = calculate_level(user_stats['total_xp'])
        user_stats['last_message'] = current_time
        
        # Level up notification
        if user_stats['level'] > old_level:
            embed = discord.Embed(
                title="🎉 Level Up!",
                description=f"{message.author.mention} reached level {user_stats['level']}!",
                color=0xFFD700
            )
            await message.channel.send(embed=embed)
        
        save_data()
    
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return
    
    user_id = str(member.id)
    current_time = datetime.now()
    
    # User joined a voice channel
    if before.channel is None and after.channel is not None:
        voice_sessions[user_id] = current_time
    
    # User left a voice channel
    elif before.channel is not None and after.channel is None:
        if user_id in voice_sessions:
            session_duration = (current_time - voice_sessions[user_id]).total_seconds() / 60
            if session_duration >= 1:  # Minimum 1 minute
                user_stats = get_user_data(member.id)
                xp_gain = int(session_duration * VC_XP_PER_MINUTE)
                user_stats['vc_xp'] += xp_gain
                user_stats['total_xp'] = user_stats['chat_xp'] + user_stats['vc_xp']
                
                old_level = user_stats['level']
                user_stats['level'] = calculate_level(user_stats['total_xp'])
                
                if user_stats['level'] > old_level:
                    # Find a text channel to send level up message
                    for channel in member.guild.text_channels:
                        if channel.permissions_for(member.guild.me).send_messages:
                            embed = discord.Embed(
                                title="🎉 Level Up!",
                                description=f"{member.mention} reached level {user_stats['level']}!",
                                color=0xFFD700
                            )
                            await channel.send(embed=embed)
                            break
                
                save_data()
            
            del voice_sessions[user_id]

@tasks.loop(minutes=1)
async def voice_xp_tracker():
    current_time = datetime.now()
    for user_id, join_time in list(voice_sessions.items()):
        # Give XP for every minute in voice
        if (current_time - join_time).total_seconds() >= 60:
            try:
                user = bot.get_user(int(user_id))
                if user:
                    user_stats = get_user_data(int(user_id))
                    user_stats['vc_xp'] += VC_XP_PER_MINUTE
                    user_stats['total_xp'] = user_stats['chat_xp'] + user_stats['vc_xp']
                    
                    old_level = user_stats['level']
                    user_stats['level'] = calculate_level(user_stats['total_xp'])
                    
                    voice_sessions[user_id] = current_time
                    save_data()
            except:
                continue

@bot.hybrid_command(name='rank')
async def rank_command(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    
    user_stats = get_user_data(member.id)
    
    try:
        card_image = await create_rank_card(member, user_stats)
        file = discord.File(card_image, filename='rank_card.png')
        await ctx.send(file=file)
    except Exception as e:
        # Fallback to text-based rank
        embed = discord.Embed(title=f"{member.display_name}'s Rank", color=0x00ff00)
        embed.add_field(name="Level", value=user_stats['level'], inline=True)
        embed.add_field(name="Total XP", value=f"{user_stats['total_xp']:,}", inline=True)
        embed.add_field(name="Chat XP", value=f"{user_stats['chat_xp']:,}", inline=True)
        embed.add_field(name="Voice XP", value=f"{user_stats['vc_xp']:,}", inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

@bot.hybrid_command(name='leaderboard', aliases=['lb'])
async def leaderboard_command(ctx):
    # Sort users by total XP
    sorted_users = sorted(user_data.items(), key=lambda x: x[1]['total_xp'], reverse=True)[:10]
    
    embed = discord.Embed(title="🏆 XP Leaderboard", color=0xFFD700)
    
    for i, (user_id, stats) in enumerate(sorted_users, 1):
        user = bot.get_user(int(user_id))
        if user:
            embed.add_field(
                name=f"{i}. {user.display_name}",
                value=f"Level {stats['level']} • {stats['total_xp']:,} XP",
                inline=False
            )
    
    await ctx.send(embed=embed)

@bot.hybrid_command(name='move')
@commands.has_permissions(move_members=True)
async def move_command(ctx, member: discord.Member, channel: discord.VoiceChannel):
    if not member.voice:
        await ctx.send(f"❌ {member.mention} is not in a voice channel!")
        return
    
    try:
        await member.move_to(channel)
        await ctx.send(f"✅ Moved {member.mention} to {channel.mention}")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to move members!")
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

# Run the bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("ERROR: DISCORD_TOKEN environment variable not set!")
        exit(1)
    bot.run(token)