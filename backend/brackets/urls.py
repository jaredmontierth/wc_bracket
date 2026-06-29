from django.urls import path

from brackets import views

urlpatterns = [
    path("matches/", views.matches_view),
    path("sync-espn/", views.sync_view),
    path("brackets/", views.brackets_view),
    path("brackets/<slug:slug>/", views.bracket_detail_view),
    path("developer-mode/", views.developer_mode_view),
    path("invites/", views.invites_view),
    path("submissions-lock/", views.submissions_lock_view),
    path("data/export/", views.data_export_view),
    path("data/import/", views.data_import_view),
    path("invites/<slug:token>/", views.invite_view),
    path("leaderboard/", views.leaderboard_view),
]
