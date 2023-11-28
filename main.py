import json
import os
from datetime import datetime
from email.mime import audio

import openai
import requests
from telegram import MessageEntity, Update
from telegram.ext import (Application, CallbackContext, CommandHandler,
                          MessageHandler, Updater, filters)

from config import OPENAI_API_KEY, TELEGRAM_BOT_TOKEN

# Initialize your OpenAI API key
openai.api_key = OPENAI_API_KEY



def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi! Send me a voice message, and I will summarize it for you.')

def read_system_instruction(file_path):
    """Read system instruction from a file."""
    with open(file_path, 'r') as file:
        return file.read().strip()

def summarize_text(text):
    """Summarize the given text using OpenAI GPT."""
    instruction = read_system_instruction('system_instruction.txt')
    # Select the appropriate model based on token length
    model = "gpt-3.5-turbo-0301"
    messages = [{"role": "system", "content": instruction}, {"role": "user", "content": text}]
    
    try:
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {openai.api_key}', 'Content-Type': 'application/json'},
            json={'model': model, 'messages': messages}
        )
        response.raise_for_status()
        data = response.json()
        summary= data['choices'][0]['message']['content'].strip()
        current_date = datetime.now().strftime("%d.%m.%Y")
        formatted_summary = f"{current_date}\n\nSummary:\n" + "\n".join(f"- {item}" for item in summary.splitlines())
        return formatted_summary
    except requests.RequestException as e:
        print(f"Error in OpenAI API call: {e}")
        return "Sorry, I couldn't process your request right now."

def download_file(url, token):
    """Download file from Telegram."""
    local_filename = url.split('/')[-1]
    response = requests.get(url, headers={'Authorization': f'Bearer {token}'})
    with open(local_filename, 'wb') as file:
        file.write(response.content)
    return local_filename

def send_to_whisper(audio_file):
    """Send audio file to OpenAI Whisper for transcription."""
    with open(audio_file, 'rb') as file:
        response = requests.post(
            'https://api.openai.com/v1/audio/transcriptions',
            headers={'Authorization': f'Bearer {openai.api_key}'},
            data={'model': 'whisper-1'},  # Specify the Whisper model here
            files={'file': file}
        )
    
    res = response.json()
    if 'error' in res:
        raise Exception(res['error'])

    return res['text']

async def handle_voice(update: Update, context: CallbackContext) -> None:
    """Handle voice messages."""

    if update.message.voice:
        bot = context.bot
        file = await bot.get_file(update.message.voice.file_id)
        file_path = file.file_path

        try:
            # Downloading the voice message
            audio_file = download_file(file_path, bot.token)

            # Transcribing the audio file using OpenAI Whisper
            transcription = send_to_whisper(audio_file)

            # Summarizing the transcription
            summary = summarize_text(transcription)

            # Send the summary back to the user
            await update.message.reply_text(summary)

            # Clean up the downloaded file
            os.remove(audio_file)
        except Exception as e:
            await update.message.reply_text(f"An error occurred: {e}")

def main():
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.ALL, handle_voice))
    application.run_polling()

def test():
    audio_file = "example_day.m4a"
    transcription = send_to_whisper(audio_file)
    summary = summarize_text(transcription)
    print(summary)

if __name__ == '__main__':
    main()
    #test()
    print("Done!")
