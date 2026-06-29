from django.contrib import admin

from brackets.models import Bracket, Invite, InviteSubmission, Match, Pick, Team

admin.site.register(Team)
admin.site.register(Match)
admin.site.register(Bracket)
admin.site.register(Pick)
admin.site.register(Invite)
admin.site.register(InviteSubmission)
