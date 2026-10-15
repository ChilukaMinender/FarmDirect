from django.db import models
from django.contrib.auth.models import User


class Product(models.Model):
    CATEGORY_CHOICES = [
        ('vegetables', 'Vegetables'),
        ('fruits', 'Fruits'),
        ('grains', 'Grains'),
        ('dairy', 'Dairy'),
        ('other', 'Other'),
    ]

    farmer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='farm_products'
    )

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='vegetables'
    )

    price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=30, default='kg')
    quantity = models.PositiveIntegerField(default=0)

    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True
    )

    location = models.CharField(max_length=150, blank=True)
    is_available = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name