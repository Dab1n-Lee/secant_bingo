from django.urls import path

from . import views

urlpatterns = [
    path("", views.login_view, name="login"),
    path("board/", views.board_view, name="board"),
    path("board/submit/<int:item_id>/", views.submit_bingo_item, name="submit_bingo_item"),
    path("logout/", views.logout_view, name="logout"),
]
