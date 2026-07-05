from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import DependenciaTarefa, Projeto, Tarefa, Utilizador


@admin.register(Utilizador)
class UtilizadorAdmin(UserAdmin):
    list_display = ["username", "first_name", "last_name", "email", "papel"]
    fieldsets = UserAdmin.fieldsets + (
        ("Perfil", {"fields": ("papel",)}),
    )


class TarefaInline(admin.TabularInline):
    model = Tarefa
    extra = 0
    fields = ["titulo", "estado", "responsavel", "prazo"]


@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ["nome", "estado", "data_inicio", "data_fim_prevista"]
    inlines = [TarefaInline]


@admin.register(Tarefa)
class TarefaAdmin(admin.ModelAdmin):
    list_display = ["titulo", "projeto", "estado", "responsavel", "prazo"]
    list_filter = ["estado", "projeto"]


@admin.register(DependenciaTarefa)
class DependenciaAdmin(admin.ModelAdmin):
    list_display = ["predecessora", "sucessora"]
