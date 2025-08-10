import asyncio
import os
from typing import Annotated, Optional
from dotenv import load_dotenv
from fastmcp import FastMCP
from pydantic import Field
import httpx
from urllib.parse import quote_plus

# Fix import paths
try:
    from fastmcp.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
    from fastmcp import ErrorData, McpError
    from fastmcp.types import INVALID_PARAMS, INTERNAL_ERROR
except ImportError:
    from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
    from mcp import ErrorData, McpError
    from mcp.server.auth.provider import AccessToken
    from mcp.types import INVALID_PARAMS, INTERNAL_ERROR

load_dotenv()

# Config
TOKEN = os.environ["AUTH_TOKEN"]
MY_NUMBER = os.environ["MY_NUMBER"]
OWM_KEY = os.environ["OWM_KEY"]
TICKETMASTER_KEY = os.environ["TICKETMASTER_KEY"]

# Auth Provider
class SimpleBearerAuthProvider(BearerAuthProvider):
    def __init__(self, token: str):
        k = RSAKeyPair.generate()
        super().__init__(public_key=k.public_key, jwks_uri=None, issuer=None, audience=None)
        self.token = token

    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(token=token, client_id="puch-client", scopes=["*"], expires_at=None)
        return None

# MCP Setup
mcp = FastMCP("Travel Guide MCP Server", auth=SimpleBearerAuthProvider(TOKEN), stateless_http=True)

@mcp.tool
async def validate() -> str:
    return MY_NUMBER

async def get_location_info(location: str) -> dict:
    """Get location data from Nominatim"""
    url = f"https://nominatim.openstreetmap.org/search?q={quote_plus(location)}&format=json&addressdetails=1&limit=1"
    
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers={"User-Agent": "PuchAI-TravelGuide/1.0"}, timeout=10.0)
        res.raise_for_status()
        data = res.json()
        
        if not data:
            raise McpError(ErrorData(code=INVALID_PARAMS, message="Location not found"))
        
        result = data[0]
        address = result.get("address", {})
        
        return {
            "name": result.get("display_name", "").split(",")[0],
            "type": result.get("type", "unknown"),
            "country": address.get("country"),
            "country_code": address.get("country_code", "").upper(),
            "city": address.get("city") or address.get("town") or address.get("village"),
            "coordinates": (float(result["lat"]), float(result["lon"])) if "lat" in result else None,
        }

async def get_location_description(location_name: str, country: str = None) -> Optional[str]:
    """Get brief description from Wikipedia"""
    try:
        # Try location name first, then with country if available
        search_terms = [location_name]
        if country and location_name != country:
            search_terms.append(f"{location_name}, {country}")
            
        for search_term in search_terms:
            # Search for page
            search_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote_plus(search_term)}"
            
            async with httpx.AsyncClient() as client:
                res = await client.get(search_url, timeout=8.0)
                
                if res.status_code == 200:
                    data = res.json()
                    extract = data.get("extract", "")
                    
                    if extract and len(extract) > 50:
                        # Return first sentence or first 200 chars
                        sentences = extract.split('. ')
                        if len(sentences) > 0:
                            first_sentence = sentences[0] + ('.' if not sentences[0].endswith('.') else '')
                            return first_sentence[:200] + ('...' if len(first_sentence) > 200 else '')
                    
        return None
    except:
        return None

async def get_weather(lat: float, lon: float) -> Optional[dict]:
    """Get weather data"""
    if not lat or not lon or not OWM_KEY:
        return None
        
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OWM_KEY}&units=metric"
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, timeout=10.0)
            data = res.json()
            return {
                "temp": data.get("main", {}).get("temp"),
                "conditions": data.get("weather", [{}])[0].get("description"),
            }
        except:
            return None

async def get_events(location_info: dict) -> list:
    """Get events from Ticketmaster"""
    if not TICKETMASTER_KEY:
        return []
    
    try:
        params = {"apikey": TICKETMASTER_KEY, "size": "3", "sort": "date,asc"}
        
        if location_info.get("city"):
            params["city"] = location_info["city"]
        if location_info.get("country_code") and len(location_info["country_code"]) == 2:
            params["countryCode"] = location_info["country_code"]
            
        coords = location_info.get("coordinates")
        if coords:
            params["latlong"] = f"{coords[0]},{coords[1]}"
            params["radius"] = "50"
        
        async with httpx.AsyncClient() as client:
            res = await client.get("https://app.ticketmaster.com/discovery/v2/events.json", 
                                 params=params, timeout=15.0)
            
            if res.status_code != 200:
                return []
                
            data = res.json()
            if "_embedded" not in data or "events" not in data["_embedded"]:
                return []
            
            events = []
            for event in data["_embedded"]["events"][:3]:
                venue_name = ""
                if "_embedded" in event and "venues" in event["_embedded"]:
                    venue_name = event["_embedded"]["venues"][0].get("name", "")
                
                events.append({
                    "name": event.get("name", "Unknown Event"),
                    "date": event.get("dates", {}).get("start", {}).get("localDate", "TBA"),
                    "venue": venue_name
                })
            
            return events
    except:
        return []

async def get_dishes(country: str) -> list:
    """Get traditional dishes"""
    if not country:
        return []
    
    # Map country names to MealDB areas
    country_map = {
        "United States": "American", "United Kingdom": "British", "UK": "British",
        "China": "Chinese", "India": "Indian", "Italy": "Italian", "France": "French",
        "Mexico": "Mexican", "Japan": "Japanese", "Thailand": "Thai", "Greece": "Greek",
        "Spain": "Spanish", "Turkey": "Turkish", "Morocco": "Moroccan", "Jamaica": "Jamaican",
        "Canada": "Canadian", "Malaysia": "Malaysian", "Egypt": "Egyptian", "Tunisia": "Tunisian",
        "Croatia": "Croatian", "Ireland": "Irish", "Poland": "Polish", "Portugal": "Portuguese",
        "Russia": "Russian", "Ukraine": "Ukrainian", "Vietnam": "Vietnamese"
    }
    
    search_terms = [country_map.get(country, country), country]
    
    for term in search_terms:
        try:
            url = f"https://www.themealdb.com/api/json/v1/1/filter.php?a={quote_plus(term)}"
            async with httpx.AsyncClient() as client:
                res = await client.get(url, timeout=10.0)
                
                if res.status_code == 200:
                    data = res.json()
                    if data.get("meals"):
                        return [{"name": meal.get("strMeal")} for meal in data["meals"][:3]]
        except:
            continue
    
    return []

@mcp.tool(description="Get comprehensive travel info")
async def travel_guide(
    location: Annotated[str, Field(description="City, country or region")],
    detail_level: Annotated[str, Field(description="'basic' or 'full'")] = "full"
) -> dict:
    try:
        loc = await get_location_info(location)
        
        response = {
            "name": loc["name"],
            "type": loc.get("type", "unknown"),
            "country": loc.get("country"),
            "coordinates": loc.get("coordinates")
        }

        if detail_level == "full":
            # Get description
            description = await get_location_description(loc["name"], loc.get("country"))
            if description:
                response["description"] = description
            
            # Get weather
            if loc.get("coordinates"):
                weather = await get_weather(*loc["coordinates"])
                if weather:
                    response["weather"] = weather
            
            # Get events for populated places
            if loc.get("type") in ["city", "town", "village", "municipality", "hamlet", "suburb"]:
                events = await get_events(loc)
                if events:
                    response["events"] = events
            
            # Get dishes
            if loc.get("country"):
                dishes = await get_dishes(loc["country"])
                if dishes:
                    response["dishes"] = dishes

        # Format output
        text_parts = [f"🌍 *{loc['name']}*"]
        if loc.get("country") and loc["name"] != loc["country"]:
            text_parts.append(f"({loc['country']})")
            
        if detail_level == "full":
            if response.get("description"):
                text_parts.append(f"\n📍 {response['description']}")
                
            if response.get("weather"):
                w = response["weather"]
                text_parts.append(f"\n☀️ *Weather*: {w['temp']}°C, {w['conditions']}")
                
            if response.get("events"):
                text_parts.append(f"\n🎟️ *Events*:")
                for e in response["events"]:
                    venue = f" at {e['venue']}" if e.get('venue') else ""
                    text_parts.append(f"\n• {e['name']}{venue} ({e['date']})")
                
            if response.get("dishes"):
                text_parts.append(f"\n🍽️ *Local Cuisine*:")
                for d in response["dishes"]:
                    text_parts.append(f"\n• {d['name']}")

        return {
            "content": [{"type": "text", "text": "".join(text_parts)}],
            "structuredContent": response,
            "isError": False
        }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
            "isError": True
        }

async def main():
    print("🚀 Travel Guide MCP running on http://0.0.0.0:8086")
    await mcp.run_async("streamable-http", host="0.0.0.0", port=8086)

if __name__ == "__main__":
    asyncio.run(main())