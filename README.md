# meal-planner

# Structure du projet

```
coloc_meal_planner/
├── coloc_meal_planner/  # Projet principal
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── meal_planner/  # Application principale
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── models.py
│   ├── scraper.py  # Scraper pour Marmiton
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── templates/  # Templates HTML
│   └── meal_planner/
│       ├── base.html
│       ├── calendar.html
│       ├── day_detail.html
│       ├── recipes.html
│       ├── recipe_form.html
│       └── shopping_list.html
├── static/  # Fichiers statiques
│   └── css/
│       └── style.css
│   └── js/
│       └── calendar.js
└── manage.py
```

# Installation et configuration initiale

```bash
# Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Installer les dépendances
pip install django
pip install requests
pip install beautifulsoup4
pip install python3-dateutil

# Créer le projet
django-admin startproject coloc_meal_planner
cd coloc_meal_planner

# Créer l'application
python3 manage.py startapp meal_planner

# Initialiser la base de données
python3 manage.py makemigrations
python3 manage.py migrate

# Créer un superutilisateur
python3 manage.py createsuperuser

# Lancer le serveur
python3 manage.py runserver
```