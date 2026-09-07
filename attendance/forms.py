from django import forms
from django.utils import timezone

from attendance.models import Project, Task, TimeEntry


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["name", "description", "color"]
        widgets = {
            "color": forms.TextInput(
                attrs={"type": "color", "class": "form-control form-control-color"}
            ),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        if owner is not None:
            self.instance.owner = owner
        for name, field in self.fields.items():
            if name != "color":
                field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        name = cleaned.get("name")
        if name and self.instance.owner_id:
            qs = Project.objects.filter(owner_id=self.instance.owner_id, name=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error("name", "同名のプロジェクトがすでにあります。")
        return cleaned


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["name", "description", "status"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project is not None:
            self.instance.project = project
        self.fields["name"].widget.attrs.setdefault("class", "form-control")
        self.fields["description"].widget.attrs.setdefault("class", "form-control")
        self.fields["status"].widget.attrs.setdefault("class", "form-select")

    def clean(self):
        cleaned = super().clean()
        name = cleaned.get("name")
        if name and self.instance.project_id:
            qs = Task.objects.filter(project_id=self.instance.project_id, name=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error("name", "同名のタスクがこのプロジェクトにあります。")
        return cleaned


class _DateTimeLocalField(forms.DateTimeField):
    input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"]
    widget = forms.DateTimeInput(
        attrs={"type": "datetime-local", "class": "form-control"},
        format="%Y-%m-%dT%H:%M",
    )


class TimeEntryForm(forms.ModelForm):
    start_at = _DateTimeLocalField(label="開始時刻")
    end_at = _DateTimeLocalField(label="終了時刻")
    break_minutes = forms.IntegerField(
        label="休憩（分）",
        min_value=0,
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0}),
    )

    class Meta:
        model = TimeEntry
        fields = ["task", "start_at", "end_at", "note"]
        widgets = {"note": forms.Textarea(attrs={"rows": 2, "class": "form-control"})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.instance.user = user
            self.fields["task"].queryset = (
                Task.objects.filter(project__owner=user)
                .select_related("project")
                .order_by("project__name", "name")
            )
        self.fields["task"].widget.attrs.setdefault("class", "form-select")
        if self.instance and self.instance.pk:
            for name in ("start_at", "end_at"):
                value = getattr(self.instance, name)
                if value:
                    self.initial[name] = timezone.localtime(value).strftime("%Y-%m-%dT%H:%M")
            self.initial["break_minutes"] = self.instance.break_seconds // 60

    @property
    def break_seconds(self):
        return (self.cleaned_data.get("break_minutes") or 0) * 60

    @staticmethod
    def _aware(dt):
        if dt and timezone.is_naive(dt):
            return timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    def clean_start_at(self):
        return self._aware(self.cleaned_data["start_at"])

    def clean_end_at(self):
        return self._aware(self.cleaned_data.get("end_at"))

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_at")
        end = cleaned.get("end_at")
        if start and start > timezone.now():
            self.add_error("start_at", "未来の日時は指定できません。")
        if start and end and end <= start:
            self.add_error("end_at", "終了時刻は開始時刻より後にしてください。")
        return cleaned


class ExportForm(forms.Form):
    date_from = forms.DateField(
        label="開始日", widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )
    date_to = forms.DateField(
        label="終了日", widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )
    project = forms.ModelChoiceField(
        queryset=Project.objects.none(),
        required=False,
        label="プロジェクト",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    task = forms.ModelChoiceField(
        queryset=Task.objects.none(),
        required=False,
        label="タスク",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            today = timezone.localdate()
            self.fields["date_from"].initial = today.replace(day=1)
            self.fields["date_to"].initial = today
        if user is not None:
            self.fields["project"].queryset = Project.objects.filter(owner=user).order_by("name")
            self.fields["task"].queryset = (
                Task.objects.filter(project__owner=user)
                .select_related("project")
                .order_by("project__name", "name")
            )

    def clean(self):
        cleaned = super().clean()
        date_from = cleaned.get("date_from")
        date_to = cleaned.get("date_to")
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError("開始日は終了日以前にしてください。")
        return cleaned


class EntryFilterForm(forms.Form):
    date_from = forms.DateField(
        required=False,
        label="開始日",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    date_to = forms.DateField(
        required=False,
        label="終了日",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    project = forms.ModelChoiceField(
        queryset=Project.objects.none(),
        required=False,
        label="プロジェクト",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    task = forms.ModelChoiceField(
        queryset=Task.objects.none(),
        required=False,
        label="タスク",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    status = forms.ChoiceField(
        required=False,
        label="状態",
        choices=[("", "すべて"), *Task.Status.choices],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["project"].queryset = Project.objects.filter(owner=user).order_by("name")
            self.fields["task"].queryset = (
                Task.objects.filter(project__owner=user)
                .select_related("project")
                .order_by("project__name", "name")
            )

    def clean(self):
        cleaned = super().clean()
        date_from = cleaned.get("date_from")
        date_to = cleaned.get("date_to")
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError("開始日は終了日以前にしてください。")
        return cleaned
