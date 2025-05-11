# meal_planner/forms.py
from django import forms
from django.forms import inlineformset_factory
from .models import Recipe, RecipeIngredient, Meal, ShoppingList, Ingredient
from django.contrib.auth.models import User
from django_select2.forms import Select2Widget, Select2TagWidget
from django_select2 import forms as s2forms

class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = ['name', 'unit']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control ingredient-name', 'autocomplete': 'off'}),
            'unit': forms.TextInput(attrs={'class': 'form-control ingredient-unit'}),
        }


class RecipeIngredientForm(forms.ModelForm):
    ingredient = forms.ModelChoiceField(
        queryset=Ingredient.objects.all(),
        widget=Select2Widget(
            attrs={
                'class': 'form-control ingredient-select',
                'data-placeholder': 'Rechercher un ingrédient...',
                'data-minimum-input-length': 1,
            }
        ),
        required=True,
    )
    quantity = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    unit = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = RecipeIngredient
        fields = ['id', 'ingredient', 'quantity', 'unit']
        widgets = {
            'id': forms.HiddenInput(),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'unit': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.ingredient:
            self.fields['ingredient'].initial = self.instance.ingredient

    def clean(self):
        cleaned_data = super().clean()
        ingredient_value = cleaned_data.get('ingredient')
        
        # Handle 'new:X' values from Select2 tags
        if isinstance(ingredient_value, str) and ingredient_value.startswith('new:'):
            new_ingredient_name = ingredient_value.replace('new:', '')
            # Check if the ingredient already exists
            try:
                # Try to get existing ingredient
                ingredient = Ingredient.objects.get(name__iexact=new_ingredient_name)
            except Ingredient.DoesNotExist:
                # Create a new ingredient
                ingredient = Ingredient.objects.create(
                    name=new_ingredient_name,
                    unit=cleaned_data.get('unit', '')
                )
            
            cleaned_data['ingredient'] = ingredient
        
        return cleaned_data


# FormSet pour gérer plusieurs ingrédients dans une recette
RecipeIngredientFormSet = inlineformset_factory(
    Recipe, RecipeIngredient,
    form=RecipeIngredientForm,
    min_num=1,
    extra=1,  # Nombre de formulaires vides à afficher
    can_delete=True
)


class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ['name', 'description', 'preparation_time', 'cooking_time', 'servings', 'instructions', 'source_url']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'preparation_time': forms.NumberInput(attrs={'class': 'form-control'}),
            'cooking_time': forms.NumberInput(attrs={'class': 'form-control'}),
            'servings': forms.NumberInput(attrs={'class': 'form-control'}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'source_url': forms.URLInput(attrs={'class': 'form-control'}),
        }
    

class MarmitonImportForm(forms.Form):
    url = forms.URLField(
        label="URL de la recette Marmiton",
        widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.marmiton.org/recettes/...'}),
        help_text="Copiez l'URL d'une recette depuis le site Marmiton"
    )


class MealForm(forms.ModelForm):
    class Meta:
        model = Meal
        fields = ['recipe', 'servings', 'cook', 'cleaner', 'meal_type']
        widgets = {
            'recipe': forms.Select(attrs={'class': 'form-select'}),
            'servings': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'cook': forms.Select(attrs={'class': 'form-select'}),
            'cleaner': forms.Select(attrs={'class': 'form-select'}),
            'meal_type': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super(MealForm, self).__init__(*args, **kwargs)
        self.fields['cook'].queryset = User.objects.all()
        self.fields['cleaner'].queryset = User.objects.all()
        self.fields['recipe'].queryset = Recipe.objects.all().order_by('name')


class ShoppingListForm(forms.ModelForm):
    class Meta:
        model = ShoppingList
        fields = ['title', 'start_date', 'end_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
