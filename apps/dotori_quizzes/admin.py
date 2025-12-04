from django.contrib import admin
from .models import Quiz, Option

class OptionInline(admin.TabularInline):
    model = Option
    extra = 0

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("id", "qtype", "difficulty", "locale", "prompt_text")
    list_filter = ("qtype", "difficulty", "locale")
    search_fields = ("prompt_text",)
    inlines = [OptionInline]
