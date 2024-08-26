import time
import re
import asyncio
import json
import os
import disnake
from disnake.ext import commands
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update

def get_config():
    config = {}

    config['BOT_TYPE'] = input("Choose bot type (telegram/discord): ").strip().lower()
    config['BOT_TOKEN'] = input("Enter bot token: ")

    if config['BOT_TYPE'] == 'telegram':
        config['CHAT_ID'] = input("Enter chat ID: ")
    elif config['BOT_TYPE'] == 'discord':
        config['CHANNEL_ID'] = input("Enter channel ID: ")
    else:
        print("Invalid bot type. Use 'telegram' or 'discord'.")
        exit()

    folder_path = input("Enter path to log folder: ")

    # Check if the path already contains 'latest.log'
    if not folder_path.endswith('latest.log'):
        config['LOG_FILE_PATH'] = os.path.join(folder_path, 'latest.log')
    else:
        config['LOG_FILE_PATH'] = folder_path

    config['NOTIFY_ON_SHIFT_1'] = input("Notify on 1 person shift? (yes/no): ").strip().lower() == 'yes'
    config['NOTIFY_ON_SHIFT_10'] = input("Notify on 10 person shift? (yes/no): ").strip().lower() == 'yes'
    config['NOTIFY_ON_REMAINING_5'] = input("Notify when 5 people left? (yes/no): ").strip().lower() == 'yes'

    with open('config.json', 'w') as config_file:
        json.dump(config, config_file)

    return config

def load_config():
    if os.path.exists('config.json'):
        with open('config.json', 'r') as config_file:
            config = json.load(config_file)
    else:
        config = get_config()
    return config

config = load_config()

BOT_TYPE = config['BOT_TYPE']
BOT_TOKEN = config['BOT_TOKEN']
LOG_FILE_PATH = config['LOG_FILE_PATH']
NOTIFY_ON_SHIFT_1 = config['NOTIFY_ON_SHIFT_1']
NOTIFY_ON_SHIFT_10 = config['NOTIFY_ON_SHIFT_10']
NOTIFY_ON_REMAINING_5 = config['NOTIFY_ON_REMAINING_5']

if BOT_TYPE == 'telegram':
    CHAT_ID = config['CHAT_ID']
    app = Application.builder().token(BOT_TOKEN).build()
    last_message_id = None

    async def send_message(message):
        global last_message_id
        try:
            if last_message_id:
                # Update the last message
                await app.bot.edit_message_text(chat_id=CHAT_ID, message_id=last_message_id, text=message)
            else:
                # Send a new message
                sent_message = await app.bot.send_message(chat_id=CHAT_ID, text=message)
                last_message_id = sent_message.message_id
        except TelegramError as e:
            print(f"An error occurred: {e}")

    async def send_startup_message():
        try:
            await app.bot.send_message(chat_id=CHAT_ID, text="I'm loaded")
        except TelegramError as e:
            print(f"An error occurred while sending startup message: {e}")

elif BOT_TYPE == 'discord':
    CHANNEL_ID = int(config['CHANNEL_ID'])
    bot = commands.Bot(command_prefix=None)
    last_message = None

    async def send_message(message):
        global last_message
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            if last_message:
                # Delete the last message
                await last_message.delete()
            # Send a new message
            last_message = await channel.send(message)
        else:
            print("Failed to find the channel.")

    @bot.event
    async def on_ready():
        print(f"Logged in as {bot.user}")

else:
    print("Invalid bot type. Use 'telegram' or 'discord'.")
    exit()

def parse_queue_position(line):
    match = re.search(r'Position in queue:\s*(\d+)', line)
    if match:
        return int(match.group(1))
    return None

def get_latest_queue_position():
    try:
        with open(LOG_FILE_PATH, 'r') as file:
            lines = file.readlines()
            for line in reversed(lines):
                position = parse_queue_position(line)
                if position is not None:
                    return position
    except FileNotFoundError:
        print("Log file not found.")
    return None

async def main():
    initial_position = None
    last_position = None

    while True:
        position = get_latest_queue_position()

        if position is not None:
            if initial_position is None:
                initial_position = position

            if NOTIFY_ON_SHIFT_10 and initial_position is not None and (initial_position - position) >= 10:
                await send_message(f"Position in queue has shifted by 10 or more: Current position is {position}")
                initial_position = position

            if NOTIFY_ON_SHIFT_1 and last_position is not None and int(position) < int(last_position):
                await send_message(f"Position in queue: {position}")

            if NOTIFY_ON_REMAINING_5 and int(position) <= 5:
                await send_message(f"Only 5 people left before you enter the game! Current position: {position}")

            last_position = position

        await asyncio.sleep(5)

if __name__ == "__main__":
    print("""
██████╗ ██████╗ ██████╗ ████████╗     ██████╗ ██╗   ██╗███████╗██╗   ██╗███████╗    ██████╗  ██████╗ ████████╗
╚════██╗██╔══██╗╚════██╗╚══██╔══╝    ██╔═══██╗██║   ██║██╔════╝██║   ██║██╔════╝    ██╔══██╗██╔═══██╗╚══██╔══╝
 █████╔╝██████╔╝ █████╔╝   ██║       ██║   ██║██║   ██║█████╗  ██║   ██║█████╗      ██████╔╝██║   ██║   ██║   
██╔═══╝ ██╔══██╗██╔═══╝    ██║       ██║   ██║██║   ██║██╔══╝  ██║   ██║██╔══╝      ██╔══██╗██║   ██║   ██║   
███████╗██████╔╝███████╗   ██║       ╚██████╔╝╚██████╔╝███████╗╚██████╔╝███████╗    ██████╔╝╚██████╔╝   ██║   
╚══════╝╚═════╝ ╚══════╝   ╚═╝        ╚══▀▀═╝  ╚═════╝ ╚══════╝ ╚═════╝ ╚══════╝    ╚═════╝  ╚═════╝    ╚═╝   
                                                                                                              
                                            v1.0.0                
""")
    if BOT_TYPE == 'telegram':
        asyncio.run(send_startup_message()) 
        asyncio.run(main())
    elif BOT_TYPE == 'discord':
        bot.loop.create_task(main())        
        bot.run(BOT_TOKEN)
