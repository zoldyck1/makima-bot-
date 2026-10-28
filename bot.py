import discord
from discord.ext import commands
import os
import re
import asyncio
import aiohttp
from urllib.parse import urlparse
from aiohttp import web
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

async def start_web():
    # Render web services need an open port; UptimeRobot pings it to keep the bot awake
    app = web.Application()
    app.router.add_get('/', lambda request: web.Response(text='ok'))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.getenv('PORT', 8080))).start()

bot.setup_hook = start_web

URL_RE = re.compile(r'https?://\S+')
GIF_HOSTS = ('tenor.com', 'giphy.com', 'klipy.com')

def is_gif(url):
    parsed = urlparse(url)
    host = parsed.hostname or ''
    return parsed.path.lower().endswith('.gif') or any(host == h or host.endswith('.' + h) for h in GIF_HOSTS)

async def check_url_virustotal(url):
    api_key = os.getenv('VT_API_KEY')
    if not api_key:
        return None
    headers = {'x-apikey': api_key}
    async with aiohttp.ClientSession(headers=headers) as session:
        # Submitting (not looking up by raw URL) works even when VT normalizes the URL differently
        async with session.post('https://www.virustotal.com/api/v3/urls', data={'url': url}) as resp:
            if resp.status != 200:
                return f"⚠️ VirusTotal error ({resp.status}) for `{url}`"
            analysis_id = (await resp.json())['data']['id']
        # Analysis id is "u-<url sha256>-<timestamp>": use VT's own URL id to get the last report instantly
        parts = analysis_id.split('-')
        if len(parts) == 3:
            async with session.get(f'https://www.virustotal.com/api/v3/urls/{parts[1]}') as resp:
                if resp.status == 200:
                    stats = (await resp.json())['data']['attributes'].get('last_analysis_stats')
                    if stats and sum(stats.values()):
                        return format_vt_result(url, stats)
        # Brand-new URL: wait for the fresh scan
        for delay in (5, 10, 15):
            await asyncio.sleep(delay)
            async with session.get(f'https://www.virustotal.com/api/v3/analyses/{analysis_id}') as resp:
                if resp.status != 200:
                    return f"⚠️ VirusTotal error ({resp.status}) for `{url}`"
                attrs = (await resp.json())['data']['attributes']
            if attrs['status'] == 'completed':
                stats = attrs['stats']
                break
        else:
            return f"⏳ `{url}` is still being scanned by VirusTotal, try again later."
    return format_vt_result(url, stats)

def format_vt_result(url, stats):
    bad = stats.get('malicious', 0) + stats.get('suspicious', 0)
    total = sum(stats.values())
    if bad:
        return f"🚨 `{url}` flagged by {bad}/{total} engines on VirusTotal. Don't open it!"
    return f"✅ `{url}` looks safe ({total} engines, 0 detections)."

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if message.content.lower() == 'b' or message.content.lower().startswith('b '):
        parts = message.content.split()
        user = None
        
        if len(parts) == 1:  # Just "b" command
            user = message.author
        elif len(parts) >= 2:
            if message.mentions:
                user = message.mentions[0]
            else:
                try:
                    user_id = int(parts[1])
                    user = bot.get_user(user_id)
                except ValueError:
                    pass
        
        if not user:
            await message.channel.send("❌ User not found!")
            return
        
        try:
            # Fetch full user to get banner
            full_user = await bot.fetch_user(user.id)
            if full_user.banner:
                banner_url = full_user.banner.url
                embed = discord.Embed(title=f"{full_user.display_name}'s Banner", color=0x2f3136)
                embed.set_image(url=banner_url)
                await message.channel.send(embed=embed)
            else:
                await message.channel.send(f"❌ {full_user.display_name} doesn't have a banner!")
        except Exception as e:
            await message.channel.send(f"❌ Error: {str(e)}")
    
    if message.content.lower() == 'clear' or message.content.lower().startswith('clear '):
        if not message.author.guild_permissions.manage_messages:
            await message.channel.send("❌ You don't have permission to delete messages!")
            return
        
        parts = message.content.split()
        amount = 5  # Default amount
        
        if len(parts) >= 2:
            try:
                amount = int(parts[1])
                if amount < 1 or amount > 100:
                    await message.channel.send("❌ Amount must be between 1 and 100!")
                    return
            except ValueError:
                await message.channel.send("❌ Invalid number!")
                return
        
        try:
            deleted = await message.channel.purge(limit=amount + 1)  # +1 to include the clear command
            await message.channel.send(f"✅ Deleted {len(deleted) - 1} messages!", delete_after=3)
        except discord.Forbidden:
            await message.channel.send("❌ I don't have permission to delete messages!")
        except Exception as e:
            await message.channel.send(f"❌ Error: {str(e)}")
    
    # shortcut: only the first link per message, to stay under VT free limit (4 req/min)
    link = URL_RE.search(message.content)
    if link and not is_gif(link.group(0).rstrip('>)')):
        try:
            result = await check_url_virustotal(link.group(0).rstrip('>)'))
            if result:
                await message.reply(result, mention_author=False)
        except Exception as e:
            await message.channel.send(f"❌ VirusTotal error: {str(e)}")

    blocked_words =['w9', 'zb', '9hba', 'qhba', 'w10', 'zbi', '9lawi', 'qlawi', 'terma', 'zok', 'zebi', 'wld9hba', 'zamel','tbon','tabon','khra']
    for word in blocked_words:
        if word in message.content.lower():
            await message.reply("matkhssrch lhdra a wld 9ahba!\nhttps://tenor.com/view/oh-no-oh-no-oh-hell-no-hell-gif-13947705")
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