# meal_planner/scraper.py
import requests
from bs4 import BeautifulSoup
import re
import logging

logger = logging.getLogger(__name__)

def scrape_marmiton_recipe(url):
    """
    Scrape une recette depuis Marmiton
    
    Args:
        url (str): URL de la recette sur marmiton.org
        
    Returns:
        dict: Données de la recette ou None en cas d'erreur
    """
    try:
        # Vérifier que l'URL est bien de marmiton
        if 'marmiton.org' not in url:
            return None
        
        # Ajouter un user-agent pour éviter d'être bloqué
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Vérifier que la requête a réussi
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Initialiser le dictionnaire pour stocker les données
        recipe_data = {
            'name': '',
            'description': '',
            'preparation_time': None,
            'cooking_time': None,
            'servings': 4,  # Par défaut
            'instructions': '',
            'ingredients': []
        }
        
        # Extraire le nom de la recette
        recipe_name = soup.find('h1', class_='SHRD__sc-du9rd0-2')
        if recipe_name:
            recipe_data['name'] = recipe_name.text.strip()
        
        # Extraire la description
        description = soup.find('div', class_='RCP__sc-1wtzleh-1')
        if description:
            recipe_data['description'] = description.text.strip()
        
        # Extraire le temps de préparation et de cuisson
        times = soup.find_all('div', class_='SHRD__sc-du9rd0-2', attrs={'data-testid': re.compile('recipe-.*-time')})
        for time_div in times:
            time_text = time_div.text.strip()
            # Convertir le temps en minutes
            minutes = 0
            if 'h' in time_text:
                hours_match = re.search(r'(\d+)\s*h', time_text)
                if hours_match:
                    minutes += int(hours_match.group(1)) * 60
            
            minutes_match = re.search(r'(\d+)\s*min', time_text)
            if minutes_match:
                minutes += int(minutes_match.group(1))
            
            if 'préparation' in time_div.get('data-testid', ''):
                recipe_data['preparation_time'] = minutes
            elif 'cuisson' in time_div.get('data-testid', ''):
                recipe_data['cooking_time'] = minutes
        
        # Extraire le nombre de portions
        servings = soup.find('div', attrs={'data-testid': 'recipe-servings'})
        if servings:
            servings_text = servings.text.strip()
            servings_match = re.search(r'(\d+)', servings_text)
            if servings_match:
                recipe_data['servings'] = int(servings_match.group(1))
        
        # Extraire les instructions
        instructions = []
        steps = soup.find_all('div', class_='RCP__sc-1wtzleh-1')
        for step in steps:
            if step.find('p') and not step.find('div', class_='RCP__sc-1wtz3lp-0'):
                instructions.append(step.text.strip())
        
        recipe_data['instructions'] = '\n\n'.join(instructions)
        
        # Extraire les ingrédients
        ingredients = []
        ingredient_items = soup.find_all('div', attrs={'data-testid': 'ingredient-item'})
        for item in ingredient_items:
            quantity_div = item.find('div', attrs={'data-testid': 'ingredient-quantity'})
            unit_div = item.find('div', attrs={'data-testid': 'ingredient-unit'})
            ingredient_div = item.find('div', attrs={'data-testid': 'ingredient-name'})
            
            quantity = 1.0
            unit = None
            name = ''
            
            if quantity_div:
                quantity_text = quantity_div.text.strip()
                try:
                    # Gérer les fractions comme "1/2"
                    if '/' in quantity_text:
                        numerator, denominator = quantity_text.split('/')
                        quantity = float(numerator) / float(denominator)
                    else:
                        quantity = float(quantity_text.replace(',', '.'))
                except ValueError:
                    quantity = 1.0
            
            if unit_div:
                unit = unit_div.text.strip()
                
            if ingredient_div:
                name = ingredient_div.text.strip()
            
            if name:
                ingredients.append({
                    'name': name,
                    'quantity': quantity,
                    'unit': unit
                })
        
        recipe_data['ingredients'] = ingredients
        
        return recipe_data
        
    except Exception as e:
        logger.error(f"Erreur lors du scraping de {url}: {str(e)}")
        return None