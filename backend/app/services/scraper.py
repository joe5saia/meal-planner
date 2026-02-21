import html
import json
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag


def decode_html_entities(text: str | None) -> str | None:
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
            "error_message": (
                "NYT Cooking requires authentication and is not currently supported. "
                "Please copy ingredients manually."
            ),
        }
    if "ambitiouskitchen.com" in domain:
        return await scrape_generic_recipe(url, "ambitiouskitchen")
    if "smittenkitchen.com" in domain:
        return await scrape_generic_recipe(url, "smittenkitchen")
    return await scrape_generic_recipe(url, "unknown")


async def scrape_generic_recipe(url: str, source_site: str) -> dict:
    """
    Generic recipe scraper that looks for JSON-LD structured data.
    Falls back to HTML parsing if needed.
    """
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    recipe_data = extract_json_ld(soup)

    if recipe_data:
        return format_recipe_data(recipe_data, url, source_site)

    microdata_recipe = extract_microdata_recipe(soup, url, source_site)
    if microdata_recipe:
        return microdata_recipe

    return fallback_html_parse(soup, url, source_site)


def extract_json_ld(soup: BeautifulSoup) -> dict | None:
    """Extract Recipe schema from JSON-LD scripts."""
    scripts = soup.find_all("script", type="application/ld+json")

    for script in scripts:
        script_content = script.string
        if script_content is None:
            continue

        try:
            data = json.loads(script_content)
            recipe = find_recipe_in_json(data)
            if recipe:
                return recipe
        except json.JSONDecodeError:
            continue
        except TypeError:
            continue

    return None


def extract_microdata_recipe(soup: BeautifulSoup, url: str, source_site: str) -> dict | None:
    """
    Extract recipe data from HTML microdata.

    Some sites (including older Jetpack recipe blocks) expose itemprop-based metadata
    without JSON-LD. This function maps that markup into the normalized recipe shape.
    """
    recipe_root = soup.select_one('[itemscope][itemtype*="Recipe"], .jetpack-recipe')
    if not isinstance(recipe_root, Tag):
        return None

    title = _extract_title_from_microdata(recipe_root)
    ingredients = _extract_list_text(recipe_root.select('[itemprop="recipeIngredient"]'))
    instructions = _extract_instructions_from_microdata(recipe_root)

    # If we cannot find core recipe fields, fall back to generic HTML extraction.
    if not ingredients and not instructions:
        return None

    description = _extract_first_text(
        [recipe_root.select_one('[itemprop="description"]'), soup.find("meta", property="og:description")]
    )
    image_url = _extract_image_from_microdata(recipe_root, soup)

    prep_time = _extract_time_from_microdata(recipe_root, "prepTime")
    cook_time = _extract_time_from_microdata(recipe_root, "cookTime")
    total_time = _extract_time_from_microdata(recipe_root, "totalTime")
    servings = _extract_first_text([recipe_root.select_one('[itemprop="recipeYield"]')])

    return {
        "url": url,
        "title": title or "Untitled Recipe",
        "description": description,
        "image_url": image_url,
        "ingredients": ingredients,
        "instructions": instructions,
        "prep_time": prep_time,
        "cook_time": cook_time,
        "total_time": total_time,
        "servings": servings,
        "source_site": source_site,
        "requires_manual_entry": False,
    }


def _extract_title_from_microdata(recipe_root: Tag) -> str | None:
    """Extract a recipe title from itemprop or common Jetpack title classes."""
    title_node = recipe_root.select_one(
        '[itemprop="name"], .jetpack-recipe-title, h1, h2, h3'
    )
    return _extract_first_text([title_node])


def _extract_list_text(nodes: list[Tag]) -> list[str]:
    """Extract and clean text values from a list of HTML nodes."""
    values: list[str] = []
    for node in nodes:
        value = _node_text(node)
        if value:
            values.append(value)
    return values


def _extract_instructions_from_microdata(recipe_root: Tag) -> list[str]:
    """
    Extract instruction steps from microdata and Jetpack recipe blocks.

    Preference order:
    1. Explicit itemprop=recipeInstructions nodes
    2. Jetpack directions list items
    3. Jetpack direction paragraphs
    4. Jetpack directions as one text block
    """
    itemprop_instructions = _extract_list_text(recipe_root.select('[itemprop="recipeInstructions"]'))
    if itemprop_instructions:
        return itemprop_instructions

    directions = recipe_root.select_one(".jetpack-recipe-directions")
    if not isinstance(directions, Tag):
        return []

    list_steps = _extract_list_text(directions.select("li"))
    if list_steps:
        return list_steps

    paragraph_steps = _extract_list_text(directions.select("p"))
    if paragraph_steps:
        return paragraph_steps

    directions_text = _node_text(directions)
    return [directions_text] if directions_text else []


def _extract_time_from_microdata(recipe_root: Tag, prop_name: str) -> str | None:
    """Extract and format a duration value from microdata recipe time fields."""
    time_node = recipe_root.select_one(f'[itemprop="{prop_name}"]')
    if not isinstance(time_node, Tag):
        return None

    raw_value = (
        time_node.get("datetime")
        or time_node.get("content")
        or _node_text(time_node)
    )
    if not isinstance(raw_value, str):
        return None

    normalized_value = raw_value.strip()
    if normalized_value.lower().startswith("time:"):
        normalized_value = normalized_value.split(":", 1)[1].strip()
    return format_duration(normalized_value)


def _extract_image_from_microdata(recipe_root: Tag, soup: BeautifulSoup) -> str | None:
    """Extract image URL from microdata image fields, then OpenGraph fallback."""
    image_node = recipe_root.select_one('[itemprop="image"]')
    if isinstance(image_node, Tag):
        image_value = image_node.get("src") or image_node.get("content")
        if isinstance(image_value, str) and image_value.strip():
            return image_value.strip()

    og_image = soup.find("meta", property="og:image")
    if isinstance(og_image, Tag):
        image_value = og_image.get("content")
        if isinstance(image_value, str) and image_value.strip():
            return image_value.strip()

    return None


def _extract_first_text(nodes: list[Tag | None]) -> str | None:
    """Return the first non-empty text/content value from a sequence of nodes."""
    for node in nodes:
        if not isinstance(node, Tag):
            continue

        content_value = node.get("content")
        if isinstance(content_value, str) and content_value.strip():
            return decode_html_entities(content_value.strip())

        text_value = _node_text(node)
        if text_value:
            return text_value
    return None


def _node_text(node: Tag) -> str | None:
    """Extract normalized display text for an HTML node."""
    text = node.get_text(" ", strip=True)
    if not text:
        return None
    return decode_html_entities(text)


def find_recipe_in_json(data) -> dict | None:
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


def extract_image(image_data) -> str | None:
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


def format_duration(duration: str | None) -> str | None:
    """Convert ISO 8601 duration to human-readable format."""
    if not duration:
        return None

    normalized = duration.strip()
    match = re.fullmatch(
        r"P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
        normalized,
    )
    if not match:
        return normalized

    days, hours, minutes, seconds = match.groups()
    parts = []
    if days and int(days) > 0:
        parts.append(f"{days} day{'s' if int(days) > 1 else ''}")
    if hours and int(hours) > 0:
        parts.append(f"{hours} hour{'s' if int(hours) > 1 else ''}")
    if minutes and int(minutes) > 0:
        parts.append(f"{minutes} min")
    if seconds and int(seconds) > 0:
        parts.append(f"{seconds} sec")

    return " ".join(parts) if parts else None


def extract_servings(yield_data) -> str | None:
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
    image_content = og_image.get("content") if og_image else None
    image_url = image_content if isinstance(image_content, str) else None

    og_description = soup.find("meta", property="og:description")
    description_content = og_description.get("content") if og_description else None
    description = description_content if isinstance(description_content, str) else None

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
        "error_message": (
            "Could not extract recipe data automatically. Please enter ingredients manually."
        ),
    }
