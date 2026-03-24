# Migration: adds LoginHistory and PaymentRecord tables
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # ── LoginHistory ─────────────────────────────────────────
        migrations.CreateModel(
            name='LoginHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True, default='')),
                ('logged_in_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='login_history',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name':          'Login History',
                'verbose_name_plural':   'Login Histories',
                'ordering':              ['-logged_in_at'],
            },
        ),

        # ── PaymentRecord ────────────────────────────────────────
        migrations.CreateModel(
            name='PaymentRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('plan',           models.CharField(max_length=20, default='premium')),
                ('amount',         models.DecimalField(max_digits=8, decimal_places=2, default=0)),
                ('currency',       models.CharField(max_length=5, default='INR')),
                ('status',         models.CharField(
                    max_length=20, default='pending',
                    choices=[('pending','Pending'),('success','Success'),
                             ('failed','Failed'),('refunded','Refunded')],
                )),
                ('method',         models.CharField(
                    max_length=20, default='card',
                    choices=[('card','Credit / Debit Card'),('upi','UPI'),
                             ('wallet','Wallet'),('other','Other')],
                )),
                ('transaction_id', models.CharField(max_length=200, blank=True, default='')),
                ('notes',          models.TextField(blank=True, default='')),
                ('paid_at',        models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='payments',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Payment Record',
                'ordering':     ['-paid_at'],
            },
        ),

        # ── Add phone field to UserProfile ───────────────────────
        migrations.AddField(
            model_name='userprofile',
            name='phone',
            field=models.CharField(blank=True, default='', max_length=20),
        ),

        # ── Add notes field to Subscription ──────────────────────
        migrations.AddField(
            model_name='subscription',
            name='notes',
            field=models.TextField(blank=True, default=''),
        ),
    ]
