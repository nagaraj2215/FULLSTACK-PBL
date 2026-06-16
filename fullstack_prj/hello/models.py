from django.db import models


class RegisterUser(models.Model):
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    height = models.FloatField()
    weight = models.FloatField()
    gender = models.CharField(max_length=20)
    goal = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)

    # Email verification
    is_email_verified = models.BooleanField(default=False)
    email_verification_code = models.CharField(max_length=6, blank=True, default='')
    email_verification_expires_at = models.DateTimeField(null=True, blank=True)


class PhysicalHealthScore(models.Model):
    user = models.ForeignKey(RegisterUser, on_delete=models.CASCADE, related_name='physical_scores')
    score = models.PositiveSmallIntegerField()
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['recorded_at', 'id']


class MentalHealthScore(models.Model):
    user = models.ForeignKey(RegisterUser, on_delete=models.CASCADE, related_name='mental_scores')
    score = models.PositiveSmallIntegerField()
    sleep_hours = models.FloatField()
    mood = models.FloatField()
    heart_rate = models.PositiveSmallIntegerField()
    stress_level = models.FloatField()
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['recorded_at', 'id']

