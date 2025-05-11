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
from django.utils import timezone

import calendar
from datetime import datetime, timedelta, date
from calendar import HTMLCalendar
from dateutil.relativedelta import relativedelta
import json

from .models import Recipe, Ingredient, RecipeIngredient, Meal, ShoppingList, ShoppingListItem, User
from .forms import RecipeForm, RecipeIngredientFormSet, MealForm, ShoppingListForm, MarmitonImportForm
from .scraper import scrape_marmiton_recipe

class CalendarView(LoginRequiredMixin, TemplateView):
    template_name = 'meal_planner/calendar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        week = self.request.GET.get('week', None)
        if week:
            try:
                d = datetime.strptime(week, '%Y-%m-%d').date()
            except ValueError:
                d = datetime.today().date()
        else:
            d = datetime.today().date()
        
        start_of_week = d - timedelta(days=d.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        cal = MealCalendar(start_of_week.year, start_of_week.month) 
        
        meals = Meal.objects.filter(
            date__gte=start_of_week,
            date__lte=end_of_week
        ).select_related('recipe', 'cook', 'cleaner')
        
        html_calendar = cal.formatweek(meals, start_of_week)
        
        prev_week = start_of_week - timedelta(days=7)
        next_week = start_of_week + timedelta(days=7)
        
        context['calendar'] = mark_safe(html_calendar)
        context['prev_week'] = f'week={prev_week.strftime("%Y-%m-%d")}'
        context['next_week'] = f'week={next_week.strftime("%Y-%m-%d")}'
        context['current_month'] = f"Semaine du {start_of_week.strftime('%d/%m/%Y')} au {end_of_week.strftime('%d/%m/%Y')}"
        
        context['meal_form'] = MealForm()
        context['all_recipes'] = Recipe.objects.all().order_by('name')
        context['all_users'] = User.objects.all().order_by('username')
        
        return context


def get_date(req_day):
    if req_day:
        year, month = (int(x) for x in req_day.split('-'))
        return date(year, month, day=1)
    return datetime.today().date()


def prev_month(d):
    prev_week = d - timedelta(days=7)
    month = 'month=' + prev_week.strftime("%Y-%m")
    return month


def next_month(d):
    next_week = d + timedelta(days=7)
    month = 'month=' + next_week.strftime("%Y-%m")
    return month


class MealCalendar(HTMLCalendar):
    def __init__(self, year=None, month=None):
        self.year = year
        self.month = month
        super(MealCalendar, self).__init__()
    
    def formatday(self, day_number, weekday, meals_for_week, current_day_date):
        """Return a day as a table cell.
        day_number: the day of the month (1-31)
        weekday: Monday is 0 and Sunday is 6
        meals_for_week: QuerySet of all meals for the displayed week
        current_day_date: the actual date object for this day cell
        """
        if day_number == 0:
            return "<td class='noday'>&nbsp;</td>"
            
        current_date = current_day_date
        
        meals_html = ""
        
        today = date.today()
        is_today = (current_date == today)
        
        day_class = 'day' + (' today' if is_today else '')
        
        for meal_type_value, meal_type_display in Meal.MEAL_TYPES:
            meal = meals_for_week.filter(date=current_date, meal_type=meal_type_value).first()
            
            meal_id = meal.id if meal else ''
            recipe_id = meal.recipe.id if meal and meal.recipe else ''
            servings = meal.servings if meal else 4
            cook_id = meal.cook.id if meal and meal.cook else ''
            cleaner_id = meal.cleaner.id if meal and meal.cleaner else ''
            meal_exists = 'true' if meal else 'false'

            data_attrs = (
                f'data-date="{current_date.isoformat()}" '
                f'data-meal-type="{meal_type_value}" '
                f'data-meal-type-display="{meal_type_display}" '
                f'data-meal-id="{meal_id}" '
                f'data-recipe-id="{recipe_id}" '
                f'data-servings="{servings}" '
                f'data-cook-id="{cook_id}" '
                f'data-cleaner-id="{cleaner_id}" '
                f'data-meal-exists="{meal_exists}"'
            )
            
            if meal:
                meals_html += f"<div class='meal meal-card-trigger {meal.meal_type}' {data_attrs}>"
                meals_html += f"<strong>{meal.get_meal_type_display()}</strong><br>"
                meals_html += f"{meal.recipe.name}<br>"
                meals_html += f"<small>{meal.servings} pers.</small>"
                meals_html += "</div>"
            else:
                meals_html += f"<div class='meal meal-card-trigger meal-empty {meal_type_value}' {data_attrs}>"
                meals_html += f"<strong>{meal_type_display}</strong><br>"
                meals_html += f"<small>Ajouter un repas</small>"
                meals_html += "</div>"
        
        return f"<td class='{day_class}'><span class='date'>{current_date.day}</span>{meals_html}</td>"
    
    def formatweek(self, meals_for_week, start_of_week_date):
        """Return a complete week as a table.
        start_of_week_date: date object for the Monday of the week.
        """
        cal = '<table border="0" cellpadding="0" cellspacing="0" class="calendar">\n'
        cal += self.formatweekheader() + '\n'
        
        week_html = ''
        for i in range(7):
            current_day_date = start_of_week_date + timedelta(days=i)
            week_html += self.formatday(current_day_date.day, current_day_date.weekday(), meals_for_week, current_day_date)
        
        cal += f'<tr>{week_html}</tr>\n'
        return cal + '</table>'
    
    def formatweekheader(self):
        """Return a header for a week as a table row."""
        s = ''.join(self.formatweekday(i) for i in self.iterweekdays())
        return '<tr class="weekday">' + s + '</tr>'
    
    def formatweekday(self, day):
        """Return a weekday name as a table header."""
        days = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
        return f'<th class="{self.cssclasses_weekday_head[day]}">{days[day]}</th>'


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
        print("request.POST")
        print(request.POST)
        print(kwargs)
        year = self.kwargs.get('year')
        month = self.kwargs.get('month')
        day = self.kwargs.get('day')
        
        current_date = date(year, month, day)
        
        # Détermine le type de repas à partir du bouton cliqué
        meal_type = None
        action = None

        for key in request.POST:
            if key.startswith('save_'):
                meal_type = key.replace('save_', '')
                action = 'save'
                break
            elif key.startswith('delete_'):
                meal_type = key.replace('delete_', '')
                action = 'delete'
                break
        
        if meal_type and action:
            try:
                meal_instance = Meal.objects.get(date=current_date, meal_type=meal_type)
                
                if action == 'delete':
                    meal_instance.delete()
                    # Optionally, add a Django message here: messages.success(request, 'Repas supprimé avec succès.')
                    return redirect('meal_planner:day_detail', year=year, month=month, day=day)
                
                # If action is 'save' (or falls through if not delete)
                form = MealForm(request.POST, instance=meal_instance, prefix=meal_type)
            except Meal.DoesNotExist:
                # This block should ideally only be hit for 'save' action if meal doesn't exist yet
                if action == 'delete': # Should not happen if delete button only shows for existing meals
                    # Optionally, add a Django message here: messages.error(request, 'Repas non trouvé pour la suppression.')
                    return redirect('meal_planner:day_detail', year=year, month=month, day=day)
                
                meal_instance = Meal(date=current_date, meal_type=meal_type) # For saving a new meal
                form = MealForm(request.POST, instance=meal_instance, prefix=meal_type)
            
            if action == 'save' and form.is_valid():
                form.save()
                # Optionally, add a Django message here: messages.success(request, 'Repas enregistré.')
            # else if action == 'save' and form is not valid, the errors will be in the form
            # and the page will be re-rendered with these errors by falling through to the redirect.
        
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

    def handle_new_ingredients(self, formset_data):
        """Handle new ingredients in the formset data and create them if needed."""
        # Create a copy of the POST data to modify
        modified_data = formset_data.copy()
        
        # Get the total number of forms
        total_forms = int(formset_data.get('ingredients-TOTAL_FORMS', 0))
        
        # Process each form in the formset
        for i in range(total_forms):
            ingredient_key = f'ingredients-{i}-ingredient'
            ingredient_value = formset_data.get(ingredient_key)
            
            # Check if this is a new ingredient (starts with 'new:')
            if ingredient_value and isinstance(ingredient_value, str) and ingredient_value.startswith('new:'):
                new_ingredient_name = ingredient_value.replace('new:', '')
                
                # Try to get existing ingredient first
                try:
                    ingredient = Ingredient.objects.get(name__iexact=new_ingredient_name)
                except Ingredient.DoesNotExist:
                    # Create new ingredient
                    unit = formset_data.get(f'ingredients-{i}-unit', '')
                    ingredient = Ingredient.objects.create(
                        name=new_ingredient_name,
                        unit=unit
                    )
                
                # Update the form data with the new ingredient's ID
                modified_data[ingredient_key] = str(ingredient.id)
        
        return modified_data

    def form_valid(self, form):
        context = self.get_context_data()
        ingredients_formset = context['ingredients_formset']
        
        if ingredients_formset.is_valid():
            self.object = form.save()
            ingredients_formset.instance = self.object
            ingredients_formset.save()
            return HttpResponseRedirect(self.get_success_url())
        else:
            # Handle new ingredients and try to validate again
            modified_data = self.handle_new_ingredients(self.request.POST)
            modified_formset = RecipeIngredientFormSet(modified_data, instance=self.object)
            
            if modified_formset.is_valid():
                self.object = form.save()
                modified_formset.instance = self.object
                modified_formset.save()
                return HttpResponseRedirect(self.get_success_url())
            else:
                # If still invalid, return the original form with errors
                print("ERRORS")
                print(form.errors)
                print(modified_formset.errors)
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
    """API endpoint for Select2 to search ingredients"""
    query = request.GET.get('q', '')
    
    if query:
        ingredients = Ingredient.objects.filter(name__icontains=query)
        results = [{'id': ingredient.id, 'name': ingredient.name} for ingredient in ingredients]
        return JsonResponse(results, safe=False)
    
    return JsonResponse([], safe=False)

@login_required
def ajax_save_meal(request):
    print(f"ajax_save_meal called with method: {request.method}") # Debug print
    if request.method == 'POST':
        form_data = request.POST.copy()
        meal_id = form_data.get('meal_id')
        
        if meal_id:
            try:
                meal_instance = Meal.objects.get(pk=meal_id) 
                form = MealForm(form_data, instance=meal_instance)
            except Meal.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Repas non trouvé.'}, status=404)
        else:
            form = MealForm(form_data)
        
        if form.is_valid():
            meal = form.save(commit=False)
            if not meal_id: # Only set date for new meals, for existing it's already on meal_instance
                date_str = form_data.get('date')
                if date_str:
                    try:
                        meal.date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        form.add_error(None, 'Format de date invalide.') # Add to non-field errors
                        return JsonResponse({'status': 'error', 'errors': form.errors.as_json()}, status=400)
                else:
                    form.add_error(None, 'La date est requise.') # Add to non-field errors
                    return JsonResponse({'status': 'error', 'errors': form.errors.as_json()}, status=400)
            
            meal.save()
            
            response_data = {
                'status': 'success',
                'meal_id': meal.id,
                'recipe_id': meal.recipe.id if meal.recipe else '',
                'recipe_name': meal.recipe.name if meal.recipe else 'Non spécifié',
                'servings': meal.servings,
                'cook_id': meal.cook.id if meal.cook else '',
                'cook_name': meal.cook.username if meal.cook else 'Non spécifié',
                'cleaner_id': meal.cleaner.id if meal.cleaner else '',
                'cleaner_name': meal.cleaner.username if meal.cleaner else 'Non spécifié',
                'meal_type': meal.meal_type,
                'meal_type_display': meal.get_meal_type_display(),
                'date': meal.date.isoformat()
            }
            return JsonResponse(response_data)
        else:
            # This is for form validation errors
            return JsonResponse({'status': 'error', 'errors': form.errors.as_json()}, status=400)
    
    # If not POST, or if other conditions lead here (which they shouldn't with proper structure)
    return JsonResponse({'status': 'error', 'message': f'Invalid request method: {request.method}. Only POST is allowed.'}, status=405)

@login_required
def ajax_delete_meal(request):
    if request.method == 'POST':
        meal_id = request.POST.get('meal_id')
        if not meal_id:
            return JsonResponse({'status': 'error', 'message': 'Meal ID manquant.'}, status=400)
        
        try:
            meal = get_object_or_404(Meal, pk=meal_id)
            # Optional: Check if the user has permission to delete this meal
            # For example, if you have a 'created_by' field on the Meal model:
            # if meal.created_by != request.user and not request.user.is_staff:
            #     return JsonResponse({'status': 'error', 'message': 'Permission refusée.'}, status=403)
            
            # Store details needed for UI update before deleting
            meal_date_iso = meal.date.isoformat()
            meal_type_value = meal.meal_type
            meal_type_display_text = meal.get_meal_type_display()

            meal.delete()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Repas supprimé avec succès.',
                'deleted_meal_info': { # Sending back info to help UI update
                    'date': meal_date_iso,
                    'meal_type': meal_type_value,
                    'meal_type_display': meal_type_display_text
                }
            })
        except Meal.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Repas non trouvé.'}, status=404)
        except Exception as e:
            # Log the exception e for server-side debugging
            print(f"Error deleting meal: {e}")
            return JsonResponse({'status': 'error', 'message': 'Une erreur est survenue lors de la suppression.'}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée.'}, status=405)