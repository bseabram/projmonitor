from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    # Projetos
    path('projetos/', views.lista_projetos, name='lista_projetos'),
    path('projetos/novo/', views.criar_projeto, name='criar_projeto'),
    path('projetos/<int:projeto_id>/', views.detalhe_projeto, name='detalhe_projeto'),
    path('projetos/<int:projeto_id>/editar/', views.editar_projeto, name='editar_projeto'),
    path('projetos/<int:projeto_id>/apagar/', views.apagar_projeto, name='apagar_projeto'),
    path('projetos/<int:projeto_id>/exportar/', views.exportar_csv, name='exportar_csv'),
    path('projetos/<int:projeto_id>/gantt/', views.gantt_projeto, name='gantt_projeto'),
    # Participantes
    path('projetos/<int:projeto_id>/participantes/adicionar/', views.adicionar_participante, name='adicionar_participante'),
    path('projetos/<int:projeto_id>/participantes/<int:utilizador_id>/remover/', views.remover_participante, name='remover_participante'),
    # Tarefas
    path('projetos/<int:projeto_id>/tarefas/nova/', views.criar_tarefa, name='criar_tarefa'),
    path('tarefas/<int:tarefa_id>/', views.detalhe_tarefa, name='detalhe_tarefa'),
    path('tarefas/<int:tarefa_id>/editar/', views.editar_tarefa, name='editar_tarefa'),
    path('tarefas/<int:tarefa_id>/apagar/', views.apagar_tarefa, name='apagar_tarefa'),
    path('tarefas/<int:tarefa_id>/decompor/', views.decompor_tarefa, name='decompor_tarefa'),
    path('tarefas/<int:tarefa_id>/dependencia/', views.adicionar_dependencia, name='adicionar_dependencia'),
    path('dependencias/<int:dep_id>/remover/', views.remover_dependencia, name='remover_dependencia'),
    # Área do colaborador
    path('minhas-tarefas/', views.minhas_tarefas, name='minhas_tarefas'),
    path('tarefas/<int:tarefa_id>/atualizar/', views.atualizar_tarefa_colaborador, name='atualizar_tarefa_colaborador'),
    # Utilizadores
    path('utilizadores/novo/', views.criar_utilizador, name='criar_utilizador'),
    path('utilizadores/password/', views.alterar_password, name='alterar_password'),
]
