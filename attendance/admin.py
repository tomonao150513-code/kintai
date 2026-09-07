from django.contrib import admin

from .models import Project, ProjectMembership, Task, TimeEntry


class ProjectMembershipInline(admin.TabularInline):
    model = ProjectMembership
    extra = 0
    autocomplete_fields = ("user",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "color", "is_archived", "created_at")
    list_filter = ("is_archived", "owner")
    search_fields = ("name", "description")
    inlines = (ProjectMembershipInline,)

    def get_changeform_initial_data(self, request):
        return {"owner": request.user.pk}


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "status", "is_archived", "created_at")
    list_filter = ("status", "is_archived", "project")
    search_fields = ("name", "description")
    autocomplete_fields = ("project",)


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = (
        "task",
        "user",
        "start_at",
        "end_at",
        "break_seconds",
        "duration_display",
        "source",
    )
    list_filter = ("source", "user", "task__project")
    search_fields = ("note", "task__name")
    autocomplete_fields = ("task",)
    readonly_fields = ("duration_display", "work_date", "created_at", "updated_at")
    date_hierarchy = "start_at"

    def get_changeform_initial_data(self, request):
        return {"user": request.user.pk}

    @admin.display(description="実働時間")
    def duration_display(self, obj):
        if obj.start_at is None:
            return "-"
        return str(obj.duration).split(".")[0]  # マイクロ秒を落とす


@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    list_display = ("project", "user", "role", "created_at")
    list_filter = ("role", "project")
    search_fields = ("project__name", "user__username")
    autocomplete_fields = ("project", "user")
