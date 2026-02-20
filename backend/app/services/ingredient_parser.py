import re
from collections import defaultdict

UNIT_NORMALIZATIONS = {
    "tbsp": "tablespoon",
    "tbsps": "tablespoon",
    "tablespoons": "tablespoon",
    "tbs": "tablespoon",
    "tsp": "teaspoon",
    "tsps": "teaspoon",
    "teaspoons": "teaspoon",
    "oz": "ounce",
    "ozs": "ounce",
    "ounces": "ounce",
    "lb": "pound",
    "lbs": "pound",
    "pounds": "pound",
    "c": "cup",
    "cups": "cup",
    "pt": "pint",
    "pts": "pint",
    "pints": "pint",
    "qt": "quart",
    "qts": "quart",
    "quarts": "quart",
    "gal": "gallon",
    "gals": "gallon",
    "gallons": "gallon",
    "ml": "milliliter",
    "mls": "milliliter",
    "milliliters": "milliliter",
    "l": "liter",
    "liters": "liter",
    "g": "gram",
    "grams": "gram",
    "kg": "kilogram",
    "kilograms": "kilogram",
    "cloves": "clove",
    "pieces": "piece",
    "slices": "slice",
    "cans": "can",
    "packages": "package",
    "bunches": "bunch",
    "heads": "head",
    "stalks": "stalk",
    "sprigs": "sprig",
}

FRACTION_MAP = {
    "½": 0.5,
    "⅓": 1 / 3,
    "⅔": 2 / 3,
    "¼": 0.25,
    "¾": 0.75,
    "⅕": 0.2,
    "⅖": 0.4,
    "⅗": 0.6,
    "⅘": 0.8,
    "⅙": 1 / 6,
    "⅚": 5 / 6,
    "⅛": 0.125,
    "⅜": 0.375,
    "⅝": 0.625,
    "⅞": 0.875,
}

DESCRIPTORS = {
    "fresh",
    "dried",
    "chopped",
    "minced",
    "diced",
    "sliced",
    "whole",
    "ground",
    "crushed",
    "grated",
    "shredded",
    "julienned",
    "thinly",
    "finely",
    "roughly",
    "coarsely",
    "peeled",
    "seeded",
    "cored",
    "trimmed",
    "rinsed",
    "drained",
    "packed",
    "loosely",
    "firmly",
    "lightly",
    "softened",
    "melted",
    "room",
    "temperature",
    "cold",
    "warm",
    "hot",
    "frozen",
    "thawed",
    "cubed",
    "halved",
    "quartered",
    "torn",
    "crumbled",
    "divided",
    "optional",
    "to",
    "taste",
    "plus",
    "more",
    "extra",
    "about",
    "approximately",
    "heaping",
    "scant",
    "level",
    "generous",
    "small",
    "medium",
    "large",
    "thin",
    "thick",
    "boneless",
    "skinless",
    "unsalted",
    "salted",
    "low-sodium",
    "reduced-fat",
    "fat-free",
    "organic",
    "raw",
    "cooked",
    "uncooked",
    "prepared",
    "store-bought",
    "homemade",
}


def singularize(word: str) -> str:
    """Simple singularization for ingredient matching."""
    if len(word) <= 2:
        return word
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("oes"):
        return word[:-2]
    if word.endswith("es") and len(word) > 3 and word[-3] in "sxzh":
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 2:
        return word[:-1]
    return word


def is_section_header(ingredient_str: str) -> bool:
    """Detect if a string is a section header, not an ingredient."""
    text = ingredient_str.strip().lower()

    return bool(
        not text
        or re.match(r"^for\s+(the\s+)?", text)
        or text.endswith(":")
        or re.match(
            r"^(sauce|filling|topping|garnish|serving|marinade|dressing|glaze|crust|base|assembly):?$",
            text,
        )
    )


COMMON_UNITS = {
    "tablespoon",
    "teaspoon",
    "cup",
    "ounce",
    "pound",
    "gram",
    "kilogram",
    "liter",
    "milliliter",
    "pint",
    "quart",
    "gallon",
    "clove",
    "piece",
    "slice",
    "can",
    "package",
    "bunch",
    "head",
    "stalk",
    "sprig",
    "pinch",
    "dash",
    "handful",
    "medium",
    "large",
    "small",
}


def parse_ingredient(ingredient_str: str) -> dict:
    """
    Parse an ingredient string into quantity, unit, and name.
    Returns a dict with 'quantity', 'unit', 'name', and 'original'.
    """
    original = ingredient_str.strip()
    text = original.lower()

    for frac_char, value in FRACTION_MAP.items():
        text = text.replace(frac_char, f" {value} ")

    text = re.sub(r"(\d+)\s*/\s*(\d+)", lambda m: str(float(m.group(1)) / float(m.group(2))), text)

    quantity_pattern = r"^([\d\s.]+(?:\s*-\s*[\d.]+)?)"
    match = re.match(quantity_pattern, text)

    quantity = None
    remaining = text

    if match:
        qty_str = match.group(1).strip()
        remaining = text[match.end() :].strip()

        if "-" in qty_str:
            parts = qty_str.split("-")
            try:
                quantity = (float(parts[0].strip()) + float(parts[1].strip())) / 2
            except ValueError:
                quantity = None
        else:
            parts = qty_str.split()
            try:
                quantity = sum(float(p) for p in parts if p)
            except ValueError:
                quantity = None

    words = remaining.split()
    unit = None
    name_words = []

    for word in words:
        clean_word = word.rstrip(".,")
        normalized = UNIT_NORMALIZATIONS.get(clean_word, clean_word)

        if normalized in COMMON_UNITS and unit is None:
            unit = normalized
        else:
            name_words.append(word)

    name = " ".join(name_words)

    name = re.sub(r"\s*\([^)]*\)\s*", " ", name)
    name = re.sub(r",.*$", "", name)
    name = " ".join(name.split())

    return {
        "quantity": quantity,
        "unit": unit,
        "name": name.strip(),
        "original": original,
    }


def normalize_ingredient_name(name: str) -> str:
    """Normalize ingredient name for matching."""
    name = name.lower().strip()
    name = re.sub(r"\s+", " ", name)

    words = name.split()
    core_words = [w for w in words if w not in DESCRIPTORS]

    core_words = [singularize(w) for w in core_words]

    core_words.sort()

    return " ".join(core_words) if core_words else name


def aggregate_ingredients(ingredients: list[str]) -> list[dict]:
    """
    Aggregate a list of ingredient strings, combining matching items.
    Returns a list of GroceryItem-like dicts.
    """
    filtered = [ing for ing in ingredients if not is_section_header(ing)]
    parsed_ingredients = [parse_ingredient(ing) for ing in filtered]

    grouped = defaultdict(list)
    for parsed in parsed_ingredients:
        key = (normalize_ingredient_name(parsed["name"]), parsed["unit"])
        grouped[key].append(parsed)

    result = []
    for (name, unit), items in grouped.items():
        original_strings = [item["original"] for item in items]

        quantities = [item["quantity"] for item in items if item["quantity"] is not None]

        if quantities:
            total_qty = sum(quantities)
            if total_qty == int(total_qty):
                quantity_str = str(int(total_qty))
            else:
                quantity_str = f"{total_qty:.2f}".rstrip("0").rstrip(".")
        else:
            quantity_str = None

        display_name = items[0]["name"] if items else name

        result.append(
            {
                "name": display_name,
                "quantity": quantity_str,
                "unit": unit,
                "original_strings": original_strings,
            }
        )

    result.sort(key=lambda x: x["name"].lower())

    return result
