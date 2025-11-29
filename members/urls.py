from django.urls import path

from . import views

urlpatterns = [
    path("", views.login_view, name="login"),
    path("board/", views.board_view, name="board"),
    path("board/submit/<int:item_id>/", views.submit_bingo_item, name="submit_bingo_item"),
    path("board/submission/<int:submission_id>/update/", views.update_submission, name="update_submission"),
    path("board/submission/<int:submission_id>/cancel/", views.cancel_submission, name="cancel_submission"),
    path("logout/", views.logout_view, name="logout"),
]
