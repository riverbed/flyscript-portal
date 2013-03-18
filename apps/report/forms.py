from django import forms

from apps.report.models import Report, Widget


class ReportDetailForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ReportDetailForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Report


class WidgetDetailForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(WidgetDetailForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Widget


