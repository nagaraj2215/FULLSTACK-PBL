import json

from django.test import TestCase
from django.urls import reverse

from .models import MentalHealthScore, PhysicalHealthScore, RegisterUser


class PhysicalHealthTrackerTests(TestCase):
    def setUp(self):
        self.user = RegisterUser.objects.create(
            name='Tracker User',
            age=28,
            height=170,
            weight=65,
            gender='Other',
            goal='Fitness',
            email='tracker@example.com',
            password='password',
        )
        session = self.client.session
        session['user_id'] = self.user.id
        session.save()

    def test_submissions_are_saved_and_displayed_as_full_history(self):
        form = {
            'water_liters': '2.5',
            'sleep_hours': '7',
            'exercise_minutes': '30',
            'steps_count': '5000',
            'age': '28',
            'height': '170',
            'weight': '65',
        }
        self.client.post(reverse('physical_health'), form)
        self.client.post(reverse('physical_health'), {**form, 'steps_count': '9000'})

        response = self.client.get(reverse('physical_health_tracker'))
        history = json.loads(response.context['history_json'])

        self.assertEqual(PhysicalHealthScore.objects.filter(user=self.user).count(), 2)
        self.assertEqual(len(history), 2)
        self.assertEqual([item['score'] for item in history], [76, 80])
        self.assertContains(response, 'Overall Progress')
        self.assertContains(response, 'All-Time Average')

    def test_incomplete_submission_does_not_create_a_progress_point(self):
        response = self.client.post(reverse('physical_health'), {
            'water_liters': '2.5',
            'sleep_hours': '7',
            'exercise_minutes': '30',
            'age': '28',
            'height': '170',
            'weight': '65',
        })

        self.assertEqual(PhysicalHealthScore.objects.filter(user=self.user).count(), 0)
        self.assertContains(response, 'Enter all daily inputs before calculating progress.')

    def test_legacy_session_history_is_imported_without_twenty_score_limit(self):
        session = self.client.session
        session['physical_history'] = [
            {'ts': f'2026-05-{index + 1:02d}T10:00:00', 'score': index}
            for index in range(25)
        ]
        session.save()

        first_response = self.client.get(reverse('physical_health_tracker'))
        second_response = self.client.get(reverse('physical_health_tracker'))

        self.assertEqual(PhysicalHealthScore.objects.filter(user=self.user).count(), 25)
        self.assertEqual(len(json.loads(first_response.context['history_json'])), 25)
        self.assertEqual(len(json.loads(second_response.context['history_json'])), 25)

    def test_physical_reset_clears_logged_in_users_graph_history(self):
        other_user = RegisterUser.objects.create(
            name='Other Tracker User',
            age=30,
            height=175,
            weight=70,
            gender='Other',
            goal='Fitness',
            email='other-tracker@example.com',
            password='password',
        )
        PhysicalHealthScore.objects.create(user=self.user, score=76)
        PhysicalHealthScore.objects.create(user=self.user, score=80)
        PhysicalHealthScore.objects.create(user=other_user, score=90)

        response = self.client.post(reverse('reset_physical_history'))

        self.assertRedirects(response, '/physical/')
        self.assertEqual(PhysicalHealthScore.objects.filter(user=self.user).count(), 0)
        self.assertEqual(PhysicalHealthScore.objects.filter(user=other_user).count(), 1)

    def test_logout_clears_session_and_redirects_to_login(self):
        response = self.client.post(reverse('logout'))

        self.assertRedirects(response, '/login/')
        self.assertNotIn('user_id', self.client.session)
        dashboard_response = self.client.get(reverse('dashboard'))
        self.assertRedirects(dashboard_response, '/login/')


class ExerciseSuggestionTests(TestCase):
    def _log_in_as(self, user):
        session = self.client.session
        session['user_id'] = user.id
        session.save()

    def test_exercise_suggestions_require_login(self):
        response = self.client.get(reverse('suggest_exercise'))

        self.assertRedirects(response, '/login/')

    def test_exercise_plan_changes_for_user_goal_and_score(self):
        gain_user = RegisterUser.objects.create(
            name='Gain User',
            age=24,
            height=170,
            weight=58,
            gender='Other',
            goal='Weight Gain',
            email='gain@example.com',
            password='password',
        )
        loss_user = RegisterUser.objects.create(
            name='Loss User',
            age=31,
            height=165,
            weight=82,
            gender='Other',
            goal='Weight Loss',
            email='loss@example.com',
            password='password',
        )
        PhysicalHealthScore.objects.create(user=gain_user, score=42)
        PhysicalHealthScore.objects.create(user=loss_user, score=90)

        self._log_in_as(gain_user)
        gain_response = self.client.get(reverse('suggest_exercise'))

        self._log_in_as(loss_user)
        loss_response = self.client.get(reverse('suggest_exercise'))

        self.assertContains(gain_response, 'Strength and Muscle Gain')
        self.assertContains(gain_response, 'Recovery First')
        self.assertEqual(json.loads(gain_response.context['history_json'])[0]['score'], 42)
        self.assertContains(loss_response, 'Active Weight Management')
        self.assertContains(loss_response, 'Ready To Progress')
        self.assertEqual(json.loads(loss_response.context['history_json'])[0]['score'], 90)


class DietSuggestionTests(TestCase):
    def _log_in_as(self, user):
        session = self.client.session
        session['user_id'] = user.id
        session.save()

    def test_diet_suggestions_require_login(self):
        response = self.client.get(reverse('suggest_diet'))

        self.assertRedirects(response, '/login/')

    def test_diet_plan_changes_for_user_goal_and_health_score(self):
        gain_user = RegisterUser.objects.create(
            name='Nutrition Gain',
            age=22,
            height=172,
            weight=53,
            gender='Other',
            goal='Weight Gain',
            email='nutrition-gain@example.com',
            password='password',
        )
        loss_user = RegisterUser.objects.create(
            name='Nutrition Loss',
            age=35,
            height=168,
            weight=85,
            gender='Other',
            goal='Weight Loss',
            email='nutrition-loss@example.com',
            password='password',
        )
        PhysicalHealthScore.objects.create(user=gain_user, score=44)
        PhysicalHealthScore.objects.create(user=loss_user, score=91)

        self._log_in_as(gain_user)
        gain_response = self.client.get(reverse('suggest_diet'))

        self._log_in_as(loss_user)
        loss_response = self.client.get(reverse('suggest_diet'))

        self.assertContains(gain_response, 'Healthy Weight Gain Nutrition')
        self.assertContains(gain_response, 'Recovery Support')
        self.assertContains(loss_response, 'Balanced Weight Management Nutrition')
        self.assertContains(loss_response, 'Strong Routine')

    def test_diet_page_includes_searchable_food_nutrition_list(self):
        user = RegisterUser.objects.create(
            name='Nutrition Table User',
            age=25,
            height=165,
            weight=60,
            gender='Other',
            goal='Stay Fit',
            email='nutrition-table@example.com',
            password='password',
        )
        self._log_in_as(user)

        response = self.client.get(reverse('suggest_diet'))

        self.assertContains(response, 'Food Nutrition List')
        self.assertContains(response, 'id="foodSearch"')
        self.assertContains(response, 'Oats (dry)')
        self.assertContains(response, 'Chicken breast (cooked)')
        self.assertContains(response, 'Mango')
        self.assertContains(response, 'Sambar')
        self.assertContains(response, 'Muesli')
        self.assertEqual(len(response.context['foods']), 200)


class MentalHealthCalculationTests(TestCase):
    def setUp(self):
        self.user = RegisterUser.objects.create(
            name='Mental Check-in User',
            age=29,
            height=168,
            weight=64,
            gender='Other',
            goal='Stay Fit',
            email='mental@example.com',
            password='password',
        )

    def _log_in(self):
        session = self.client.session
        session['user_id'] = self.user.id
        session.save()

    def test_mental_calculator_requires_login(self):
        response = self.client.get(reverse('mental_health'))

        self.assertRedirects(response, '/login/')

    def test_valid_mental_check_in_calculates_and_saves_score_history(self):
        self._log_in()

        response = self.client.post(reverse('mental_health'), {
            'sleep_hours': '7',
            'mood': '8',
            'heart_rate': '72',
            'stress_level': '2',
        })
        history = json.loads(response.context['history_json'])

        self.assertEqual(MentalHealthScore.objects.filter(user=self.user).count(), 1)
        self.assertEqual(history[0]['score'], 98)
        self.assertContains(response, 'Mental Health Score: 98/100')
        self.assertContains(response, 'Doing Well')
        self.assertContains(response, 'Mental Score History')

    def test_incomplete_or_invalid_mental_input_is_not_saved(self):
        self._log_in()

        incomplete_response = self.client.post(reverse('mental_health'), {
            'sleep_hours': '7',
            'mood': '6',
            'heart_rate': '72',
        })
        invalid_response = self.client.post(reverse('mental_health'), {
            'sleep_hours': '7',
            'mood': '6',
            'heart_rate': '72',
            'stress_level': '12',
        })

        self.assertEqual(MentalHealthScore.objects.filter(user=self.user).count(), 0)
        self.assertContains(incomplete_response, 'Enter all mental wellness inputs')
        self.assertContains(invalid_response, 'stress level must be between 0 and 10')

    def test_mental_reset_clears_logged_in_users_graph_history(self):
        self._log_in()
        other_user = RegisterUser.objects.create(
            name='Other Mental User',
            age=32,
            height=172,
            weight=68,
            gender='Other',
            goal='Stay Fit',
            email='other-mental@example.com',
            password='password',
        )
        MentalHealthScore.objects.create(
            user=self.user,
            score=82,
            sleep_hours=7,
            mood=7,
            heart_rate=72,
            stress_level=3,
        )
        MentalHealthScore.objects.create(
            user=other_user,
            score=91,
            sleep_hours=8,
            mood=8,
            heart_rate=70,
            stress_level=2,
        )

        response = self.client.post(reverse('reset_mental_history'))

        self.assertRedirects(response, '/mental/')
        self.assertEqual(MentalHealthScore.objects.filter(user=self.user).count(), 0)
        self.assertEqual(MentalHealthScore.objects.filter(user=other_user).count(), 1)
