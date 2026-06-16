import json

from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import MentalHealthScore, PhysicalHealthScore, RegisterUser


def _physical_history(request, user):
    """Return all saved scores, importing legacy session scores once."""
    if not request.session.get('physical_history_imported'):
        for entry in request.session.get('physical_history', []):
            try:
                score = max(0, min(100, int(entry.get('score'))))
            except (AttributeError, TypeError, ValueError):
                continue

            result = PhysicalHealthScore.objects.create(user=user, score=score)
            recorded_at = parse_datetime(entry.get('ts', '')) if isinstance(entry, dict) else None
            if recorded_at:
                if timezone.is_naive(recorded_at):
                    recorded_at = timezone.make_aware(recorded_at)
                PhysicalHealthScore.objects.filter(pk=result.pk).update(recorded_at=recorded_at)

        request.session['physical_history_imported'] = True
        request.session.pop('physical_history', None)

    return [
        {'ts': entry.recorded_at.isoformat(), 'score': entry.score}
        for entry in user.physical_scores.all()
    ]


def _mental_history(user):
    return [
        {'ts': entry.recorded_at.isoformat(), 'score': entry.score}
        for entry in user.mental_scores.all()
    ]


def _exercise_recommendation(user, history):
    scores = [entry['score'] for entry in history]
    latest_score = scores[-1] if scores else None
    average_score = round(sum(scores) / len(scores), 1) if scores else None
    progress = latest_score - scores[0] if len(scores) > 1 else None
    goal = (user.goal or 'Stay Fit').strip()
    normalized_goal = goal.lower()

    if 'gain' in normalized_goal or 'muscle' in normalized_goal or 'strength' in normalized_goal:
        focus_title = 'Strength and Muscle Gain'
        focus_text = 'Build strength steadily with resistance work and enough recovery between sessions.'
        exercises = [
            'Squats or goblet squats: 3 sets of 8-12 reps',
            'Push-ups or chest press: 3 sets of 8-12 reps',
            'Resistance-band rows or dumbbell rows: 3 sets of 10 reps',
            'Glute bridges and plank: 2-3 controlled sets',
        ]
        goal_tips = [
            'Prioritize good technique before adding repetitions or resistance.',
            'Leave a recovery day between demanding full-body strength sessions.',
        ]
    elif 'loss' in normalized_goal or 'lose' in normalized_goal or 'reduce' in normalized_goal:
        focus_title = 'Active Weight Management'
        focus_text = 'Combine calorie-burning movement with strength exercises that support consistency.'
        exercises = [
            'Brisk walking or cycling intervals: 20-30 minutes',
            'Squat-to-chair and step-ups: 3 rounds of 10 reps',
            'Incline push-ups and rows: 3 rounds of 8-12 reps',
            'Core work followed by a gentle five-minute walk',
        ]
        goal_tips = [
            'Choose a pace you can repeat throughout the week instead of one exhausting workout.',
            'Add daily walking gradually and keep at least one easy recovery day.',
        ]
    else:
        focus_title = 'Balanced Fitness'
        focus_text = 'Maintain fitness with a practical mix of cardio, mobility, and strength.'
        exercises = [
            'Brisk walk, jog, or cycling: 20-30 minutes',
            'Squats, push-ups, and rows: 2-3 rounds',
            'Plank or dead bug core exercise: 2 controlled sets',
            'Mobility stretching: 5-10 minutes after activity',
        ]
        goal_tips = [
            'Rotate cardio and strength days to keep the routine balanced.',
            'Increase time or repetitions gradually when sessions feel comfortable.',
        ]

    if latest_score is None:
        readiness = 'Starter Baseline'
        schedule = 'Begin with 3 easy sessions this week, 15-20 minutes each.'
        score_tip = 'Complete a physical health calculation to tune this plan to your current readiness.'
    elif latest_score < 50:
        readiness = 'Recovery First'
        schedule = 'Use 2-3 light sessions this week, 10-20 minutes each.'
        score_tip = 'Your latest score is low, so use low-impact movements and focus on sleep and hydration before increasing intensity.'
    elif latest_score < 70:
        readiness = 'Foundation Build'
        schedule = 'Plan 3 moderate sessions this week, 20-30 minutes each.'
        score_tip = 'Build consistency first and only add effort when recovery feels steady.'
    elif latest_score < 85:
        readiness = 'Steady Progress'
        schedule = 'Plan 3-4 moderate sessions this week, 25-40 minutes each.'
        score_tip = 'Your score supports gradual progression: add a few minutes or a small set each week.'
    else:
        readiness = 'Ready To Progress'
        schedule = 'Plan 4 sessions this week, mixing harder days with active recovery.'
        score_tip = 'Your latest score is strong; progress one variable at a time and keep recovery days.'

    return {
        'goal': goal,
        'focus_title': focus_title,
        'focus_text': focus_text,
        'exercises': exercises,
        'tips': [score_tip] + goal_tips + [
            'Warm up for 5-10 minutes and stop if you develop pain, dizziness, or unusual symptoms.',
        ],
        'readiness': readiness,
        'schedule': schedule,
        'has_score': latest_score is not None,
        'score_display': f'{latest_score}/100' if latest_score is not None else 'No score yet',
        'average_display': f'{average_score}/100' if average_score is not None else 'No history',
        'progress_display': (
            f'{progress:+d} points' if progress is not None else 'Need 2 scores'
        ),
        'benchmark': 80,
    }


FOOD_NUTRITION_LIST = [
    {'name': 'Oats (dry)', 'category': 'Grain', 'calories': 389, 'protein': '16.9 g', 'carbs': '66.3 g', 'fat': '6.9 g', 'fiber': '10.6 g'},
    {'name': 'Brown rice (cooked)', 'category': 'Grain', 'calories': 123, 'protein': '2.7 g', 'carbs': '25.6 g', 'fat': '1.0 g', 'fiber': '1.6 g'},
    {'name': 'Whole wheat bread', 'category': 'Grain', 'calories': 247, 'protein': '13.0 g', 'carbs': '41.0 g', 'fat': '3.4 g', 'fiber': '7.0 g'},
    {'name': 'Chicken breast (cooked)', 'category': 'Protein', 'calories': 165, 'protein': '31.0 g', 'carbs': '0.0 g', 'fat': '3.6 g', 'fiber': '0.0 g'},
    {'name': 'Egg (whole)', 'category': 'Protein', 'calories': 143, 'protein': '12.6 g', 'carbs': '0.7 g', 'fat': '9.5 g', 'fiber': '0.0 g'},
    {'name': 'Paneer', 'category': 'Protein', 'calories': 265, 'protein': '18.3 g', 'carbs': '1.2 g', 'fat': '20.8 g', 'fiber': '0.0 g'},
    {'name': 'Tofu (firm)', 'category': 'Protein', 'calories': 144, 'protein': '17.3 g', 'carbs': '2.8 g', 'fat': '8.7 g', 'fiber': '2.3 g'},
    {'name': 'Lentils (cooked)', 'category': 'Protein', 'calories': 116, 'protein': '9.0 g', 'carbs': '20.1 g', 'fat': '0.4 g', 'fiber': '7.9 g'},
    {'name': 'Chickpeas (cooked)', 'category': 'Protein', 'calories': 164, 'protein': '8.9 g', 'carbs': '27.4 g', 'fat': '2.6 g', 'fiber': '7.6 g'},
    {'name': 'Milk (whole)', 'category': 'Dairy', 'calories': 61, 'protein': '3.2 g', 'carbs': '4.8 g', 'fat': '3.3 g', 'fiber': '0.0 g'},
    {'name': 'Greek yogurt (plain)', 'category': 'Dairy', 'calories': 97, 'protein': '9.0 g', 'carbs': '3.9 g', 'fat': '5.0 g', 'fiber': '0.0 g'},
    {'name': 'Banana', 'category': 'Fruit', 'calories': 89, 'protein': '1.1 g', 'carbs': '22.8 g', 'fat': '0.3 g', 'fiber': '2.6 g'},
    {'name': 'Apple', 'category': 'Fruit', 'calories': 52, 'protein': '0.3 g', 'carbs': '13.8 g', 'fat': '0.2 g', 'fiber': '2.4 g'},
    {'name': 'Orange', 'category': 'Fruit', 'calories': 47, 'protein': '0.9 g', 'carbs': '11.8 g', 'fat': '0.1 g', 'fiber': '2.4 g'},
    {'name': 'Spinach', 'category': 'Vegetable', 'calories': 23, 'protein': '2.9 g', 'carbs': '3.6 g', 'fat': '0.4 g', 'fiber': '2.2 g'},
    {'name': 'Broccoli', 'category': 'Vegetable', 'calories': 34, 'protein': '2.8 g', 'carbs': '6.6 g', 'fat': '0.4 g', 'fiber': '2.6 g'},
    {'name': 'Sweet potato (cooked)', 'category': 'Vegetable', 'calories': 90, 'protein': '2.0 g', 'carbs': '20.7 g', 'fat': '0.2 g', 'fiber': '3.3 g'},
    {'name': 'Almonds', 'category': 'Nuts', 'calories': 579, 'protein': '21.2 g', 'carbs': '21.6 g', 'fat': '49.9 g', 'fiber': '12.5 g'},
    {'name': 'Peanut butter', 'category': 'Nuts', 'calories': 588, 'protein': '25.1 g', 'carbs': '20.0 g', 'fat': '50.4 g', 'fiber': '6.0 g'},
    {'name': 'Avocado', 'category': 'Healthy fat', 'calories': 160, 'protein': '2.0 g', 'carbs': '8.5 g', 'fat': '14.7 g', 'fiber': '6.7 g'},
]

FOOD_NUTRITION_LIST.extend([
    {
        'name': name,
        'category': category,
        'calories': calories,
        'protein': f'{protein:.1f} g',
        'carbs': f'{carbs:.1f} g',
        'fat': f'{fat:.1f} g',
        'fiber': f'{fiber:.1f} g',
    }
    for name, category, calories, protein, carbs, fat, fiber in [
        # Grains and staple carbohydrates
        ('White rice (cooked)', 'Grain', 130, 2.4, 28.2, 0.3, 0.4),
        ('Basmati rice (cooked)', 'Grain', 121, 3.5, 25.2, 0.4, 0.4),
        ('Quinoa (cooked)', 'Grain', 120, 4.4, 21.3, 1.9, 2.8),
        ('Barley (cooked)', 'Grain', 123, 2.3, 28.2, 0.4, 3.8),
        ('Bulgur (cooked)', 'Grain', 83, 3.1, 18.6, 0.2, 4.5),
        ('Couscous (cooked)', 'Grain', 112, 3.8, 23.2, 0.2, 1.4),
        ('Millet (cooked)', 'Grain', 119, 3.5, 23.7, 1.0, 1.3),
        ('Rye bread', 'Grain', 259, 8.5, 48.3, 3.3, 5.8),
        ('Multigrain bread', 'Grain', 265, 13.4, 43.3, 4.2, 7.4),
        ('Pasta (cooked)', 'Grain', 158, 5.8, 30.9, 0.9, 1.8),
        ('Whole wheat pasta (cooked)', 'Grain', 149, 6.0, 30.1, 1.7, 3.9),
        ('Poha (cooked)', 'Grain', 130, 2.6, 27.0, 1.3, 1.1),
        ('Idli', 'Grain', 146, 4.5, 30.4, 0.7, 1.5),
        ('Dosa (plain)', 'Grain', 184, 4.0, 28.0, 6.0, 1.0),
        ('Chapati (whole wheat)', 'Grain', 297, 9.6, 46.4, 7.5, 7.1),
        # Protein foods and legumes
        ('Turkey breast (cooked)', 'Protein', 135, 29.0, 0.0, 1.6, 0.0),
        ('Salmon (cooked)', 'Protein', 206, 22.1, 0.0, 12.4, 0.0),
        ('Tuna (canned in water)', 'Protein', 116, 25.5, 0.0, 0.8, 0.0),
        ('Sardines (canned)', 'Protein', 208, 24.6, 0.0, 11.5, 0.0),
        ('Shrimp (cooked)', 'Protein', 99, 24.0, 0.2, 0.3, 0.0),
        ('Mackerel (cooked)', 'Protein', 262, 23.9, 0.0, 17.8, 0.0),
        ('Cod (cooked)', 'Protein', 105, 22.8, 0.0, 0.9, 0.0),
        ('Beef lean (cooked)', 'Protein', 217, 26.1, 0.0, 11.8, 0.0),
        ('Pork loin (cooked)', 'Protein', 242, 27.3, 0.0, 13.9, 0.0),
        ('Lamb (cooked)', 'Protein', 258, 25.6, 0.0, 16.5, 0.0),
        ('Egg white', 'Protein', 52, 10.9, 0.7, 0.2, 0.0),
        ('Black beans (cooked)', 'Protein', 132, 8.9, 23.7, 0.5, 8.7),
        ('Kidney beans (cooked)', 'Protein', 127, 8.7, 22.8, 0.5, 6.4),
        ('Pinto beans (cooked)', 'Protein', 143, 9.0, 26.2, 0.7, 9.0),
        ('Soybeans (cooked)', 'Protein', 173, 16.6, 9.9, 9.0, 6.0),
        ('Edamame (cooked)', 'Protein', 121, 11.9, 8.9, 5.2, 5.2),
        ('Green peas (cooked)', 'Protein', 84, 5.4, 15.6, 0.2, 5.5),
        ('Mung beans (cooked)', 'Protein', 105, 7.0, 19.2, 0.4, 7.6),
        ('Black gram (cooked)', 'Protein', 116, 7.5, 20.5, 0.5, 7.0),
        ('Pigeon peas (cooked)', 'Protein', 121, 6.8, 23.3, 0.4, 6.7),
        ('Tempeh', 'Protein', 193, 20.3, 7.6, 10.8, 0.0),
        ('Seitan', 'Protein', 143, 24.9, 6.0, 2.0, 0.5),
        ('Cottage cheese', 'Protein', 98, 11.1, 3.4, 4.3, 0.0),
        ('Moong dal (cooked)', 'Protein', 106, 7.0, 19.0, 0.4, 7.0),
        ('Masoor dal (cooked)', 'Protein', 116, 9.0, 20.1, 0.4, 7.9),
        ('Rajma curry', 'Protein', 124, 6.8, 18.5, 2.8, 5.6),
        ('Chana dal (cooked)', 'Protein', 160, 8.9, 27.0, 2.6, 7.5),
        ('Crab (cooked)', 'Protein', 97, 19.4, 0.0, 1.5, 0.0),
        # Dairy and alternatives
        ('Milk (skim)', 'Dairy', 34, 3.4, 5.0, 0.1, 0.0),
        ('Milk (low-fat)', 'Dairy', 42, 3.4, 5.0, 1.0, 0.0),
        ('Soy milk (unsweetened)', 'Dairy alternative', 33, 2.9, 1.7, 1.6, 0.3),
        ('Curd (plain)', 'Dairy', 61, 3.5, 4.7, 3.3, 0.0),
        ('Cheddar cheese', 'Dairy', 403, 24.9, 1.3, 33.1, 0.0),
        ('Mozzarella cheese', 'Dairy', 280, 27.5, 3.1, 17.1, 0.0),
        ('Feta cheese', 'Dairy', 264, 14.2, 4.1, 21.3, 0.0),
        ('Ricotta cheese', 'Dairy', 174, 11.3, 3.0, 13.0, 0.0),
        ('Buttermilk', 'Dairy', 40, 3.3, 4.8, 0.9, 0.0),
        ('Whey protein powder', 'Protein supplement', 400, 78.0, 8.0, 6.0, 0.0),
        ('Yogurt (low-fat plain)', 'Dairy', 63, 5.3, 7.0, 1.6, 0.0),
        ('Ghee', 'Healthy fat', 900, 0.0, 0.0, 100.0, 0.0),
        # Fruits
        ('Grapes', 'Fruit', 69, 0.7, 18.1, 0.2, 0.9),
        ('Mango', 'Fruit', 60, 0.8, 15.0, 0.4, 1.6),
        ('Papaya', 'Fruit', 43, 0.5, 10.8, 0.3, 1.7),
        ('Pineapple', 'Fruit', 50, 0.5, 13.1, 0.1, 1.4),
        ('Watermelon', 'Fruit', 30, 0.6, 7.6, 0.2, 0.4),
        ('Cantaloupe', 'Fruit', 34, 0.8, 8.2, 0.2, 0.9),
        ('Strawberry', 'Fruit', 32, 0.7, 7.7, 0.3, 2.0),
        ('Blueberry', 'Fruit', 57, 0.7, 14.5, 0.3, 2.4),
        ('Raspberry', 'Fruit', 52, 1.2, 11.9, 0.7, 6.5),
        ('Blackberry', 'Fruit', 43, 1.4, 9.6, 0.5, 5.3),
        ('Guava', 'Fruit', 68, 2.6, 14.3, 1.0, 5.4),
        ('Kiwi fruit', 'Fruit', 61, 1.1, 14.7, 0.5, 3.0),
        ('Pear', 'Fruit', 57, 0.4, 15.2, 0.1, 3.1),
        ('Peach', 'Fruit', 39, 0.9, 9.5, 0.3, 1.5),
        ('Plum', 'Fruit', 46, 0.7, 11.4, 0.3, 1.4),
        ('Pomegranate arils', 'Fruit', 83, 1.7, 18.7, 1.2, 4.0),
        ('Dates (dried)', 'Fruit', 282, 2.5, 75.0, 0.4, 8.0),
        ('Raisins', 'Fruit', 299, 3.1, 79.2, 0.5, 3.7),
        ('Fig (fresh)', 'Fruit', 74, 0.8, 19.2, 0.3, 2.9),
        ('Apricot', 'Fruit', 48, 1.4, 11.1, 0.4, 2.0),
        ('Cherries', 'Fruit', 63, 1.1, 16.0, 0.2, 2.1),
        ('Lemon', 'Fruit', 29, 1.1, 9.3, 0.3, 2.8),
        ('Lime', 'Fruit', 30, 0.7, 10.5, 0.2, 2.8),
        ('Coconut meat (raw)', 'Fruit', 354, 3.3, 15.2, 33.5, 9.0),
        ('Jackfruit', 'Fruit', 95, 1.7, 23.3, 0.6, 1.5),
        ('Lychee', 'Fruit', 66, 0.8, 16.5, 0.4, 1.3),
        ('Dragon fruit', 'Fruit', 57, 0.4, 13.0, 0.1, 3.1),
        ('Passion fruit', 'Fruit', 97, 2.2, 23.4, 0.7, 10.4),
        ('Prunes (dried)', 'Fruit', 240, 2.2, 63.9, 0.4, 7.1),
        ('Tangerine', 'Fruit', 53, 0.8, 13.3, 0.3, 1.8),
        ('Custard apple', 'Fruit', 94, 2.1, 23.6, 0.3, 4.4),
        # Vegetables
        ('Carrot', 'Vegetable', 41, 0.9, 9.6, 0.2, 2.8),
        ('Tomato', 'Vegetable', 18, 0.9, 3.9, 0.2, 1.2),
        ('Cucumber', 'Vegetable', 15, 0.7, 3.6, 0.1, 0.5),
        ('Bell pepper (red)', 'Vegetable', 31, 1.0, 6.0, 0.3, 2.1),
        ('Cauliflower', 'Vegetable', 25, 1.9, 5.0, 0.3, 2.0),
        ('Cabbage', 'Vegetable', 25, 1.3, 5.8, 0.1, 2.5),
        ('Kale', 'Vegetable', 35, 2.9, 4.4, 1.5, 4.1),
        ('Romaine lettuce', 'Vegetable', 17, 1.2, 3.3, 0.3, 2.1),
        ('Beetroot', 'Vegetable', 43, 1.6, 9.6, 0.2, 2.8),
        ('Pumpkin', 'Vegetable', 26, 1.0, 6.5, 0.1, 0.5),
        ('Zucchini', 'Vegetable', 17, 1.2, 3.1, 0.3, 1.0),
        ('Eggplant', 'Vegetable', 25, 1.0, 5.9, 0.2, 3.0),
        ('Okra', 'Vegetable', 33, 1.9, 7.5, 0.2, 3.2),
        ('Green beans', 'Vegetable', 31, 1.8, 7.0, 0.2, 2.7),
        ('Asparagus', 'Vegetable', 20, 2.2, 3.9, 0.1, 2.1),
        ('Mushroom (white)', 'Vegetable', 22, 3.1, 3.3, 0.3, 1.0),
        ('Onion', 'Vegetable', 40, 1.1, 9.3, 0.1, 1.7),
        ('Garlic', 'Vegetable', 149, 6.4, 33.1, 0.5, 2.1),
        ('Ginger root', 'Vegetable', 80, 1.8, 17.8, 0.8, 2.0),
        ('Potato (boiled)', 'Vegetable', 87, 1.9, 20.1, 0.1, 1.8),
        ('Sweet corn (boiled)', 'Vegetable', 96, 3.4, 21.0, 1.5, 2.4),
        ('Bottle gourd', 'Vegetable', 14, 0.6, 3.4, 0.0, 0.5),
        ('Ridge gourd', 'Vegetable', 20, 1.2, 4.4, 0.2, 1.1),
        ('Bitter gourd', 'Vegetable', 17, 1.0, 3.7, 0.2, 2.8),
        ('Drumstick pods', 'Vegetable', 37, 2.1, 8.5, 0.2, 3.2),
        ('Radish', 'Vegetable', 16, 0.7, 3.4, 0.1, 1.6),
        ('Turnip', 'Vegetable', 28, 0.9, 6.4, 0.1, 1.8),
        ('Celery', 'Vegetable', 14, 0.7, 3.0, 0.2, 1.6),
        ('Leek', 'Vegetable', 61, 1.5, 14.2, 0.3, 1.8),
        ('Brussels sprouts', 'Vegetable', 43, 3.4, 9.0, 0.3, 3.8),
        ('Yam (boiled)', 'Vegetable', 116, 1.5, 27.5, 0.1, 3.9),
        ('Cassava (boiled)', 'Vegetable', 112, 1.4, 27.8, 0.3, 1.8),
        ('Plantain (cooked)', 'Vegetable', 122, 1.3, 31.9, 0.4, 2.3),
        ('Bamboo shoots', 'Vegetable', 27, 2.6, 5.2, 0.3, 2.2),
        ('Parsnip', 'Vegetable', 75, 1.2, 18.0, 0.3, 4.9),
        ('Collard greens', 'Vegetable', 32, 3.0, 5.4, 0.6, 4.0),
        ('Swiss chard', 'Vegetable', 19, 1.8, 3.7, 0.2, 1.6),
        # Nuts, seeds, and fats
        ('Walnuts', 'Nuts', 654, 15.2, 13.7, 65.2, 6.7),
        ('Cashews', 'Nuts', 553, 18.2, 30.2, 43.9, 3.3),
        ('Pistachios', 'Nuts', 560, 20.2, 27.2, 45.3, 10.6),
        ('Hazelnuts', 'Nuts', 628, 15.0, 16.7, 60.8, 9.7),
        ('Pecans', 'Nuts', 691, 9.2, 13.9, 72.0, 9.6),
        ('Macadamia nuts', 'Nuts', 718, 7.9, 13.8, 75.8, 8.6),
        ('Sunflower seeds', 'Seeds', 584, 20.8, 20.0, 51.5, 8.6),
        ('Pumpkin seeds', 'Seeds', 559, 30.2, 10.7, 49.1, 6.0),
        ('Chia seeds', 'Seeds', 486, 16.5, 42.1, 30.7, 34.4),
        ('Flaxseeds', 'Seeds', 534, 18.3, 28.9, 42.2, 27.3),
        ('Sesame seeds', 'Seeds', 573, 17.7, 23.5, 49.7, 11.8),
        ('Hemp seeds', 'Seeds', 553, 31.6, 8.7, 48.8, 4.0),
        ('Tahini', 'Healthy fat', 595, 17.0, 21.2, 53.8, 9.3),
        ('Olive oil', 'Healthy fat', 884, 0.0, 0.0, 100.0, 0.0),
        ('Coconut oil', 'Healthy fat', 892, 0.0, 0.0, 100.0, 0.0),
        ('Mustard oil', 'Healthy fat', 884, 0.0, 0.0, 100.0, 0.0),
        ('Canola oil', 'Healthy fat', 884, 0.0, 0.0, 100.0, 0.0),
        ('Butter', 'Healthy fat', 717, 0.9, 0.1, 81.1, 0.0),
        ('Peanuts (roasted)', 'Nuts', 587, 24.4, 21.3, 49.7, 8.4),
        ('Coconut milk', 'Healthy fat', 230, 2.3, 5.5, 23.8, 2.2),
        ('Olives (green)', 'Healthy fat', 145, 1.0, 3.8, 15.3, 3.3),
        ('Dark chocolate (70%)', 'Treat', 598, 7.8, 45.9, 42.6, 10.9),
        ('Trail mix', 'Nuts', 462, 13.8, 44.9, 29.4, 6.4),
        # Common prepared foods
        ('Sambar', 'Prepared meal', 70, 3.5, 10.0, 1.8, 3.0),
        ('Dal tadka', 'Prepared meal', 140, 6.2, 17.0, 5.2, 5.0),
        ('Vegetable khichdi', 'Prepared meal', 120, 4.0, 20.0, 2.5, 2.5),
        ('Upma', 'Prepared meal', 125, 3.0, 22.0, 3.0, 2.0),
        ('Vegetable poha', 'Prepared meal', 145, 3.2, 24.0, 4.2, 2.2),
        ('Pongal', 'Prepared meal', 150, 4.2, 22.0, 5.0, 1.8),
        ('Curd rice', 'Prepared meal', 130, 3.8, 20.0, 3.8, 0.8),
        ('Lemon rice', 'Prepared meal', 175, 3.2, 29.0, 5.3, 1.5),
        ('Vegetable biryani', 'Prepared meal', 155, 3.6, 25.0, 4.5, 2.0),
        ('Chicken curry', 'Prepared meal', 180, 16.0, 4.0, 11.0, 1.0),
        ('Paneer tikka', 'Prepared meal', 230, 15.0, 5.0, 17.0, 1.0),
        ('Palak paneer', 'Prepared meal', 170, 8.5, 5.5, 13.0, 2.0),
        ('Chole curry', 'Prepared meal', 165, 7.5, 22.0, 5.0, 6.0),
        ('Mixed vegetable curry', 'Prepared meal', 95, 2.5, 12.0, 4.0, 3.0),
        ('Jowar roti', 'Prepared meal', 285, 8.5, 55.0, 3.0, 6.0),
        ('Bajra roti', 'Prepared meal', 300, 9.5, 53.0, 5.0, 8.0),
        ('Ragi porridge', 'Prepared meal', 95, 2.0, 19.0, 1.2, 2.5),
        ('Sprouted mung salad', 'Prepared meal', 80, 5.0, 13.0, 0.8, 3.5),
        ('Hummus', 'Prepared meal', 166, 7.9, 14.3, 9.6, 6.0),
        ('Falafel (baked)', 'Prepared meal', 210, 10.0, 28.0, 7.0, 7.0),
        ('Tomato soup', 'Prepared meal', 38, 1.0, 7.0, 0.7, 1.0),
        ('Vegetable soup', 'Prepared meal', 42, 1.6, 7.0, 0.8, 1.8),
        ('Chicken soup', 'Prepared meal', 50, 4.5, 3.5, 2.0, 0.5),
        ('Peanut chutney', 'Prepared meal', 300, 13.0, 15.0, 23.0, 5.0),
        ('Coconut chutney', 'Prepared meal', 220, 3.0, 8.0, 20.0, 5.0),
        ('Idiyappam', 'Prepared meal', 175, 2.5, 38.0, 0.5, 1.0),
        ('Appam', 'Prepared meal', 120, 2.0, 23.0, 2.2, 0.8),
        ('Uttapam', 'Prepared meal', 190, 4.5, 30.0, 5.5, 2.0),
        ('Besan chilla', 'Prepared meal', 190, 9.0, 22.0, 7.0, 4.0),
        ('Ragi dosa', 'Prepared meal', 170, 3.5, 29.0, 4.0, 3.0),
        ('Granola', 'Breakfast', 471, 10.0, 64.0, 20.0, 8.0),
        ('Popcorn (air-popped)', 'Snack', 387, 12.9, 77.9, 4.5, 14.5),
        ('Cornflakes', 'Breakfast', 357, 7.5, 84.0, 0.4, 3.3),
        ('Muesli', 'Breakfast', 360, 10.0, 68.0, 6.0, 8.0),
    ]
])


def _diet_recommendation(user, history):
    scores = [entry['score'] for entry in history]
    latest_score = scores[-1] if scores else None
    average_score = round(sum(scores) / len(scores), 1) if scores else None
    goal = (user.goal or 'Stay Fit').strip()
    normalized_goal = goal.lower()

    if 'gain' in normalized_goal or 'muscle' in normalized_goal or 'strength' in normalized_goal:
        title = 'Healthy Weight Gain Nutrition'
        strategy = 'Support your goal with regular meals that combine protein, carbohydrates, and energy-dense healthy fats.'
        meal_ideas = [
            'Breakfast: oats with milk, banana, peanut butter, and nuts.',
            'Lunch: rice or roti with lentils or chicken/paneer, vegetables, and yogurt.',
            'Snack: fruit smoothie with milk or yogurt and nut butter.',
            'Dinner: potatoes or rice with a protein source and cooked vegetables.',
        ]
        goal_tips = [
            'Add energy gradually with foods such as nuts, seeds, milk, paneer, or avocado.',
            'Include a protein source in each main meal to support strength-training recovery.',
        ]
    elif 'loss' in normalized_goal or 'lose' in normalized_goal or 'reduce' in normalized_goal:
        title = 'Balanced Weight Management Nutrition'
        strategy = 'Favor satisfying meals built around protein, vegetables, fiber-rich carbohydrates, and consistent portions.'
        meal_ideas = [
            'Breakfast: yogurt with fruit and oats, or eggs with vegetables.',
            'Lunch: lentils or lean protein with a large vegetable portion and moderate rice or roti.',
            'Snack: fruit, yogurt, or a measured portion of nuts.',
            'Dinner: vegetable-rich soup or stir-fry with tofu, paneer, eggs, or chicken.',
        ]
        goal_tips = [
            'Use protein and fiber at meals to support fullness and steady energy.',
            'Limit liquid calories and choose water most often during the day.',
        ]
    else:
        title = 'Balanced Daily Nutrition'
        strategy = 'Maintain your health with varied meals containing protein, colorful plants, whole grains, and healthy fats.'
        meal_ideas = [
            'Breakfast: oats, eggs, or yogurt with fruit.',
            'Lunch: grain or roti with protein and two vegetable choices.',
            'Snack: fruit with yogurt or a small portion of nuts.',
            'Dinner: a balanced home-cooked meal with protein and vegetables.',
        ]
        goal_tips = [
            'Rotate protein and vegetable choices through the week for variety.',
            'Keep hydration consistent, especially on more active days.',
        ]

    if latest_score is None:
        score_focus = 'Baseline Needed'
        score_tip = 'Complete a physical health calculation so nutrition suggestions can respond to your current routine.'
    elif latest_score < 50:
        score_focus = 'Recovery Support'
        score_tip = 'Your latest health score is low. Focus first on regular meals, enough water, and simple nourishing foods while rebuilding routine.'
    elif latest_score < 70:
        score_focus = 'Build Consistency'
        score_tip = 'Your score suggests room for improvement. Plan meals in advance and aim for steady hydration and protein each day.'
    elif latest_score < 85:
        score_focus = 'Maintain Progress'
        score_tip = 'Your health score is progressing well. Keep meals balanced and make small goal-based adjustments consistently.'
    else:
        score_focus = 'Strong Routine'
        score_tip = 'Your latest score is strong. Maintain variety and choose portions that continue supporting your personal goal.'

    return {
        'goal': goal,
        'title': title,
        'strategy': strategy,
        'meal_ideas': meal_ideas,
        'tips': [score_tip] + goal_tips + [
            'Nutrition values in the food list are approximate per 100 g and may vary by brand and cooking method.',
        ],
        'score_focus': score_focus,
        'score_display': f'{latest_score}/100' if latest_score is not None else 'No score yet',
        'average_display': f'{average_score}/100' if average_score is not None else 'No history',
    }



def home(request):
    return render(request, 'index.html')



def register(request):
    if request.method == "POST":
        email = request.POST['email']

        user = RegisterUser.objects.filter(email=email).first()
        if user:
            messages.error(request, "Email already registered. Please login.")
            return render(request, 'register.html')

        from datetime import date

        dob_str = request.POST.get('dob')
        # dob is expected as YYYY-MM-DD from the date input
        dob = date.fromisoformat(dob_str) if dob_str else None
        computed_age = None
        if dob:
            today = date.today()
            computed_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        RegisterUser.objects.create(
            name=request.POST['name'],
            age=computed_age or 0,
            height=request.POST['height'],
            weight=request.POST['weight'],
            gender=request.POST['gender'],
            goal=request.POST['goal'],
            email=email,
            password=request.POST['password'],
        )

        # After successful register show the dedicated success page
        return redirect('register_success')


    return render(request, 'register.html')



def register_success(request):
    return render(request, 'register_success.html')



def login_view(request):
    message = ""

    if request.method == "POST":
        email = request.POST['email']
        password = request.POST['password']

        try:
            user = RegisterUser.objects.get(email=email)

            # No OTP/email verification in this project right now.
            if user.password == password:
                # Store the logged-in user so dashboard can show correct details.
                request.session['user_id'] = user.id
                return redirect('/dashboard/')
            message = "Incorrect password"

        except RegisterUser.DoesNotExist:
            message = "Not registered"

    return render(request, 'login.html', {'message': message})



def dashboard(request):
    user_id = request.session.get('user_id')
    if not user_id:
        # If user did not log in (or session expired), go to login.
        return redirect('/login/')

    user = RegisterUser.objects.filter(id=user_id).first()
    if not user:
        return redirect('/login/')

    return render(request, 'dashboard.html', {'user': user})


def logout_view(request):
    if request.method == 'POST':
        request.session.flush()
    return redirect('/login/')





def physical_health(request):
    # Physical health calculator (no external AI; rule-based "AI-style" scoring)
    # Require logged-in user to access physical page so we can read registered age/height/weight.
    user_id = request.session.get('user_id')
    user = None
    if user_id:
        user = RegisterUser.objects.filter(id=user_id).first()
    if not user:
        return redirect('/login/')

    _physical_history(request, user)

    if request.method == 'POST':
        def to_float(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        def to_int(v):
            try:
                return int(v)
            except (TypeError, ValueError):
                return None

        water_liters = to_float(request.POST.get('water_liters'))
        sleep_hours = to_float(request.POST.get('sleep_hours'))
        exercise_minutes = to_float(request.POST.get('exercise_minutes'))
        steps_count = to_int(request.POST.get('steps_count'))
        age = to_int(request.POST.get('age'))
        weight = to_float(request.POST.get('weight'))
        height = to_float(request.POST.get('height'))

        history = _physical_history(request, user)
        required_inputs = {
            'water intake': water_liters,
            'sleep duration': sleep_hours,
            'exercise time': exercise_minutes,
            'steps count': steps_count,
        }
        missing_inputs = [label for label, value in required_inputs.items() if value is None]
        if missing_inputs:
            return render(request, 'physical.html', {
                'form_error': 'Enter all daily inputs before calculating progress. Missing: '
                + ', '.join(missing_inputs) + '.',
                'form': {
                    'water_liters': water_liters,
                    'sleep_hours': sleep_hours,
                    'exercise_minutes': exercise_minutes,
                    'steps_count': steps_count,
                    'age': age,
                    'weight': weight,
                    'height': height,
                },
                'user': user,
                'history': history,
                'history_json': json.dumps(history),
            })

        # Basic scoring per provided logic
        score = 50
        risks = []
        analysis_lines = []

        # Hydration
        if water_liters is not None:
            if water_liters < 2:
                score -= 18
                risks.append('Dehydration risk (low water intake).')
                analysis_lines.append('Your water intake appears low; hydration supports digestion, recovery, and energy levels.')
            elif 2 <= water_liters <= 3:
                score += 4
                analysis_lines.append('Your hydration looks in a healthy range for daily function and recovery.')
            else:
                score += 10
                analysis_lines.append('Great hydration! This can improve recovery and workout performance.')

        # Sleep
        if sleep_hours is not None:
            if sleep_hours < 6:
                score -= 20
                risks.append('Poor sleep (below 6 hours).')
                analysis_lines.append('Sleep is currently low. Poor sleep can increase stress, cravings, and slow muscle recovery.')
            elif 6 <= sleep_hours <= 8:
                score += 6
                analysis_lines.append('Your sleep duration is healthy and supports recovery.')
            else:
                score += 10
                analysis_lines.append('Excellent recovery window. Longer sleep can support training adaptations (ensure quality too).')

        # Exercise
        if exercise_minutes is not None:
            if exercise_minutes < 20:
                score -= 18
                risks.append('Lack of exercise (under 20 minutes/day).')
                analysis_lines.append('Your daily exercise time seems low. Even short workouts help strength, mood, and metabolism.')
            elif 20 <= exercise_minutes <= 45:
                score += 8
                analysis_lines.append('Moderately active—nice balance. Consistency here can bring steady physical improvements.')
            else:
                score += 12
                analysis_lines.append('Active lifestyle—great for cardiovascular health and long-term fitness.')

        # Daily movement / steps
        if steps_count is not None:
            if steps_count < 3000:
                score -= 18
                risks.append('Low daily movement (under 3000 steps).')
                analysis_lines.append('Low daily movement can reduce metabolic health. Adding walks can make a big difference.')
            elif 3000 <= steps_count <= 8000:
                score += 8
                analysis_lines.append('Your movement level is moderate. A small step increase could yield more benefits.')
            else:
                score += 12
                analysis_lines.append('Highly active daily movement—excellent for heart health and energy expenditure.')

        # Optional BMI context (not used for scoring heavily)
        if weight is not None and height is not None and height > 0:
            try:
                bmi = weight / ((height/100) ** 2)
                analysis_lines.append(f'BMI estimate: {bmi:.1f} (used as context only).')
            except Exception:
                pass

        # Clamp and classify
        score = max(0, min(100, int(score)))

        if score >= 85:
            condition = 'Excellent'
        elif score >= 70:
            condition = 'Good'
        elif score >= 50:
            condition = 'Average'
        else:
            condition = 'Poor'

        # Personalized suggestions
        suggestions = []
        if water_liters is None:
            suggestions.append('Add your water intake so I can fine-tune hydration advice.')
        elif water_liters < 2:
            suggestions.append('Start with an extra glass in the morning and another in the afternoon; aim toward 2–3L/day.')

        if sleep_hours is None:
            suggestions.append('Share your sleep hours to get targeted recovery recommendations.')
        elif sleep_hours < 6:
            suggestions.append('Try shifting bedtime 30 minutes earlier for 3–4 days and keep wake time consistent.')

        if exercise_minutes is None:
            suggestions.append('Share daily exercise time to tailor your activity plan.')
        elif exercise_minutes < 20:
            suggestions.append('Begin with 15–20 minutes/day: brisk walk + basic strength (squats/push-ups) 2–3x/week.')

        if steps_count is None:
            suggestions.append('Share your steps so I can recommend a realistic movement goal.')
        elif steps_count < 3000:
            suggestions.append('Add two 10-minute walks daily (after meals). This can push you closer to 3000–8000 steps.')

        if not risks:
            suggestions.append('Keep your routine consistent. If you want to level up, increase either sleep quality or steps gradually (5–10%/week).')

        # Do not show suggestions on the main physical page (user requested)
        result_text = {
            'score': score,
            'condition': condition,
            'risks': risks,
            'analysis': analysis_lines,
            'suggestions': [],
        }

        # Save the last physical calculation so other pages can use it
        request.session['physical_last_result'] = result_text

        # Save every score for this user so progress includes their full history.
        PhysicalHealthScore.objects.create(user=user, score=score)
        history = _physical_history(request, user)
        history_json = json.dumps(history)

        # Record last inputs for potential prefill (optional)
        request.session['physical_last_sleep_hours'] = sleep_hours

        return render(request, 'physical.html', {
            'result': result_text,
            'form': {
                'water_liters': water_liters,
                'sleep_hours': sleep_hours,
                'exercise_minutes': exercise_minutes,
                'steps_count': steps_count,
                'age': age,
                'weight': weight,
                'height': height,
            },
            'user': user,
            'history': history,
            'history_json': history_json,
        })


    # GET: render page with user context and any history
    history = _physical_history(request, user)
    history_json = json.dumps(history)
    return render(request, 'physical.html', {
        'user': user,
        'history': history,
        'history_json': history_json,
    })




def physical_health_tracker(request):
    user_id = request.session.get('user_id')
    user = RegisterUser.objects.filter(id=user_id).first() if user_id else None
    if not user:
        return redirect('/login/')

    history = _physical_history(request, user)

    context = {
        'history': history,
        'history_json': json.dumps(history),
    }

    return render(request, 'physical_tracker.html', context)


def reset_physical_history(request):
    if request.method != 'POST':
        return redirect('/physical/')

    user_id = request.session.get('user_id')
    user = RegisterUser.objects.filter(id=user_id).first() if user_id else None
    if not user:
        return redirect('/login/')

    PhysicalHealthScore.objects.filter(user=user).delete()
    request.session.pop('physical_history', None)
    request.session['physical_history_imported'] = True
    request.session.pop('physical_last_result', None)
    return redirect('/physical/')



def mental_health(request):
    user_id = request.session.get('user_id')
    user = RegisterUser.objects.filter(id=user_id).first() if user_id else None
    if not user:
        return redirect('/login/')

    sleep_prefill = request.session.get('physical_last_sleep_hours')
    if sleep_prefill is None:
        sleep_prefill = request.session.get('mental_last_sleep_hours', '')

    history = _mental_history(user)
    form = {
        'sleep_hours': sleep_prefill,
        'mood': '',
        'heart_rate': '',
        'stress_level': '',
    }
    context = {
        'user': user,
        'form': form,
        'history': history,
        'history_json': json.dumps(history),
    }

    if request.method != 'POST':
        return render(request, 'mental.html', context)

    def to_float(value):
        try:
            return float(value) if value not in (None, '') else None
        except (TypeError, ValueError):
            return None

    def to_int(value):
        try:
            return int(float(value)) if value not in (None, '') else None
        except (TypeError, ValueError):
            return None

    sleep_hours = to_float(request.POST.get('sleep_hours'))
    mood = to_float(request.POST.get('mood'))
    heart_rate = to_int(request.POST.get('heart_rate'))
    stress_level = to_float(request.POST.get('stress_level'))
    form = {
        'sleep_hours': sleep_hours if sleep_hours is not None else '',
        'mood': mood if mood is not None else '',
        'heart_rate': heart_rate if heart_rate is not None else '',
        'stress_level': stress_level if stress_level is not None else '',
    }
    context['form'] = form

    required_inputs = {
        'sleep hours': sleep_hours,
        'mood': mood,
        'heart rate': heart_rate,
        'stress level': stress_level,
    }
    missing_inputs = [label for label, value in required_inputs.items() if value is None]
    if missing_inputs:
        context['form_error'] = (
            'Enter all mental wellness inputs before calculating. Missing: '
            + ', '.join(missing_inputs) + '.'
        )
        return render(request, 'mental.html', context)

    invalid_ranges = []
    if not 0 <= sleep_hours <= 24:
        invalid_ranges.append('sleep hours must be between 0 and 24')
    if not 0 <= mood <= 10:
        invalid_ranges.append('mood must be between 0 and 10')
    if not 30 <= heart_rate <= 220:
        invalid_ranges.append('heart rate must be between 30 and 220 bpm')
    if not 0 <= stress_level <= 10:
        invalid_ranges.append('stress level must be between 0 and 10')
    if invalid_ranges:
        context['form_error'] = 'Please correct your inputs: ' + '; '.join(invalid_ranges) + '.'
        return render(request, 'mental.html', context)

    score = 70 + ((mood - 5) * 4)
    concerns = []
    suggestions = []

    if mood < 4:
        concerns.append('Low mood may be affecting daily motivation and resilience.')
        suggestions.append('Try a gentle 10-minute walk or write down one manageable task for today.')
    elif mood >= 8:
        suggestions.append('Protect the routines supporting your mood, especially sleep and regular breaks.')

    if sleep_hours < 6:
        score -= 18
        concerns.append('Low sleep duration may affect mental recovery.')
        suggestions.append('Try moving bedtime 30 minutes earlier while keeping a steady wake time.')
    elif sleep_hours <= 8:
        score += 6
        suggestions.append('Your sleep duration is in a supportive range; aim to keep it consistent.')
    else:
        score += 4
        suggestions.append('Your sleep duration is adequate; focus on quality and how rested you feel.')

    if heart_rate > 100:
        score -= 12
        concerns.append('Your entered heart rate is elevated and may reflect stress or recent activity.')
        suggestions.append('Rest quietly for a few minutes and recheck your heart rate if appropriate.')
    elif heart_rate < 50:
        score -= 6
        concerns.append('Your entered heart rate is low; this can be normal for some people.')
        suggestions.append('If you feel unwell, dizzy, or unusually tired, consider professional medical advice.')
    else:
        score += 4

    if stress_level >= 7:
        score -= 18
        concerns.append('High self-reported stress may affect wellbeing and sleep.')
        suggestions.append('Try a three-minute reset: slow breathing and deliberately relax your shoulders and jaw.')
    elif stress_level >= 4:
        score -= 6
        suggestions.append('For moderate stress, schedule a brief screen-free break during your day.')
    else:
        score += 6

    score = max(0, min(100, int(score)))
    if score >= 85:
        condition = 'Doing Well'
    elif score >= 70:
        condition = 'Steady'
    elif score >= 50:
        condition = 'Needs Attention'
    else:
        condition = 'Support Recommended'
        suggestions.append(
            'If distress feels overwhelming or you may harm yourself, seek immediate local crisis or emergency support.'
        )

    result = {
        'score': score,
        'condition': condition,
        'concerns': concerns,
        'suggestions': suggestions,
    }
    MentalHealthScore.objects.create(
        user=user,
        score=score,
        sleep_hours=sleep_hours,
        mood=mood,
        heart_rate=heart_rate,
        stress_level=stress_level,
    )
    request.session['mental_last_sleep_hours'] = sleep_hours
    request.session['mental_last_result'] = result

    history = _mental_history(user)
    context.update({
        'result': result,
        'history': history,
        'history_json': json.dumps(history),
    })
    return render(request, 'mental.html', context)


def reset_mental_history(request):
    if request.method != 'POST':
        return redirect('/mental/')

    user_id = request.session.get('user_id')
    user = RegisterUser.objects.filter(id=user_id).first() if user_id else None
    if not user:
        return redirect('/login/')

    MentalHealthScore.objects.filter(user=user).delete()
    request.session.pop('mental_last_result', None)
    return redirect('/mental/')



def suggest_exercise(request):
    user_id = request.session.get('user_id')
    user = RegisterUser.objects.filter(id=user_id).first() if user_id else None
    if not user:
        return redirect('/login/')

    history = _physical_history(request, user)
    plan = _exercise_recommendation(user, history)
    return render(request, 'suggest_exercise.html', {
        'user': user,
        'plan': plan,
        'history_json': json.dumps(history),
    })



def suggest_diet(request):
    user_id = request.session.get('user_id')
    user = RegisterUser.objects.filter(id=user_id).first() if user_id else None
    if not user:
        return redirect('/login/')

    history = _physical_history(request, user)
    plan = _diet_recommendation(user, history)
    return render(request, 'suggest_diet.html', {
        'user': user,
        'plan': plan,
        'foods': FOOD_NUTRITION_LIST,
    })



def sleep_improvement(request):
    return render(request, 'sleep_improvement.html')



def stress_management(request):
    return render(request, 'stress_management.html')

