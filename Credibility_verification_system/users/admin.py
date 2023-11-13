from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Statement, Verdict, StatementVerdict
from django.template.loader import render_to_string
from django.urls import reverse
from weasyprint import HTML
from django.http import HttpResponse

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name','gender','country' ,'password')
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Names', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name','username', 'email', 'password1', 'password2'),
        }),
    )
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)

admin.site.register(CustomUser, CustomUserAdmin)

class StatementVerdictAdmin(admin.ModelAdmin):
    list_display = ('statement_text', 'created_at', 'verdict', 'probability_percentage')
    actions = ['export_selected_objects']


    def statement_text(self, obj):
        return obj.statement.statement  # Use lowercase 'statement'

    def created_at(self, obj):
        return obj.statement.created_at  # Use lowercase 'statement'

    def verdict(self, obj):
        return obj.verdict.Statement_verdict  # Use lowercase 'verdict'

    def probability_percentage(self, obj):
        return "{:.2%}".format(obj.verdict.predicted_probability/100)  # Use lowercase 'verdict'

    statement_text.short_description = 'Statement'
    created_at.short_description = 'Created At'
    verdict.short_description = 'Verdict'
    probability_percentage.short_description = 'Probability (%)'
    
    def export_selected_objects(self, request, queryset):
        # Render the data to the template
        html_string = render_to_string('admin/export_statements_pdf.html', {'statement_verdicts': queryset})

        # Convert the HTML to PDF
        html = HTML(string=html_string)
        pdf = html.write_pdf()

        # Create the HttpResponse object with the appropriate PDF headers.
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'filename=selected_statement_verdicts.pdf'
        return response

    export_selected_objects.short_description = "Export selected to PDF"
    

admin.site.register(StatementVerdict, StatementVerdictAdmin)



class VerdictAdmin(admin.ModelAdmin):
    list_display = ('form_id', 'statement_id', 'Statement_verdict', 'predicted_probability')

admin.site.register(Verdict, VerdictAdmin)


class StatementAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'statement', 'created_at')
    
admin.site.register(Statement, StatementAdmin)



