from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import DependenciaTarefa, Projeto, Tarefa, Utilizador


class Command(BaseCommand):
    help = "Cria dados de demonstração para screenshots"

    def handle(self, *args, **options):
        # --- Utilizadores ---
        admin, _ = Utilizador.objects.get_or_create(
            username="admin",
            defaults=dict(papel=Utilizador.Papel.GESTOR_PROJETO, is_superuser=True, is_staff=True),
        )
        admin.set_password("admin123")
        admin.first_name = "Ana"
        admin.last_name = "Silva"
        admin.save()

        gestor, _ = Utilizador.objects.get_or_create(
            username="gestor",
            defaults=dict(papel=Utilizador.Papel.GESTOR_PROJETO),
        )
        gestor.set_password("gestor123")
        gestor.first_name = "Carlos"
        gestor.last_name = "Ferreira"
        gestor.save()

        colab1, _ = Utilizador.objects.get_or_create(
            username="joao",
            defaults=dict(papel=Utilizador.Papel.COLABORADOR),
        )
        colab1.set_password("joao123")
        colab1.first_name = "João"
        colab1.last_name = "Costa"
        colab1.save()

        colab2, _ = Utilizador.objects.get_or_create(
            username="maria",
            defaults=dict(papel=Utilizador.Papel.COLABORADOR),
        )
        colab2.set_password("maria123")
        colab2.first_name = "Maria"
        colab2.last_name = "Santos"
        colab2.save()

        colab3, _ = Utilizador.objects.get_or_create(
            username="rui",
            defaults=dict(papel=Utilizador.Papel.COLABORADOR),
        )
        colab3.set_password("rui123")
        colab3.first_name = "Rui"
        colab3.last_name = "Oliveira"
        colab3.save()

        today = timezone.localdate()

        # --- Projeto 1: em curso com risco médio ---
        p1, created = Projeto.objects.get_or_create(
            nome="Sistema de Gestão de Clientes",
            defaults=dict(
                descricao="Desenvolvimento de uma plataforma CRM para acompanhamento de clientes e oportunidades comerciais.",
                data_inicio=today - timedelta(days=60),
                data_fim_prevista=today + timedelta(days=30),
                estado=Projeto.Estado.ATIVO,
                criado_por=admin,
            ),
        )
        if created:
            p1.participantes.add(admin, gestor, colab1, colab2)
            # Tarefa raiz
            raiz1 = Tarefa.objects.create(projeto=p1, titulo="Trabalho global – Sistema de Gestão de Clientes")

            # Fase 1: Requisitos
            fase1 = Tarefa.objects.create(projeto=p1, tarefa_pai=raiz1, titulo="Fase 1 – Levantamento de Requisitos",
                                          esforco_estimado=20)
            t1 = Tarefa.objects.create(projeto=p1, tarefa_pai=fase1, titulo="Entrevistas com stakeholders",
                                       estado=Tarefa.Estado.CONCLUIDA, esforco_estimado=8, esforco_real=9,
                                       prazo=today - timedelta(days=40), responsavel=colab1,
                                       notas="Realizadas 5 entrevistas. Requisitos documentados em Confluence.")
            t2 = Tarefa.objects.create(projeto=p1, tarefa_pai=fase1, titulo="Documento de requisitos",
                                       estado=Tarefa.Estado.CONCLUIDA, esforco_estimado=12, esforco_real=14,
                                       prazo=today - timedelta(days=30), responsavel=colab2,
                                       notas="Versão 1.2 aprovada pelo cliente a 15/04.")

            # Fase 2: Design
            fase2 = Tarefa.objects.create(projeto=p1, tarefa_pai=raiz1, titulo="Fase 2 – Design e Arquitetura",
                                          esforco_estimado=30)
            t3 = Tarefa.objects.create(projeto=p1, tarefa_pai=fase2, titulo="Modelação da base de dados",
                                       estado=Tarefa.Estado.CONCLUIDA, esforco_estimado=10, esforco_real=12,
                                       prazo=today - timedelta(days=20), responsavel=colab1,
                                       notas="Diagrama ER revisto após feedback da reunião de 20/04.")
            t4 = Tarefa.objects.create(projeto=p1, tarefa_pai=fase2, titulo="Wireframes do frontend",
                                       estado=Tarefa.Estado.EM_EXECUCAO, esforco_estimado=20, esforco_real=10,
                                       prazo=today + timedelta(days=5), responsavel=colab2)

            # Fase 3: Desenvolvimento
            fase3 = Tarefa.objects.create(projeto=p1, tarefa_pai=raiz1, titulo="Fase 3 – Desenvolvimento",
                                          esforco_estimado=80)
            t5 = Tarefa.objects.create(projeto=p1, tarefa_pai=fase3, titulo="API de autenticação",
                                       estado=Tarefa.Estado.EM_EXECUCAO, esforco_estimado=15, esforco_real=8,
                                       prazo=today + timedelta(days=10), responsavel=colab1)
            t6 = Tarefa.objects.create(projeto=p1, tarefa_pai=fase3, titulo="Módulo de clientes",
                                       estado=Tarefa.Estado.POR_INICIAR, esforco_estimado=25,
                                       prazo=today + timedelta(days=20), responsavel=colab2)
            t7 = Tarefa.objects.create(projeto=p1, tarefa_pai=fase3, titulo="Módulo de oportunidades",
                                       estado=Tarefa.Estado.POR_INICIAR, esforco_estimado=20,
                                       prazo=today - timedelta(days=5), responsavel=colab1,
                                       notas="Dependente do módulo de clientes. Rever prazo com o gestor.")
            t8 = Tarefa.objects.create(projeto=p1, tarefa_pai=fase3, titulo="Relatórios e exportação",
                                       estado=Tarefa.Estado.POR_INICIAR, esforco_estimado=20,
                                       prazo=today + timedelta(days=25), responsavel=colab2)

            DependenciaTarefa.objects.create(predecessora=t3, sucessora=t5)
            DependenciaTarefa.objects.create(predecessora=t5, sucessora=t6)
            DependenciaTarefa.objects.create(predecessora=t6, sucessora=t7)

        # --- Projeto 2: concluído ---
        p2, created = Projeto.objects.get_or_create(
            nome="Portal de Recursos Humanos",
            defaults=dict(
                descricao="Migração do sistema legado de RH para uma aplicação web moderna com gestão de férias, faltas e avaliações.",
                data_inicio=today - timedelta(days=120),
                data_fim_prevista=today - timedelta(days=10),
                estado=Projeto.Estado.CONCLUIDO,
                criado_por=gestor,
            ),
        )
        if created:
            p2.participantes.add(gestor, colab2, colab3)
            raiz2 = Tarefa.objects.create(projeto=p2, titulo="Trabalho global – Portal de Recursos Humanos")
            fase_a = Tarefa.objects.create(projeto=p2, tarefa_pai=raiz2, titulo="Análise e Planeamento")
            Tarefa.objects.create(projeto=p2, tarefa_pai=fase_a, titulo="Análise do sistema legado",
                                  estado=Tarefa.Estado.CONCLUIDA, esforco_estimado=15, esforco_real=13,
                                  prazo=today - timedelta(days=100), responsavel=colab3)
            Tarefa.objects.create(projeto=p2, tarefa_pai=fase_a, titulo="Plano de migração",
                                  estado=Tarefa.Estado.CONCLUIDA, esforco_estimado=10, esforco_real=11,
                                  prazo=today - timedelta(days=90), responsavel=colab2)
            fase_b = Tarefa.objects.create(projeto=p2, tarefa_pai=raiz2, titulo="Desenvolvimento")
            Tarefa.objects.create(projeto=p2, tarefa_pai=fase_b, titulo="Gestão de férias",
                                  estado=Tarefa.Estado.CONCLUIDA, esforco_estimado=30, esforco_real=28,
                                  prazo=today - timedelta(days=50), responsavel=colab3)
            Tarefa.objects.create(projeto=p2, tarefa_pai=fase_b, titulo="Gestão de faltas",
                                  estado=Tarefa.Estado.CONCLUIDA, esforco_estimado=20, esforco_real=22,
                                  prazo=today - timedelta(days=40), responsavel=colab2)
            Tarefa.objects.create(projeto=p2, tarefa_pai=fase_b, titulo="Avaliações de desempenho",
                                  estado=Tarefa.Estado.CONCLUIDA, esforco_estimado=25, esforco_real=24,
                                  prazo=today - timedelta(days=30), responsavel=colab3)
            fase_c = Tarefa.objects.create(projeto=p2, tarefa_pai=raiz2, titulo="Testes e Implantação")
            Tarefa.objects.create(projeto=p2, tarefa_pai=fase_c, titulo="Testes de aceitação",
                                  estado=Tarefa.Estado.CONCLUIDA, esforco_estimado=15, esforco_real=16,
                                  prazo=today - timedelta(days=20), responsavel=colab2)
            Tarefa.objects.create(projeto=p2, tarefa_pai=fase_c, titulo="Implantação em produção",
                                  estado=Tarefa.Estado.CONCLUIDA, esforco_estimado=5, esforco_real=5,
                                  prazo=today - timedelta(days=10), responsavel=colab3)

        # --- Projeto 3: novo, em risco ---
        p3, created = Projeto.objects.get_or_create(
            nome="Plataforma E-learning",
            defaults=dict(
                descricao="Desenvolvimento de plataforma de ensino online com cursos, quizzes e certificados.",
                data_inicio=today - timedelta(days=15),
                data_fim_prevista=today + timedelta(days=75),
                estado=Projeto.Estado.ATIVO,
                criado_por=admin,
            ),
        )
        if created:
            p3.participantes.add(admin, colab1, colab3)
            raiz3 = Tarefa.objects.create(projeto=p3, titulo="Trabalho global – Plataforma E-learning")
            Tarefa.objects.create(projeto=p3, tarefa_pai=raiz3, titulo="Definição da arquitetura",
                                  estado=Tarefa.Estado.CONCLUIDA, esforco_estimado=10, esforco_real=10,
                                  prazo=today - timedelta(days=10), responsavel=colab1)
            Tarefa.objects.create(projeto=p3, tarefa_pai=raiz3, titulo="Módulo de cursos",
                                  estado=Tarefa.Estado.EM_EXECUCAO, esforco_estimado=40, esforco_real=5,
                                  prazo=today + timedelta(days=30), responsavel=colab3)
            Tarefa.objects.create(projeto=p3, tarefa_pai=raiz3, titulo="Sistema de quizzes",
                                  estado=Tarefa.Estado.POR_INICIAR, esforco_estimado=25,
                                  prazo=today - timedelta(days=3), responsavel=colab1,
                                  notas="Prazo ultrapassado. Aguarda conclusão do módulo de cursos.")
            Tarefa.objects.create(projeto=p3, tarefa_pai=raiz3, titulo="Emissão de certificados",
                                  estado=Tarefa.Estado.POR_INICIAR, esforco_estimado=15,
                                  prazo=today + timedelta(days=60), responsavel=colab3)

        self.stdout.write(self.style.SUCCESS(
            "\nDados criados com sucesso!\n"
            "  admin   / admin123  (Gestor de Projeto / superutilizador)\n"
            "  gestor  / gestor123 (Gestor de Projeto)\n"
            "  joao    / joao123   (Colaborador)\n"
            "  maria   / maria123  (Colaborador)\n"
            "  rui     / rui123    (Colaborador)\n\n"
            "Projetos:\n"
            "  1. Sistema de Gestão de Clientes – ativo, risco médio\n"
            "  2. Portal de Recursos Humanos    – concluído, risco baixo\n"
            "  3. Plataforma E-learning         – ativo, risco elevado\n"
        ))
