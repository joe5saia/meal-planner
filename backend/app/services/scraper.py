import httpx
from bs4 import BeautifulSoup
import json
import re
import html
from typing import Optional
from urllib.parse import urlparse


def decode_html_entities(text: Optional[str]) -> Optional[str]:
    """Decode HTML entities like &amp; to & in text."""
    if text is None:
        return None
    return html.unescape(text)


async def scrape_recipe(url: str) -> dict:
    """
    Scrape a recipe from a URL.
    Routes to appropriate scraper based on the domain.
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    if "cooking.nytimes.com" in domain:
        return {
            "url": url,
            "title": "NYT Cooking Recipe",
            "description": None,
            "image_url": None,
            "ingredients": [],
            "instructions": [],
            "prep_time": None,
            "cook_time": None,
            "total_time": None,
            "servings": None,
            "source_site": "nyt",
            "requires_manual_entry": True,
            "error_message": "NYT Cooking requires authentication and is not currently supported. Please copy ingredients manually.",
        }
    elif "ambitiouskitchen.com" in domain:
        return await scrape_generic_recipe(url, "ambitiouskitchen")
    elif "smittenkitchen.com" in domain:
        return await scrape_generic_recipe(url, "smittenkitchen")
    else:
        return await scrape_generic_recipe(url, "unknown")


async def scrape_generic_recipe(url: str, source_site: str) -> dict:
    """
    Generic recipe scraper that looks for JSON-LD structured data.
    Falls back to HTML parsing if needed.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
    
    soup = BeautifulSoup(response.text, "lxml")
    
    recipe_data = extract_json_ld(soup)
    
    if recipe_data:
        return format_recipe_data(recipe_data, url, source_site)
    
    return fallback_html_parse(soup, url, source_site)


def extract_json_ld(soup: BeautifulSoup) -> Optional[dict]:
    """Extract Recipe schema from JSON-LD scripts."""
    scripts = soup.find_all("script", type="application/ld+json")
    
    for script in scripts:
        try:
            data = json.loads(script.string)
            recipe = find_recipe_in_json(data)
            if recipe:
                return recipe
        except (json.JSONDecodeError, TypeError):
            continue
    
    return None


def find_recipe_in_json(data) -> Optional[dict]:
    """Recursively search for Recipe type in JSON-LD."""
    if isinstance(data, dict):
        if data.get("@type") == "Recipe":
            return data
        if isinstance(data.get("@type"), list) and "Recipe" in data.get("@type"):
            return data
        if "@graph" in data:
            for item in data["@graph"]:
                recipe = find_recipe_in_json(item)
                if recipe:
                    return recipe
    elif isinstance(data, list):
        for item in data:
            recipe = find_recipe_in_json(item)
            if recipe:
                return recipe
    return None


def format_recipe_data(data: dict, url: str, source_site: str) -> dict:
    """Format JSON-LD recipe data into our standard format."""
    ingredients = data.get("recipeIngredient", [])
    if not isinstance(ingredients, list):
        ingredients = [ingredients]
    
    decoded_ingredients = [decode_html_entities(ing) for ing in ingredients]
    
    instructions = extract_instructions(data.get("recipeInstructions", []))
    decoded_instructions = [decode_html_entities(inst) for inst in instructions]
    
    return {
        "url": url,
        "title": decode_html_entities(data.get("name", "Untitled Recipe")),
        "description": decode_html_entities(data.get("description")),
        "image_url": extract_image(data.get("image")),
        "ingredients": decoded_ingredients,
        "instructions": decoded_instructions,
        "prep_time": format_duration(data.get("prepTime")),
        "cook_time": format_duration(data.get("cookTime")),
        "total_time": format_duration(data.get("totalTime")),
        "servings": decode_html_entities(extract_servings(data.get("recipeYield"))),
        "source_site": source_site,
        "requires_manual_entry": False,
    }


def extract_instructions(instructions) -> list[str]:
    """Extract instruction steps from various formats."""
    if not instructions:
        return []
    
    if isinstance(instructions, str):
        return [instructions]
    
    if isinstance(instructions, list):
        result = []
        for item in instructions:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                if item.get("@type") == "HowToStep":
                    result.append(item.get("text", ""))
                elif item.get("@type") == "HowToSection":
                    section_steps = item.get("itemListElement", [])
                    for step in section_steps:
                        if isinstance(step, dict):
                            result.append(step.get("text", ""))
        return [s for s in result if s]
    
    return []


def extract_image(image_data) -> Optional[str]:
    """Extract image URL from various formats."""
    if not image_data:
        return None
    if isinstance(image_data, str):
        return image_data
    if isinstance(image_data, list) and image_data:
        return extract_image(image_data[0])
    if isinstance(image_data, dict):
        return image_data.get("url") or image_data.get("contentUrl")
    return None


def format_duration(duration: Optional[str]) -> Optional[str]:
    """Convert ISO 8601 duration to human-readable format."""
    if not duration:
        return None
    
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if not match:
        return duration
    
    hours, minutes, seconds = match.groups()
    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if int(hours) > 1 else ''}")
    if minutes:
        parts.append(f"{minutes} min")
    if seconds:
        parts.append(f"{seconds} sec")
    
    return " ".join(parts) if parts else None


def extract_servings(yield_data) -> Optional[str]:
    """Extract servings from recipeYield."""
    if not yield_data:
        return None
    if isinstance(yield_data, str):
        return yield_data
    if isinstance(yield_data, list) and yield_data:
        return str(yield_data[0])
    return str(yield_data)


def fallback_html_parse(soup: BeautifulSoup, url: str, source_site: str) -> dict:
    """
    Fallback HTML parsing when JSON-LD is not available.
    Returns partial data and flags for manual entry.
    """
    title = soup.find("h1")
    title_text = title.get_text(strip=True) if title else "Untitled Recipe"
    
    og_image = soup.find("meta", property="og:image")
    image_url = og_image.get("content") if og_image else None
    
    og_description = soup.find("meta", property="og:description")
    description = og_description.get("content") if og_description else None
    
    return {
        "url": url,
        "title": decode_html_entities(title_text),
        "description": decode_html_entities(description),
        "image_url": image_url,
        "ingredients": [],
        "instructions": [],
        "prep_time": None,
        "cook_time": None,
        "total_time": None,
        "servings": None,
        "source_site": source_site,
        "requires_manual_entry": True,
        "error_message": "Could not extract recipe data automatically. Please enter ingredients manually.",
    }
