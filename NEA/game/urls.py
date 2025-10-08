from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Route for the homepage
    path('main-menu/', views.main_menu, name='main_menu'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.register, name='register'),
    path('pass-and-play/', views.pass_and_play, name='pass_and_play'),
    path('game-over/', views.game_over, name='game_over'),
    path('setup-pass-and-play/', views.setup_pass_and_play, name='setup_pass_and_play'),
    path('game-rules/', views.game_rules, name='game_rules'),
    path('view_profile/', views.view_profile, name='view_profile'),
    path('setup_bot_game/', views.setup_bot_game, name='setup_bot_game'),
    path('bot_game/', views.bot_game, name='bot_game'),
    path('view_leaderboard/', views.view_leaderboard, name = 'view_leaderboard'),
]
