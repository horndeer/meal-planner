# meal_planner/urls.py
from django.urls import path
from . import views

app_name = 'meal_planner'

urlpatterns = [
    # Page d'accueil - Calendrier
    path('', views.CalendarView.as_view(), name='calendar'),
    
    # Détails du jour
    path('day/<int:year>/<int:month>/<int:day>/', views.DayDetailView.as_view(), name='day_detail'),
    
    # Gestion des recettes
    path('recipes/', views.RecipeListView.as_view(), name='recipes'),
    path('recipes/<int:pk>/', views.RecipeDetailView.as_view(), name='recipe_detail'),
    path('recipes/new/', views.RecipeCreateView.as_view(), name='recipe_create'),
    path('recipes/<int:pk>/edit/', views.RecipeUpdateView.as_view(), name='recipe_update'),
    path('recipes/import-marmiton/', views.import_marmiton_recipe, name='import_marmiton'),
    path('toggle-favorite/', views.toggle_favorite, name='toggle_favorite'),
    
    # Planning
    path('add-to-planning/<int:recipe_id>/<str:day>/', views.add_to_planning, name='add_to_planning'),
    path('add-to-planning/<int:recipe_id>/form/', views.add_to_planning_form, name='add_to_planning_form'),
    
    # Gestion des listes de courses
    path('shopping-lists/new/', views.ShoppingListCreateView.as_view(), name='shopping_list_create'),
    path('shopping-lists/<int:pk>/', views.ShoppingListDetailView.as_view(), name='shopping_list_detail'),
    path('shopping-items/<int:pk>/toggle/', views.toggle_shopping_item, name='toggle_shopping_item'),
    path('api/ingredients/', views.ingredients_api, name='ingredients_api'),
    
    # URL for saving meal from calendar modal
    path('ajax/save_meal/', views.ajax_save_meal, name='ajax_save_meal'),
]