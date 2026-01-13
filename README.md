# Discord XP Bot

A professional Discord bot that tracks voice channel and chat XP with beautiful rank cards.

## Features

- **Chat XP**: Earn 15-25 XP per message (60-second cooldown)
- **Voice XP**: Earn 10 XP per minute in voice channels
- **Professional Rank Cards**: Custom-generated cards with user avatar and stats
- **Leaderboard**: View top 10 users by XP
- **Level System**: Automatic level calculation and notifications

## Commands

- `!rank [@user]` - Show rank card for yourself or mentioned user
- `!leaderboard` or `!lb` - Display XP leaderboard

## Setup

1. Create a Discord application at https://discord.com/developers/applications
2. Create a bot and copy the token
3. Replace `YOUR_BOT_TOKEN` in `bot.py` with your actual token
4. Install dependencies: `pip install -r requirements.txt`
5. Run the bot: `python bot.py`

## Discloud Hosting

1. Zip all files (bot.py, requirements.txt, discloud.config)
2. Upload to Discloud
3. Set your bot token in environment variables
4. Deploy!

## Bot Permissions Required

- Send Messages
- Read Message History
- Connect to Voice Channels
- Use Slash Commands
- Attach Files