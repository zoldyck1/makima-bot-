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
    width, height = 1000, 300
    card = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    
    # Keep original background unchanged
    try:
        background = Image.open('background.jpg').convert('RGBA')
        background = background.resize((width, height))
        card.paste(background, (0, 0))
        
        # Add dark overlay for better text readability
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 140))
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
    avatar = avatar.resize((160, 160))
    
    # Create circular mask
    mask = Image.new('L', (160, 160), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, 160, 160), fill=255)
    
    # Create neon glow border
    glow_size = 6
    glow_avatar = Image.new('RGBA', (160 + glow_size * 2, 160 + glow_size * 2), (0, 255, 255, 200))
    glow_mask = Image.new('L', (160 + glow_size * 2, 160 + glow_size * 2), 0)
    draw_glow = ImageDraw.Draw(glow_mask)
    draw_glow.ellipse((0, 0, 160 + glow_size * 2, 160 + glow_size * 2), fill=255)
    
    # Apply masks
    avatar.putalpha(mask)
    glow_avatar.putalpha(glow_mask)
    
    # Paste avatar with glow - centered vertically
    avatar_y = (height - 160) // 2 - 10
    card.paste(glow_avatar, (30, avatar_y), glow_avatar)
    card.paste(avatar, (30 + glow_size, avatar_y + glow_size), avatar)
    
    draw = ImageDraw.Draw(card)
    
    # Load fonts
    try:
        font_username = ImageFont.truetype("arialbd.ttf", 56)  # Bold, very large
        font_level = ImageFont.truetype("arialbd.ttf", 38)     # Bold level
        font_label = ImageFont.truetype("arial.ttf", 28)       # Labels
        font_xp = ImageFont.truetype("arial.ttf", 24)          # XP numbers
    except:
        try:
            font_username = ImageFont.truetype("arial.ttf", 56)
            font_level = ImageFont.truetype("arial.ttf", 38)
            font_label = ImageFont.truetype("arial.ttf", 28)
            font_xp = ImageFont.truetype("arial.ttf", 24)
        except:
            font_username = ImageFont.load_default()
            font_level = ImageFont.load_default()
            font_label = ImageFont.load_default()
            font_xp = ImageFont.load_default()
    
    # Username - very large and bold
    username_x = 230
    draw.text((username_x, 35), user.display_name.upper(), fill=(255, 255, 255), font=font_username)
    
    # Level badge with background
    level_y = 95
    level_text = f"LEVEL {user_stats['level']}"
    level_bbox = draw.textbbox((0, 0), level_text, font=font_level)
    level_width = level_bbox[2] - level_bbox[0]
    
    # Level badge background
    draw.rounded_rectangle(
        [username_x - 5, level_y - 5, username_x + level_width + 15, level_y + 40],
        radius=8,
        fill=(255, 215, 0, 50),
        outline=(255, 215, 0, 255),
        width=2
    )
    draw.text((username_x + 5, level_y), level_text, fill=(255, 215, 0), font=font_level)
    
    # Progress bars setup
    bar_width = 720
    bar_height = 28
    bar_x = username_x
    
    # TEXT XP Progress Bar
    text_y = 160
    draw.text((bar_x, text_y - 30), "TEXT XP", fill=(100, 200, 255), font=font_label)
    
    # Background bar with border
    draw.rounded_rectangle(
        [bar_x, text_y, bar_x + bar_width, text_y + bar_height],
        radius=bar_height // 2,
        fill=(30, 30, 40),
        outline=(60, 60, 70),
        width=2
    )
    
    # Progress fill - blue gradient
    chat_max = max(user_stats['chat_xp'], 1000)
    chat_progress = min(user_stats['chat_xp'] / chat_max, 1.0)
    progress_width = int(chat_progress * (bar_width - 4))
    if progress_width > 10:
        for i in range(progress_width):
            intensity = i / bar_width
            color = (int(30 + intensity * 120), int(120 + intensity * 135), 255)
            draw.rectangle([bar_x + 2 + i, text_y + 2, bar_x + 3 + i, text_y + bar_height - 2], fill=color)
    
    # XP text on bar
    xp_text = f"{user_stats['chat_xp']:,} XP"
    draw.text((bar_x + 15, text_y + 4), xp_text, fill=(255, 255, 255), font=font_xp)
    
    # VOICE XP Progress Bar
    voice_y = 230
    draw.text((bar_x, voice_y - 30), "VOICE XP", fill=(255, 100, 200), font=font_label)
    
    # Background bar with border
    draw.rounded_rectangle(
        [bar_x, voice_y, bar_x + bar_width, voice_y + bar_height],
        radius=bar_height // 2,
        fill=(30, 30, 40),
        outline=(60, 60, 70),
        width=2
    )
    
    # Progress fill - purple gradient
    voice_max = max(user_stats['vc_xp'], 1000)
    voice_progress = min(user_stats['vc_xp'] / voice_max, 1.0)
    progress_width = int(voice_progress * (bar_width - 4))
    if progress_width > 10:
        for i in range(progress_width):
            intensity = i / bar_width
            color = (int(180 + intensity * 75), int(30 + intensity * 70), 255)
            draw.rectangle([bar_x + 2 + i, voice_y + 2, bar_x + 3 + i, voice_y + bar_height - 2], fill=color)
    
    # XP text on bar
    xp_text = f"{user_stats['vc_xp']:,} XP"
    draw.text((bar_x + 15, voice_y + 4), xp_text, fill=(255, 255, 255), font=font_xp)
    
    # Total XP badge - top right
    total_text = f"TOTAL: {user_stats['total_xp']:,} XP"
    total_bbox = draw.textbbox((0, 0), total_text, font=font_label)
    total_width = total_bbox[2] - total_bbox[0]
    total_x = width - total_width - 40
    
    draw.rounded_rectangle(
        [total_x - 10, 35, width - 30, 70],
        radius=8,
        fill=(40, 40, 50, 200),
        outline=(255, 215, 0, 255),
        width=2
    )
    draw.text((total_x, 40), total_text, fill=(255, 215, 0), font=font_label)
    
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

# Run the bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("ERROR: DISCORD_TOKEN environment variable not set!")
        exit(1)
    bot.run(token)