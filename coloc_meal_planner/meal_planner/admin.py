# meal_planner/admin.py
from django.contrib import admin
from .models import Ingredient, Recipe, RecipeIngredient, Meal, ShoppingList, ShoppingListItem

class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 3

class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'preparation_time', 'cooking_time', 'servings', 'created_by', 'created_at')
    list_filter = ('created_at', 'created_by')
    search_fields = ('name', 'description')
    inlines = [RecipeIngredientInline]

class MealAdmin(admin.ModelAdmin):
    list_display = ('date', 'meal_type', 'recipe', 'servings', 'cook', 'cleaner')
    list_filter = ('date', 'meal_type', 'cook', 'cleaner')
    date_hierarchy = 'date'

class ShoppingListItemInline(admin.TabularInline):
    model = ShoppingListItem
    extra = 3

class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_date', 'end_date', 'created_by', 'created_at')
    list_filter = ('created_at', 'created_by')
    inlines = [ShoppingListItemInline]

class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit')
    search_fields = ('name',)

admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Meal, MealAdmin)
admin.site.register(ShoppingList, ShoppingListAdmin)
admin.site.register(ShoppingListItem)
