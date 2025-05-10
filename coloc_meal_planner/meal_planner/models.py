
# meal_planner/models.py
from django.db import models
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse


class Ingredient(models.Model):
    name = models.CharField(max_length=100)
    unit = models.CharField(max_length=20, blank=True, null=True)  # g, ml, pièce, etc.
    
    def __str__(self):
        return self.name


class Recipe(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    preparation_time = models.IntegerField(help_text="Temps de préparation en minutes", blank=True, null=True)
    cooking_time = models.IntegerField(help_text="Temps de cuisson en minutes", blank=True, null=True)
    servings = models.IntegerField(default=4, help_text="Nombre de portions")
    instructions = models.TextField()
    source_url = models.URLField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('meal_planner:recipe_detail', kwargs={'pk': self.pk})


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ingredients')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.FloatField()
    unit = models.CharField(max_length=20, blank=True, null=True)  # Permet override de l'unité par défaut
    
    def __str__(self):
        return f"{self.quantity} {self.unit or self.ingredient.unit or ''} {self.ingredient.name}"


class Meal(models.Model):
    MEAL_TYPES = [
        # ('breakfast', 'Petit-déjeuner'),
        ('lunch', 'Déjeuner'),
        ('dinner', 'Dîner'),
    ]
    
    date = models.DateField()
    meal_type = models.CharField(max_length=10, choices=MEAL_TYPES, default='dinner')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='meals')
    servings = models.IntegerField(default=4, help_text="Nombre de personnes qui mangent")
    cook = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='cooking')
    cleaner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='cleaning')
    
    class Meta:
        unique_together = ['date', 'meal_type']  # Un seul repas par type et par jour
    
    def __str__(self):
        return f"{self.get_meal_type_display()} du {self.date.strftime('%d/%m/%Y')} - {self.recipe.name}"
    
    def get_absolute_url(self):
        return reverse('meal_planner:day_detail', kwargs={'year': self.date.year, 
                                                       'month': self.date.month, 
                                                       'day': self.date.day})


class ShoppingList(models.Model):
    title = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Liste du {self.start_date.strftime('%d/%m/%Y')} au {self.end_date.strftime('%d/%m/%Y')}"
    
    def get_absolute_url(self):
        return reverse('meal_planner:shopping_list_detail', kwargs={'pk': self.pk})


class ShoppingListItem(models.Model):
    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE, related_name='items')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.FloatField()
    unit = models.CharField(max_length=20, blank=True, null=True)
    purchased = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.quantity} {self.unit or self.ingredient.unit or ''} {self.ingredient.name}"
