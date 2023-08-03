import os
import time
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty, DocumentAttributeFilename, InputMessagesFilterDocument
from tqdm import tqdm
from telethon.tl.functions.channels import GetFullChannelRequest
from tabulate import tabulate
import re

def get_api_credentials():
    api_id = input("Enter your API ID: ")
    api_hash = input("Enter your API HASH: ")

    # Save the API credentials in a .txt file for future reference
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_credentials.txt'), 'w') as f:
        f.write(f"{api_id}\n")
        f.write(f"{api_hash}")

    return int(api_id), api_hash

def initialize_client():
    print(os.path.dirname)
    script_directory = os.path.dirname(os.path.abspath(__file__))
    session_file_name = 'name.session'
    session_file_alt_name = 'session.session'
    session_file = os.path.join(script_directory, session_file_name)
    api_creds_file = os.path.join(script_directory, 'api_credentials.txt')

    if not os.path.exists(session_file):
        # Try the alternate session file name
        session_file = os.path.join(script_directory, session_file_alt_name)

    if os.path.exists(session_file):
        # Load API credentials from the .txt file
        with open(api_creds_file, 'r') as f:
            api_id = int(f.readline().strip())
            api_hash = f.readline().strip()
            print("Session file exists.")
    else:
        # Ask the user for API credentials for the first time
        api_id, api_hash = get_api_credentials()
        print("Session file not found. Asking for API credentials.")

    # Initialize the TelegramClient
    client = TelegramClient('name', api_id, api_hash)
    client.start()

    return client

# Initialize the TelegramClient
client = initialize_client()
# Rest of the code remains the same...


def is_valid_media(message):
    if message.media:
        if hasattr(message.media, 'document'):
            return True
        elif hasattr(message.media, 'web'):
            return True
    return False


def fetch_extensions(messages):
    extensions = {}  
    for message in tqdm(messages, desc="Fetching extensions", unit="message"):
        if is_valid_media(message):
            for attribute in message.media.document.attributes:
                if isinstance(attribute, DocumentAttributeFilename):
                    file_name = attribute.file_name.lower()
                    ext = os.path.splitext(file_name)[1]
                    if ext not in extensions:
                        extensions[ext] = 0
                    extensions[ext] += 1
    return extensions



def display_extensions_table(extensions):
    extensions_table = []
    for i, (ext, total_attachments) in enumerate(extensions.items(), start=1):
        extensions_table.append([i, ext, total_attachments])
    print(tabulate(extensions_table, headers=["Index", "Extension", "Total Attachments"]))


def download_media(group, cl, name, file_ext):
    messages = cl.get_messages(group, limit=1000, filter=InputMessagesFilterDocument)

    for message in tqdm(messages, desc="Downloading media", unit="message"):
        if is_valid_media(message):
            for attribute in message.media.document.attributes:
                if isinstance(attribute, DocumentAttributeFilename):
                    original_file_name = attribute.file_name  # Get the original file name with the extension
                    ext = os.path.splitext(original_file_name)[1]
                    if ext == file_ext :
                        # Save the file with the original file name
                        message.download_media('./' + name + '/' + original_file_name)

def generate_txt_files(messages, extension_index):
    for message in tqdm(messages, desc="Generating text files", unit="message"):
        if is_valid_media(message):
            for attribute in message.media.document.attributes:
                if isinstance(attribute, DocumentAttributeFilename):
                    file_name = attribute.file_name.lower()
                    ext = os.path.splitext(file_name)[1]
                    if ext == extension_index:
                        base_file_name = os.path.splitext(file_name)[0]
                        txt_file_name = os.path.join('.', f"{base_file_name}.txt")
                        with open(txt_file_name, 'w', encoding='utf-8') as txt_file:
                            txt_file.write(message.message)


def get_user_choice(prompt, min_value, max_value):
    while True:
        try:
            user_choice = int(input(prompt))
            if min_value <= user_choice <= max_value:
                return user_choice
            print("Invalid choice. Please enter a valid index.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def get_total_messages(channel):
    full_channel = client(GetFullChannelRequest(channel=channel))
    return full_channel.full_chat.read_inbox_max_id

def fetch_attachments_details(messages, extension_index):
    attachments_details = []
    for message in messages:
        if is_valid_media(message):
            for attribute in message.media.document.attributes:
                if isinstance(attribute, DocumentAttributeFilename):
                    file_name = attribute.file_name
                    ext = os.path.splitext(file_name)[1]
                    if ext == extension_index:
                        size_in_mb = message.media.document.size / 1024 / 1024
                        message_text = message.message if message.message else "No Message"
                        attachments_details.append([file_name, message_text, f"{size_in_mb:.2f} MB"])
    return attachments_details


# Fetch the chats
result = client(GetDialogsRequest(
    offset_date=None,
    offset_id=0,
    offset_peer=InputPeerEmpty(),
    limit=500,
    hash=0,
))

# Display chats in an indexed table with total messages
chats_table = []
for i, chat in enumerate(result.chats, start=1):
    if hasattr(chat, 'title'):
        chat_name = chat.title
    elif hasattr(chat, 'username'):
        chat_name = chat.username
    else:
        chat_name = "Unknown"
    
    total_messages = get_total_messages(chat) if hasattr(chat, 'megagroup') or hasattr(chat, 'channel') else 0
    chats_table.append([i, chat_name, total_messages])

print(tabulate(chats_table, headers=["INDEX", "NAME", "TOTAL MESSAGES"]))

# Ask the user to choose a chat
chat_choice = get_user_choice("Enter the index of the channel/group you want to choose: ", 1, len(result.chats))
selected_chat = result.chats[chat_choice - 1]

# Fetch extensions of all available attachments
messages = client.get_messages(selected_chat, limit=1000)
extensions = fetch_extensions(messages)

# Display extension table with the total number of attachments
display_extensions_table(extensions)

# Ask user to choose an extension
extension_choice = get_user_choice("Enter the index of the extension you want to choose: ", 1, len(extensions))
extension_index = list(extensions.keys())[extension_choice - 1]

# Sanitize the chat title to replace invalid characters with underscores
chat_title = re.sub(r'[<>:"/\\|?*]', '_', selected_chat.title)

# Filter attachments based on the selected extension
attachments_details = fetch_attachments_details(messages, extension_index)

print(tabulate(attachments_details, headers=["INDEX", "FILE NAME", "MESSAGE", "SIZE (MB)"]))

# Pause for 4 seconds
print("Please wait for 4 seconds...")
time.sleep(4)

# Ask user if they want to download files
download_choice = input("Do you want to download the files? (y/n): ")
if download_choice.lower() == 'y':
    # Download the chosen extension files
    download_media(selected_chat, client, chat_title, extension_index)
    print(f"Download of {extension_index.upper()} files is completed.")

    # Ask user if they want to generate text files
    generate_txt_choice = input("Do you want to generate the text files? (y/n): ")
    if generate_txt_choice.lower() == 'y':
        # Generate text files for the chosen extension files
        generate_txt_files(messages, extension_index)
        print("Text files generated.")
    else:
        print("Text file generation process canceled.")
else:
    print("Download process canceled.")

# Add a delay before exiting the script
print("Exiting the script in 2 seconds...")
time.sleep(2)
