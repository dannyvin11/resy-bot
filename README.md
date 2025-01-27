# Resy Reservation Bot

An automated bot for making restaurant reservations through Resy's platform.

## Setup

1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file by copying `.env.example`:
```bash
cp .env.example .env
```

4. Get your Resy API credentials:
   - Log into Resy in your web browser
   - Open Developer Tools (F12)
   - Go to the Network tab
   - Make any search on Resy
   - Look for requests to api.resy.com
   - Find the `x-resy-auth-token` in the request headers
   - Find the `api_key` in the authorization header

5. Update the `.env` file with your credentials and preferences

## Usage

Run the bot:
```bash
python resy_bot.py
```

The bot will prompt you for:
1. Restaurant name to search for

It will then attempt to:
1. Find the restaurant
2. Check for available reservations
3. Book the first available slot

## Features

- Restaurant search by name
- Automatic reservation booking
- Configurable party size and booking preferences
- Default to booking for next day at 7:00 PM

## Note

This bot requires valid Resy API credentials to function. Make sure to keep your API credentials secure and never share them. 