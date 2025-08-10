# 🌍 Travel Guide MCP Server
- A FastMCP-powered travel guide tool that provides detailed information about any location in the world.
- It integrates with OpenStreetMap, Wikipedia, OpenWeatherMap, Ticketmaster, and TheMealDB to fetch data like:

-📍 Location details

- 📜 Brief descriptions

- ☀️ Weather info

- 🎟️ Local events

- 🍽️ Traditional dishes

# 📦 Features

Location Search: Get city/country details with coordinates.

Description: Pulls a short summary from Wikipedia.

Weather Data: Current temperature and conditions.

Events: Upcoming events from Ticketmaster.

Cuisine: Local dishes from TheMealDB API.

Authentication: Secured with Bearer token authentication.

# 🚀 Installation
### 1 setup the enviroment
```bash

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Mac/Linux
source venv/bin/activate
# Windows
venv\Scripts\activate
```

# 2 Install dependencies
```bash
pip install -r requirements.txt
```
# 3 🔑 Environment Variables
Create a .env file in the root directory and set:
```bash
AUTH_TOKEN=your_auth_token_here
MY_NUMBER=your_phone_or_custom_id
OWM_KEY=your_openweathermap_api_key
TICKETMASTER_KEY=your_ticketmaster_api_key
```
Notes:

AUTH_TOKEN → Required for Bearer authentication.

MY_NUMBER → Any ID you want to return in validate() tool.

OWM_KEY → Get it from OpenWeatherMap.

TICKETMASTER_KEY → Get it from Ticketmaster Developer Portal.

# 4 ▶️ Usage
Run the MCP server:
```bash
python main.py
```

🛠️ API Tools
1. validate
Returns the value of MY_NUMBER from .env.
```bash
{
  "result": "123456789"
}
```

Example Request:
```bash
{
  "location": "Paris",
  "detail_level": "full"
}
```
Example Response:
```bash
{
  "content": [
    {
      "type": "text",
      "text": "🌍 *Paris* (France)\n📍 Capital city of France.\n☀️ Weather: 20°C, clear sky\n🎟️ Events:\n• Jazz Festival (2025-08-15)\n🍽️ Local Cuisine:\n• Croissant\n• Ratatouille\n• Crème brûlée"
    }
  ],
  "structuredContent": {
    "name": "Paris",
    "type": "city",
    "country": "France",
    "coordinates": [48.8566, 2.3522]
  },
  "isError": false
}
```

# 📚 Dependencies
fastmcp
httpx
python-dotenv
pydantic

