# Generated by Django 3.2.16 on 2024-05-24 15:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0003_comment'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='comment_count',
            field=models.IntegerField(default=0, verbose_name='количество комментариев'),
        ),
    ]