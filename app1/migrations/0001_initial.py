# Generated migration for app1 models
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # ── UserProfile ──────────────────────────────────────────
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('bio', models.TextField(blank=True, default='')),
                ('avatar_url', models.URLField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profile',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'verbose_name': 'User Profile'},
        ),

        # ── Subscription ─────────────────────────────────────────
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('plan', models.CharField(
                    choices=[('free', 'Free'), ('premium', 'Premium')],
                    default='free', max_length=20,
                )),
                ('status', models.CharField(
                    choices=[('active', 'Active'), ('expired', 'Expired'), ('cancelled', 'Cancelled')],
                    default='active', max_length=20,
                )),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='subscription',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'verbose_name': 'Subscription'},
        ),

        # ── LiveSession ───────────────────────────────────────────
        migrations.CreateModel(
            name='LiveSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('session_date', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'ordering': ['session_date'], 'verbose_name': 'Live Session'},
        ),

        # ── LiveSessionRegistration ───────────────────────────────
        migrations.CreateModel(
            name='LiveSessionRegistration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('session_name', models.CharField(max_length=200)),
                ('name', models.CharField(max_length=150)),
                ('email', models.EmailField()),
                ('message', models.TextField(blank=True)),
                ('registered_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='session_registrations',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-registered_at'], 'verbose_name': 'Session Registration'},
        ),

        # ── UserProgress ──────────────────────────────────────────
        migrations.CreateModel(
            name='UserProgress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('module', models.CharField(
                    choices=[
                        ('python','Python'),('java','Java'),('cpp','C++'),
                        ('javascript','JavaScript'),('sql','SQL'),('dsa','DSA'),
                        ('communication','Communication'),('aptitude','Aptitude'),
                    ],
                    max_length=30,
                )),
                ('topic_name', models.CharField(max_length=200)),
                ('content_type', models.CharField(
                    choices=[('lesson','Lesson'),('practice','Practice'),('test','Test')],
                    default='lesson', max_length=20,
                )),
                ('completed', models.BooleanField(default=False)),
                ('visited_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='progress',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-visited_at'], 'verbose_name': 'User Progress'},
        ),
        migrations.AlterUniqueTogether(
            name='userprogress',
            unique_together={('user', 'module', 'topic_name', 'content_type')},
        ),

        # ── TestResult ────────────────────────────────────────────
        migrations.CreateModel(
            name='TestResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('module', models.CharField(
                    choices=[
                        ('python','Python'),('java','Java'),('cpp','C++'),
                        ('javascript','JavaScript'),('sql','SQL'),('dsa','DSA'),
                        ('communication','Communication'),('aptitude','Aptitude'),
                        ('interview','Interview'),('technical','Technical'),
                    ],
                    max_length=30,
                )),
                ('test_name', models.CharField(max_length=200)),
                ('score', models.FloatField()),
                ('total_questions', models.PositiveIntegerField(default=0)),
                ('correct_answers', models.PositiveIntegerField(default=0)),
                ('time_taken', models.PositiveIntegerField(default=0)),
                ('attempted_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='test_results',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-attempted_at'], 'verbose_name': 'Test Result'},
        ),

        # ── ContactMessage ────────────────────────────────────────
        migrations.CreateModel(
            name='ContactMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=150)),
                ('email', models.EmailField()),
                ('subject', models.CharField(blank=True, max_length=300)),
                ('message', models.TextField()),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('is_read', models.BooleanField(default=False)),
            ],
            options={'ordering': ['-sent_at'], 'verbose_name': 'Contact Message'},
        ),
    ]