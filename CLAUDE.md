# Sistema de Monitorização de Projetos de Software

## Contexto do projeto
Aplicação web Django desenvolvida como projeto final de Engenharia Informática.
Permite criar projetos, decompor tarefas em subtarefas (WBS), atribuir tarefas a colaboradores, registar esforço estimado/real e calcular métricas de desempenho (conclusão, desvio de esforço, nível de risco).

## Stack técnica
- Python + Django 4.2
- Base de dados: SQLite
- Frontend: HTML + Bootstrap 5
- Testes: Django TestCase (unittest)

## Estrutura do projeto
```
sistema_monitoramento/
├── manage.py
├── requirements.txt
├── monitoramento/        # configurações Django (settings, urls, wsgi)
└── core/                 # app principal
    ├── models.py         # Utilizador, Projeto, Tarefa, DependenciaTarefa
    ├── views.py          # todas as vistas
    ├── urls.py           # rotas
    ├── forms.py          # formulários
    ├── admin.py
    ├── tests.py          # testes unitários e de integração
    └── templates/core/   # templates HTML
```

## Perfis de utilizador
- **Gestor de Projeto**: cria e gere projetos, decompõe tarefas, adiciona colaboradores
- **Colaborador**: atualiza estado das tarefas e regista esforço real

## Regras de negócio importantes
- Só tarefas sem subtarefas (tarefas finais) podem ser atribuídas a colaboradores
- Só colaboradores associados ao projeto podem receber tarefas
- Uma tarefa não pode transitar para EM_EXECUCAO/CONCLUIDA se a tarefa predecessora não estiver concluída
- Percentagem de conclusão = tarefas finais concluídas / total tarefas finais × 100
- Desvio de esforço = (esforço real - esforço estimado) / esforço estimado × 100
- Nível de risco: baixo (<10% desvio, 0 atrasos), médio (até 2 atrasos ou 10-20%), elevado (>2 atrasos ou >20%)

## Como arrancar
```bash
pip install -r requirements.txt
python manage.py makemigrations core
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Como correr os testes
```bash
python manage.py test core
```

## Estado atual
Implementação completa. Relatório final em curso (Capítulos 3 e 4 escritos).
Falta: capturar screenshots do sistema a correr para inserir no relatório.
