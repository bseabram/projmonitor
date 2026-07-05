# projmonitor# ProjMonitor

Sistema de informação web para monitorização de desempenho em projetos de software.

Projeto Final de Licenciatura em Engenharia Informática — Universidade Aberta
**Autora:** Beatriz Mucambe (n.º 2303641) · **Orientador:** José Coelho · Julho 2026

## O que faz

- Gestão de projetos com decomposição hierárquica do trabalho (WBS)
- Dois perfis: **Gestor de Projeto** e **Colaborador**, com controlo de acesso
- Registo de esforço estimado e real por tarefa
- Métricas automáticas: **percentagem de conclusão**, **desvio de esforço** e **nível de risco** (baixo / médio / elevado)
- Diagrama de **Gantt** interativo com setas de precedência
- Exportação de dados em **CSV**

## Tecnologias

Python 3.9 · Django 4.2 · SQLite 3 · Bootstrap 5 · HTML/CSS/JavaScript

## Como executar

```bash
# 1. Instalar dependências (recomendado: dentro de um ambiente virtual)
pip install -r requirements.txt

# 2. Criar a base de dados e carregar os dados de demonstração
python manage.py migrate
python manage.py loaddata demo_data.json

# 3. Arrancar o servidor
python manage.py runserver
```

Abrir <http://127.0.0.1:8000> no browser.

### Contas de demonstração

| Perfil | Utilizador | Password |
|---|---|---|
| Gestor de Projeto | `<preencher>` | `<preencher>` |
| Colaborador | `<preencher>` | `<preencher>` |

## Testes

```bash
python manage.py test
```

43 testes automatizados (21 unitários + 22 de integração), todos com resultado positivo.
Inclui ainda testes de desempenho: cálculo de métricas e exportação CSV < 100 ms para projetos com 100 tarefas.

## Estrutura

- `models.py` — entidades e regras de negócio (métricas, risco, WBS, precedências)
- `views.py` — controlo de acesso e orquestração
- `templates/` — interface (Bootstrap 5)
- `tests/` — classes de teste unitário e de integração
- `demo_data.json` — dados de demonstração (8 projetos)

## Documentação

O relatório final documenta a especificação, arquitetura, implementação e validação do sistema.
O Anexo II do relatório contém um tutorial ilustrado de utilização.
