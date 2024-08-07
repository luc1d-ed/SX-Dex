import os
import json
import time
import datetime
import logging
import requests
import discord
from bs4 import BeautifulSoup
from discord.ext import commands
from dotenv import load_dotenv

def setup_logger(log_file_path):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(log_file_path)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)


def get_log_file_path():
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H_%M_%S,%f")[:-3]
    log_file_name = f"message_log_{timestamp}.log"
    log_file_path = os.path.join(os.path.dirname(__file__), "Logs", log_file_name)
    return log_file_path


def should_exclude_message(message_text):  # Add text here, which are in list but you do not want to send that.
    exclusion_keywords = [
        "A Brief History of SXD", 
        "Endeavour 2022-23 (Annual Magazine) : Colours and Promises",
        "Endeavour 2021 (Diamond Jubilee Edition): Bliss of Solitude",
        "SXD School Diary 2023-24",
        "SXD School Calendar 2023-24",
        "Book List - Class XI (Science, Commerce, Arts:2022-23)"
    ]

    for keyword in exclusion_keywords:
        if keyword in message_text:
            return True

    return False
            
def check_messages():
    url = "https://stxaviersschool.com"
    file_path = os.path.join(os.path.dirname(__file__), 'Data', 'Data.json')

    html_text = requests.get(url).text
    soup = BeautifulSoup(html_text, 'lxml')

    messages = soup.find_all('li', class_='')[:11]

    existing_messages = []

    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
            existing_messages = json.load(file)
    except FileNotFoundError:
        logging.error('File not found! \nCheck the path.')
        pass

    new_messages = []
    next_serial_number = len(existing_messages) + 1

    for message in messages:
        message_text = message.text.strip()
    
        if not message_text:
            continue  
    
        if should_exclude_message(message_text):
            continue  
    
        if message_text not in [existing_message["message"] for existing_message in existing_messages]:
            current_date = datetime.datetime.now().strftime("%d-%m-%Y")
            message_text = message_text.replace('"', '\\"')
            message_text = f"""{message_text}"""
            new_message = {
                "serial_number": next_serial_number,
                "message": message_text,
                "date": current_date
            }
            existing_messages.append(new_message)
            new_messages.append(new_message)
            next_serial_number += 1

    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(existing_messages, file, ensure_ascii=False, indent=4)

    log_file_path = get_log_file_path()
    setup_logger(log_file_path)

    dotenv_path = os.path.join(os.path.dirname(__file__), 'Data', '.env')
    load_dotenv(dotenv_path)
    TOKEN = os.getenv('DISCORD_TOKEN')

    intents = discord.Intents.default()
    intents.typing = True
    intents.presences = False

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='for new messages by SXD.'))
        logging.info(f"We have logged in as {client.user.name}.") 

        channels = [] # Add you own channel ID here.

        for one_channel in channels:
            channel = client.get_channel(one_channel)
            if channel:
                for message_data in new_messages:
                    formatted_message = f"- {message_data['message']}"
                    logging.info(f"Attempting to send message number: {next_serial_number}")
                    if isinstance(channel, (discord.TextChannel, discord.DMChannel)):
                        await channel.send(formatted_message)
                        logging.info(f"Relayed message: {formatted_message}")
                    else:
                        logging.error("Invalid channel type. Unable to send messages.")
            else:
                logging.error("Channel not found")

    try:
        client.run(TOKEN) # type: ignore
    except discord.LoginFailure:
        logging.error("Failed to log in with the provided token")


check_interval = 3600  # Customize the timing as per your wish (It is in seconds)

while True:
    check_messages()
    time.sleep(check_interval)
