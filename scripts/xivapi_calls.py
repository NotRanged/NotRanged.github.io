import requests
import json
import math
import threading
from pathlib import Path
from collections import defaultdict

# Buffs Endpoint
BUFFS_API_URL = "https://xivapi.com/search"
buff_types = ["Medicine", "Meal"]
RECIPE_API_URL = 'https://xivapi.com/Recipe'
PARENT_DIR = Path(__file__).parents[1]


class Buffs:
    def __init__(self, cp_percent, cp_value, craft_percent, craft_value, control_percent, control_value, hq, name, name_de, name_fr, name_ja):
        self.cp_percent = cp_percent
        self.cp_value = cp_value
        self.craftsmanship_percent = craft_percent
        self.craftsmanship_value = craft_value
        self.control_percent = control_percent
        self.control_value = control_value
        self.hq = hq
        self.name = {
            "en": name,
            "de": name_de,
            "fr": name_fr,
            "ja": name_ja,
        }

def construct_recipe_json(original_recipe):
    """
    Returns a recipe dictionary in the format desired by the FFXIV crafting solver.
    Rewriting how it handles all the data is a monumental task, so instead I'm just going to do this.
    """
    if original_recipe["RecipeLevelTable"] is None:
        return
    recipe = {
        "name": {},
        "baseLevel": original_recipe["RecipeLevelTable"]["ClassJobLevel"],
        "level": original_recipe["RecipeLevelTable"]["ID"],
        "difficulty": math.floor(
            original_recipe["RecipeLevelTable"]["Difficulty"] * original_recipe["DifficultyFactor"] / 100),
        "durability": math.floor(
            original_recipe["RecipeLevelTable"]["Durability"] * original_recipe["DurabilityFactor"] / 100),
        "maxQuality": math.floor(
            original_recipe["RecipeLevelTable"]["Quality"] * original_recipe["QualityFactor"] / 100),
        "suggestedCraftsmanship": original_recipe["RecipeLevelTable"]["SuggestedCraftsmanship"],
        "suggestedControl": original_recipe["RecipeLevelTable"]["SuggestedControl"],
        "progressDivider": original_recipe["RecipeLevelTable"]["ProgressDivider"],
        "progressModifier": original_recipe["RecipeLevelTable"]["ProgressModifier"],
        "qualityDivider": original_recipe["RecipeLevelTable"]["QualityDivider"],
        "qualityModifier": original_recipe["RecipeLevelTable"]["QualityModifier"],
    }
    recipe["name"]["en"] = original_recipe["Name_en"]
    recipe["name"]["de"] = original_recipe["Name_de"]
    recipe["name"]["fr"] = original_recipe["Name_fr"]
    recipe["name"]["ja"] = original_recipe["Name_ja"]
    if original_recipe["RecipeLevelTable"]["Stars"] != 0:
        recipe["stars"] = original_recipe["RecipeLevelTable"]["Stars"]
    return recipe


def get_total_pages():
    """
    Gets the total amount of recipe pages that exist!
    """
    r = requests.get(RECIPE_API_URL)
    recipe_data = r.json()
    return recipe_data['Pagination']['PageTotal']


def api_call(page_id, recipes):
    """
    Handles the actual API calls.
    """
    url_call = f'https://xivapi.com/Recipe?page={page_id}&columns=Name_en,Name_de,Name_fr,Name_ja,' \
               f'ClassJob.NameEnglish,DurabilityFactor,QualityFactor,DifficultyFactor,RequiredControl,' \
               f'RequiredCraftsmanship,RecipeLevelTable'
    r = requests.get(url_call)
    page_data = r.json()
    if r.status_code == 429:
        print("Too many requests sent to XIVAPI!")

    for recipe in page_data['Results']:
        key = recipe['ClassJob']['NameEnglish']
        constructed_recipe = construct_recipe_json(recipe)
        if constructed_recipe:
            recipes[key].append(constructed_recipe)


def handle_api_calls(pages_amount):
    """
    Handle API calls with multi-threading, since XIVAPI is rate limited to 20.
    """
    recipes = defaultdict(list)
    threads = []
    for i in range(1, pages_amount + 1):
        t = threading.Thread(target=api_call, args=(i, recipes))
        threads.append(t)
        t.start()
        if i % 20 == 0:
            for t in threads:
                t.join()
            threads = []
    for t in threads:
        t.join()
    return recipes


def save_data_to_json(recipes):
    """
    Save recipes data to a .json file
    """
    Path(f'{PARENT_DIR}/data/recipedb/').mkdir(parents=True, exist_ok=True)
    for class_job, class_recipes in recipes.items():
        with open(f"{PARENT_DIR}/data/recipedb/{class_job}.json", mode="w", encoding="utf-8") as my_file:
            json.dump(class_recipes, my_file, indent=2, sort_keys=True, ensure_ascii=False)


def extract_buff_data(buff_name):
    """
    Extracts buff data for the given buff_name
    """
    params = {
        "indexes": "item",
        "columns": "Name,Bonuses,Name_en,Name_de,Name_fr,Name_ja",
        "body": {
            "query": {
                "bool": {
                    "should": [
                        {"match": {"Bonuses.CP.Relative": "true"}},
                        {"match": {"Bonuses.Control.Relative": "true"}},
                        {"match": {"Bonuses.Craftsmanship.Relative": "true"}}

                    ],
                    "must_not": [
                        {"match": {"ItemSearchCategory.Name_en": buff_name}}

                    ]
                }
            },
            "from": 0,
            "size": 100
        }
    }
    request = requests.post(BUFFS_API_URL, json=params)
    request.raise_for_status()

    buffs = []
    for item in request.json()["Results"]:
        # Extract both HQ and NQ buff data
        for hq in [False, True]:
            new_item = vars(Buffs(
                item.get("Bonuses", {}).get("CP", {}).get("Value"),
                item.get("Bonuses", {}).get("CP", {}).get("Max"),
                item.get("Bonuses", {}).get("Craftsmanship", {}).get("Value"),
                item.get("Bonuses", {}).get("Craftsmanship", {}).get("Max"),
                item.get("Bonuses", {}).get("Control", {}).get("Value"),
                item.get("Bonuses", {}).get("Control", {}).get("Max"),
                hq,
                item.get("Name"),
                item.get("Name_de"),
                item.get("Name_fr"),
                item.get("Name_ja")
            ))

            # Remove None values from previous step
            new_item = {k: v for k, v in new_item.items() if v is not None}
            buffs.append(new_item)
    return buffs


def save_buffs_to_file(buffs, buff_name):
    """
    Save buffs data to a .json file
    """
    Path(f'{PARENT_DIR}/data/buffs').mkdir(parents=True, exist_ok=True)
    with open(f"{PARENT_DIR}/data/buffs/{buff_name}.json", mode="w", encoding="utf-8") as my_file:
        json.dump(buffs, my_file, indent=2, sort_keys=True, ensure_ascii=False)


if __name__ == '__main__':
    pages_amount = get_total_pages()
    recipes = handle_api_calls(pages_amount)
    save_data_to_json(recipes)

    for buff_name in buff_types:
        buffs = extract_buff_data(buff_name)
        save_buffs_to_file(buffs, buff_name)
