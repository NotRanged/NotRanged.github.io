import requests
import json
import math
import io
import csv
from pathlib import Path
from collections import defaultdict
from tqdm import tqdm # funny progress bar :)
# This script is a mess.
# This is genuinely the first time I've ever made an API scraping script, or worked with .json objects!
# Feel free to suggest improvements and criticize and such.

# RE: Scraping Food & Medicine: read bottom README.md or on the github repo readme

def construct_recipe_json(original_recipe):
    # Returns a recipe dictionary in the format desired by the ffxiv crafting solver
    # Rewriting how it handles all the data is a monumental task so instead I'm just going to do this
    if original_recipe["RecipeLevelTable"] is None:
        return
    recipe = {
        "name": {},
        "baseLevel": original_recipe["RecipeLevelTable"]["ClassJobLevel"],
        "level": original_recipe["RecipeLevelTable"]["ID"],
        "difficulty": math.floor(original_recipe["RecipeLevelTable"]["Difficulty"] * original_recipe["DifficultyFactor"] / 100),
        "durability": math.floor(original_recipe["RecipeLevelTable"]["Durability"] * original_recipe["DurabilityFactor"] / 100),
        "maxQuality": math.floor(original_recipe["RecipeLevelTable"]["Quality"] * original_recipe["QualityFactor"] / 100),
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
    recipe["name"]["ko"] = original_recipe["Name_ko"]
    if original_recipe["RecipeLevelTable"]["Stars"] != 0:
        recipe["stars"] = original_recipe["RecipeLevelTable"]["Stars"]
    return recipe


def item_names_ko() -> dict[int, str]:
    response = requests.get(
        'https://raw.githubusercontent.com/Ra-Workspace/ffxiv-datamining-ko/master/csv/Item.csv',
    )

    body = io.StringIO(response.text)
    # omit the first line - second line will be field names
    body.readline()

    reader = csv.DictReader(
        body,
        delimiter=',',
        quotechar='"',
        lineterminator='\n',
        strict=True,
    )

    result = dict()

    for row in reader:
        id = row['#']
        name = row['Name']

        if name == '' or not id.isdigit():
            continue

        result[int(id)] = name

    return result


if __name__ == '__main__':
    # First part is getting the total amount of recipes that exist! This goes into an ID range.
    recipe_url = 'https://xivapi.com/Recipe'
    r = requests.get(recipe_url)
    recipe_data = r.json()
    pages_amount = recipe_data['Pagination']['PageTotal']
    ID_range = range(1, pages_amount + 1) # +1 because of how range works lol
    #ID_range = range(1, 1 + 1) # +1 because of how range works lol

    recipes = defaultdict(list)
    names_ko = item_names_ko()

    # Handle the actual API calls here
    for ID in tqdm(ID_range):
        # Construct an URL to get data from for every page
        url_call = 'https://xivapi.com/Recipe?page={0}&columns=Name_en,Name_de,Name_fr,Name_ja,ClassJob.NameEnglish,DurabilityFactor,QualityFactor,DifficultyFactor,RequiredControl,RequiredCraftsmanship,RecipeLevelTable,ItemResult.ID'.format(ID)
        r = requests.get(url_call)
        page_data = r.json()

        # Iterate through each recipe on the page
        for recipe in page_data['Results']:
            # Inject korean item names
            if recipe['ItemResult']['ID'] != None:
                id = int(recipe['ItemResult']['ID'])
                recipe['Name_ko'] = names_ko[id] if id in names_ko else None
            else:
                recipe['Name_ko'] = None

            # Save the data to the recipes dictionary, with a key for each crafting job
            key = recipe['ClassJob']['NameEnglish']
            constructed_recipe = construct_recipe_json(recipe)
            if constructed_recipe:
                recipes[key].append(constructed_recipe)

    # Save the data in recipes to a .json file in the out folder, with a file for every job
    # Create out directory, ignore error if it already exists
    path = Path('out')
    path.mkdir(exist_ok=True)
    keys = recipes.keys()
    for key in tqdm(keys):
        with open(f"out/{key}.json", mode="wt", encoding="utf-8") as db_file:
            json.dump(recipes[key], db_file, indent=2, sort_keys=True, ensure_ascii=False)

    print('script complete')
    print('debug halt')
