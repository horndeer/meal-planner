# meal_planner/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseRedirect
from django.utils.safestring import mark_safe
from django.db.models import Sum
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers import serialize

import calendar
from datetime import datetime, timedelta, date
from calendar import HTMLCalendar
from dateutil.relativedelta import relativedelta
import json

from .models import Recipe, Ingredient, RecipeIngredient, Meal, ShoppingList, ShoppingListItem
from .forms import RecipeForm, RecipeIngredientFormSet, MealForm, ShoppingListForm, MarmitonImportForm
from .scraper import scrape_marmiton_recipe

class CalendarView(LoginRequiredMixin, TemplateView):
    template_name = 'meal_planner/calendar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Récupérer la date actuelle ou celle spécifiée dans l'URL
        d = get_date(self.request.GET.get('month', None))
        cal = MealCalendar(d.year, d.month)
        
        # Récupérer tous les repas du mois
        meals = Meal.objects.filter(date__year=d.year, date__month=d.month)
        html_calendar = cal.formatmonth(meals, withyear=True)
        
        context['calendar'] = mark_safe(html_calendar)
        context['prev_month'] = prev_month(d)
        context['next_month'] = next_month(d)
        context['current_month'] = d.strftime("%B %Y")
        
        return context


def get_date(req_day):
    if req_day:
        year, month = (int(x) for x in req_day.split('-'))
        return date(year, month, day=1)
    return datetime.today().date()


def prev_month(d):
    first = d.replace(day=1)
    prev_month = first - timedelta(days=1)
    month = 'month=' + prev_month.strftime("%Y-%m")
    return month


def next_month(d):
    days_in_month = calendar.monthrange(d.year, d.month)[1]
    last = d.replace(day=days_in_month)
    next_month = last + timedelta(days=1)
    month = 'month=' + next_month.strftime("%Y-%m")
    return month


class MealCalendar(HTMLCalendar):
    def __init__(self, year=None, month=None):
        self.year = year
        self.month = month
        super(MealCalendar, self).__init__()
    
    def formatday(self, day, weekday, meals):
        """Return a day as a table cell."""
        day_meals = meals.filter(date__day=day)
        meals_html = ""
        
        for meal in day_meals:
            meals_html += f"<div class='meal {meal.meal_type}'>"
            meals_html += f"{meal.get_meal_type_display()}: {meal.recipe.name} ({meal.servings} pers.)"
            meals_html += "</div>"
        
        if day != 0:
            return f"<td class='day'><span class='date'>{day}</span>{meals_html}</td>"
        return "<td class='noday'>&nbsp;</td>"
    
    def formatweek(self, theweek, meals):
        """Return a complete week as a table row."""
        week = ''
        for d, weekday in theweek:
            week += self.formatday(d, weekday, meals)
        return f'<tr> {week} </tr>'
    
    def formatmonth(self, meals, withyear=True):
        """Return a formatted month as a table."""
        cal = f'<table border="0" cellpadding="0" cellspacing="0" class="calendar">\n'
        cal += f'{self.formatmonthname(self.year, self.month, withyear=withyear)}\n'
        cal += f'{self.formatweekheader()}\n'
        for week in self.monthdays2calendar(self.year, self.month):
            cal += f'{self.formatweek(week, meals)}\n'
        return cal + '</table>'


class DayDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'meal_planner/day_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        year = self.kwargs.get('year')
        month = self.kwargs.get('month')
        day = self.kwargs.get('day')
        
        current_date = date(year, month, day)
        
        # Récupérer les repas existants pour cette date
        meals = Meal.objects.filter(date=current_date)
        
        # Préparation des formulaires pour chaque type de repas
        meal_forms = {}
        for meal_type, meal_name in Meal.MEAL_TYPES:
            try:
                meal = meals.get(meal_type=meal_type)
                form = MealForm(instance=meal, prefix=meal_type)
            except Meal.DoesNotExist:
                meal = Meal(date=current_date, meal_type=meal_type)
                form = MealForm(instance=meal, prefix=meal_type)
            
            meal_forms[meal_type] = {
                'form': form,
                'name': meal_name,
                'exists': meal.pk is not None
            }
        
        context['date'] = current_date
        context['meal_forms'] = meal_forms
        context['prev_day'] = current_date - timedelta(days=1)
        context['next_day'] = current_date + timedelta(days=1)
        
        return context
    
    def post(self, request, *args, **kwargs):
        year = self.kwargs.get('year')
        month = self.kwargs.get('month')
        day = self.kwargs.get('day')
        
        current_date = date(year, month, day)
        
        # Détermine le type de repas à partir du bouton cliqué
        meal_type = None
        for key in request.POST:
            if key.startswith('save_'):
                meal_type = key.replace('save_', '')
                break
        
        if meal_type:
            try:
                meal = Meal.objects.get(date=current_date, meal_type=meal_type)
            except Meal.DoesNotExist:
                meal = Meal(date=current_date, meal_type=meal_type)
            
            form = MealForm(request.POST, instance=meal, prefix=meal_type)
            
            if form.is_valid():
                form.save()
        
        return redirect('meal_planner:day_detail', year=year, month=month, day=day)


class RecipeListView(LoginRequiredMixin, ListView):
    model = Recipe
    template_name = 'meal_planner/recipes.html'
    context_object_name = 'recipes'


class RecipeDetailView(LoginRequiredMixin, DetailView):
    model = Recipe
    template_name = 'meal_planner/recipe_detail.html'
    context_object_name = 'recipe'


class RecipeCreateView(LoginRequiredMixin, CreateView):
    model = Recipe
    form_class = RecipeForm
    template_name = 'meal_planner/recipe_form.html'
    success_url = reverse_lazy('meal_planner:recipes')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['ingredients_formset'] = RecipeIngredientFormSet(self.request.POST)
        else:
            context['ingredients_formset'] = RecipeIngredientFormSet()
        return context
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        context = self.get_context_data()
        ingredients_formset = context['ingredients_formset']
        
        if ingredients_formset.is_valid():
            self.object = form.save()
            ingredients_formset.instance = self.object
            
            # Gérer la création des nouveaux ingrédients
            for form in ingredients_formset.forms:
                if form.is_valid() and not form.cleaned_data.get('DELETE', False):
                    ingredient_data = form.cleaned_data.get('ingredient')
                    if isinstance(ingredient_data, str):
                        # C'est un nouvel ingrédient
                        ingredient = Ingredient.objects.create(
                            name=ingredient_data,
                            unit=form.cleaned_data.get('unit', '')
                        )
                        form.instance.ingredient = ingredient
            
            ingredients_formset.save()
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))


class RecipeUpdateView(LoginRequiredMixin, UpdateView):
    model = Recipe
    form_class = RecipeForm
    template_name = 'meal_planner/recipe_form.html'
    success_url = reverse_lazy('meal_planner:recipes')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['ingredients_formset'] = RecipeIngredientFormSet(self.request.POST, instance=self.object)
        else:
            context['ingredients_formset'] = RecipeIngredientFormSet(instance=self.object)
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        ingredients_formset = context['ingredients_formset']
        
        if ingredients_formset.is_valid():
            self.object = form.save()
            ingredients_formset.instance = self.object
            ingredients_formset.save()
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))


@login_required
def import_marmiton_recipe(request):
    if request.method == 'POST':
        form = MarmitonImportForm(request.POST)
        if form.is_valid():
            url = form.cleaned_data['url']
            
            # Utiliser le scraper pour récupérer les données de la recette
            recipe_data = scrape_marmiton_recipe(url)
            
            if recipe_data:
                # Créer la recette
                recipe = Recipe(
                    name=recipe_data['name'],
                    description=recipe_data['description'],
                    preparation_time=recipe_data['preparation_time'],
                    cooking_time=recipe_data['cooking_time'],
                    servings=recipe_data['servings'],
                    instructions=recipe_data['instructions'],
                    source_url=url,
                    created_by=request.user
                )
                recipe.save()
                
                # Ajouter les ingrédients
                for ingredient_data in recipe_data['ingredients']:
                    # Vérifier si l'ingrédient existe déjà
                    ingredient, created = Ingredient.objects.get_or_create(
                        name=ingredient_data['name'],
                        defaults={'unit': ingredient_data.get('unit')}
                    )
                    
                    # Créer la relation avec la recette
                    RecipeIngredient.objects.create(
                        recipe=recipe,
                        ingredient=ingredient,
                        quantity=ingredient_data['quantity'],
                        unit=ingredient_data.get('unit')
                    )
                
                return redirect('meal_planner:recipe_detail', pk=recipe.pk)
            else:
                form.add_error('url', "Impossible d'importer cette recette. Vérifiez l'URL et réessayez.")
    else:
        form = MarmitonImportForm()
    
    return render(request, 'meal_planner/import_marmiton.html', {'form': form})


class ShoppingListCreateView(LoginRequiredMixin, CreateView):
    model = ShoppingList
    form_class = ShoppingListForm
    template_name = 'meal_planner/shopping_list_form.html'
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        
        # Générer automatiquement les éléments de la liste
        self.generate_shopping_list(self.object)
        
        return response
    
    def generate_shopping_list(self, shopping_list):
        # Récupérer tous les repas dans la période
        meals = Meal.objects.filter(
            date__gte=shopping_list.start_date,
            date__lte=shopping_list.end_date
        ).select_related('recipe')
        
        # Dictionnaire pour stocker les quantités agrégées par ingrédient
        ingredients_dict = {}
        
        for meal in meals:
            recipe = meal.recipe
            ratio = meal.servings / recipe.servings  # Ratio pour ajuster les quantités
            
            for recipe_ingredient in recipe.ingredients.all():
                ingredient = recipe_ingredient.ingredient
                adjusted_quantity = recipe_ingredient.quantity * ratio
                
                if ingredient.id in ingredients_dict:
                    # Si l'ingrédient est déjà dans le dictionnaire, ajouter la quantité
                    if recipe_ingredient.unit == ingredients_dict[ingredient.id]['unit']:
                        ingredients_dict[ingredient.id]['quantity'] += adjusted_quantity
                    else:
                        # Si les unités sont différentes, on garde quand même mais séparément
                        # Dans une version plus avancée, on pourrait convertir les unités
                        key = f"{ingredient.id}_{recipe_ingredient.unit}"
                        if key in ingredients_dict:
                            ingredients_dict[key]['quantity'] += adjusted_quantity
                        else:
                            ingredients_dict[key] = {
                                'ingredient': ingredient,
                                'quantity': adjusted_quantity,
                                'unit': recipe_ingredient.unit
                            }
                else:
                    ingredients_dict[ingredient.id] = {
                        'ingredient': ingredient,
                        'quantity': adjusted_quantity,
                        'unit': recipe_ingredient.unit or ingredient.unit
                    }
        
        # Créer les éléments de la liste de courses
        for key, data in ingredients_dict.items():
            ShoppingListItem.objects.create(
                shopping_list=shopping_list,
                ingredient=data['ingredient'],
                quantity=data['quantity'],
                unit=data['unit']
            )


class ShoppingListDetailView(LoginRequiredMixin, DetailView):
    model = ShoppingList
    template_name = 'meal_planner/shopping_list_detail.html'
    context_object_name = 'shopping_list'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Regrouper les éléments par catégorie (future amélioration)
        items = self.object.items.all().order_by('ingredient__name')
        context['items'] = items
        
        return context


@login_required
def toggle_shopping_item(request, pk):
    """Toggle l'état d'achat d'un élément de la liste de courses"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        item = get_object_or_404(ShoppingListItem, pk=pk)
        item.purchased = not item.purchased
        item.save()
        return JsonResponse({'status': 'success', 'purchased': item.purchased})
    return JsonResponse({'status': 'error'}, status=400)

@csrf_exempt
@login_required
def toggle_favorite(request):
    if request.method == 'POST':
        recipe_id = request.POST.get('recipe_id')
        recipe = get_object_or_404(Recipe, id=recipe_id)
        recipe.is_favorite = not recipe.is_favorite
        recipe.save()
        return JsonResponse({'status': 'success', 'is_favorite': recipe.is_favorite})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def add_to_planning(request, recipe_id, day):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    
    if day == 'today':
        target_date = date.today()
    elif day == 'tomorrow':
        target_date = date.today() + timedelta(days=1)
    else:
        return HttpResponseRedirect(reverse('meal_planner:calendar'))
    
    # Create a new meal for the recipe
    meal = Meal.objects.create(
        date=target_date,
        recipe=recipe,
        meal_type='dinner',  # Default to dinner, can be changed later
        servings=recipe.servings
    )
    
    return HttpResponseRedirect(reverse('meal_planner:day_detail', 
                                      kwargs={'year': target_date.year,
                                             'month': target_date.month,
                                             'day': target_date.day}))

@login_required
def add_to_planning_form(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    
    if request.method == 'POST':
        target_date = request.POST.get('date')
        meal_type = request.POST.get('meal_type')
        servings = request.POST.get('servings', recipe.servings)
        
        if target_date and meal_type:
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            meal = Meal.objects.create(
                date=target_date,
                recipe=recipe,
                meal_type=meal_type,
                servings=servings
            )
            return HttpResponseRedirect(reverse('meal_planner:day_detail',
                                              kwargs={'year': target_date.year,
                                                     'month': target_date.month,
                                                     'day': target_date.day}))
    
    return render(request, 'meal_planner/add_to_planning_form.html', {
        'recipe': recipe,
        'meal_types': Meal.MEAL_TYPES
    })

@login_required
def ingredients_api(request):
    """API endpoint to get the list of ingredients"""
    ingredients = Ingredient.objects.all().order_by('name')
    data = [{
        'name': ing.name,
        'unit': ing.unit or ''
    } for ing in ingredients]
    return JsonResponse(data, safe=False)