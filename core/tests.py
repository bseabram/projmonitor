from datetime import timedelta

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from .models import DependenciaTarefa, Projeto, Tarefa, Utilizador


# ---------------------------------------------------------------------------
# Fixtures auxiliares
# ---------------------------------------------------------------------------

def criar_gestor(username="gestor"):
    return Utilizador.objects.create_user(
        username=username,
        password="teste123",
        papel=Utilizador.Papel.GESTOR_PROJETO,
    )

def criar_colaborador(username="colab"):
    return Utilizador.objects.create_user(
        username=username,
        password="teste123",
        papel=Utilizador.Papel.COLABORADOR,
    )

def criar_projeto(gestor, nome="Projeto Teste"):
    p = Projeto.objects.create(nome=nome, criado_por=gestor)
    p.participantes.add(gestor)
    return p


# ===========================================================================
# Testes unitários – Modelo Tarefa
# ===========================================================================

class TarefaFinalTest(TestCase):
    def setUp(self):
        self.gestor = criar_gestor()
        self.projeto = criar_projeto(self.gestor)

    def test_tarefa_sem_subtarefas_e_final(self):
        """RF04 – tarefa sem subtarefas deve ser considerada final."""
        t = Tarefa.objects.create(projeto=self.projeto, titulo="T1")
        self.assertTrue(t.is_tarefa_final())

    def test_tarefa_com_subtarefas_nao_e_final(self):
        """RF04 – tarefa com subtarefas não deve ser considerada final."""
        pai = Tarefa.objects.create(projeto=self.projeto, titulo="Pai")
        Tarefa.objects.create(projeto=self.projeto, titulo="Filho", tarefa_pai=pai)
        self.assertFalse(pai.is_tarefa_final())

    def test_tarefa_atrasada(self):
        """RF10 – tarefa final não concluída com prazo passado deve estar em atraso."""
        t = Tarefa.objects.create(
            projeto=self.projeto,
            titulo="Atrasada",
            prazo=timezone.localdate() - timedelta(days=1),
            estado=Tarefa.Estado.POR_INICIAR,
        )
        self.assertTrue(t.esta_atrasada())

    def test_tarefa_concluida_nao_esta_em_atraso(self):
        """Tarefa concluída com prazo passado não deve ser assinalada em atraso."""
        t = Tarefa.objects.create(
            projeto=self.projeto,
            titulo="Concluída",
            prazo=timezone.localdate() - timedelta(days=1),
            estado=Tarefa.Estado.CONCLUIDA,
        )
        self.assertFalse(t.esta_atrasada())

    def test_tarefa_sem_prazo_nao_esta_em_atraso(self):
        """Tarefa sem prazo definido nunca deve ser considerada em atraso."""
        t = Tarefa.objects.create(projeto=self.projeto, titulo="Sem prazo")
        self.assertFalse(t.esta_atrasada())


# ===========================================================================
# Testes unitários – Métricas do Projeto
# ===========================================================================

class MetricasProjetoTest(TestCase):
    def setUp(self):
        self.gestor = criar_gestor()
        self.projeto = criar_projeto(self.gestor)

    def test_percentagem_conclusao_zero_sem_tarefas(self):
        """RF09 – projeto sem tarefas finais deve ter 0% de conclusão."""
        self.assertEqual(self.projeto.percentagem_conclusao(), 0)

    def test_percentagem_conclusao_50_porcento(self):
        """RF09 – 1 de 2 tarefas finais concluídas = 50%."""
        Tarefa.objects.create(projeto=self.projeto, titulo="T1", estado=Tarefa.Estado.CONCLUIDA)
        Tarefa.objects.create(projeto=self.projeto, titulo="T2", estado=Tarefa.Estado.POR_INICIAR)
        self.assertEqual(self.projeto.percentagem_conclusao(), 50)

    def test_percentagem_conclusao_100_porcento(self):
        """RF09 – todas as tarefas finais concluídas = 100%."""
        Tarefa.objects.create(projeto=self.projeto, titulo="T1", estado=Tarefa.Estado.CONCLUIDA)
        Tarefa.objects.create(projeto=self.projeto, titulo="T2", estado=Tarefa.Estado.CONCLUIDA)
        self.assertEqual(self.projeto.percentagem_conclusao(), 100)

    def test_desvio_esforco_none_sem_estimativa(self):
        """RF09 – desvio de esforço deve ser None quando esforço estimado é 0."""
        Tarefa.objects.create(projeto=self.projeto, titulo="T1", esforco_estimado=0, esforco_real=5)
        self.assertIsNone(self.projeto.desvio_esforco())

    def test_desvio_esforco_positivo(self):
        """RF09 – desvio positivo quando esforço real supera estimado."""
        Tarefa.objects.create(projeto=self.projeto, titulo="T1", esforco_estimado=10, esforco_real=12)
        self.assertEqual(self.projeto.desvio_esforco(), 20.0)

    def test_desvio_esforco_negativo(self):
        """RF09 – desvio negativo quando esforço real é inferior ao estimado."""
        Tarefa.objects.create(projeto=self.projeto, titulo="T1", esforco_estimado=10, esforco_real=8)
        self.assertEqual(self.projeto.desvio_esforco(), -20.0)

    def test_nivel_risco_baixo(self):
        """RF09 – sem atrasos e desvio < 10% = risco baixo."""
        Tarefa.objects.create(projeto=self.projeto, titulo="T1", esforco_estimado=10, esforco_real=10,
                              estado=Tarefa.Estado.CONCLUIDA)
        self.assertEqual(self.projeto.nivel_risco(), "Risco baixo")

    def test_nivel_risco_elevado_por_atrasos(self):
        """RF09 – mais de 2 tarefas em atraso = risco elevado."""
        for i in range(3):
            Tarefa.objects.create(
                projeto=self.projeto, titulo=f"T{i}",
                prazo=timezone.localdate() - timedelta(days=1),
                estado=Tarefa.Estado.POR_INICIAR,
            )
        self.assertEqual(self.projeto.nivel_risco(), "Risco elevado")

    def test_nivel_risco_elevado_por_desvio(self):
        """RF09 – desvio de esforço > 20% = risco elevado."""
        Tarefa.objects.create(projeto=self.projeto, titulo="T1", esforco_estimado=10, esforco_real=13)
        self.assertEqual(self.projeto.nivel_risco(), "Risco elevado")


# ===========================================================================
# Testes unitários – Validações de Negócio
# ===========================================================================

class ValidacoesNegocioTest(TestCase):
    def setUp(self):
        self.gestor = criar_gestor()
        self.colaborador = criar_colaborador()
        self.projeto = criar_projeto(self.gestor)
        self.projeto.participantes.add(self.colaborador)

    def test_pode_atribuir_colaborador_participante(self):
        """RF06 – colaborador associado ao projeto pode ser atribuído a tarefa."""
        t = Tarefa(
            projeto=self.projeto,
            titulo="T1",
            responsavel=self.colaborador,
        )
        t.full_clean()  # não deve lançar exceção

    def test_nao_pode_atribuir_colaborador_nao_participante(self):
        """RF06 – colaborador não associado ao projeto não pode receber tarefa."""
        from django.core.exceptions import ValidationError
        outro = criar_colaborador("outro")
        t = Tarefa(projeto=self.projeto, titulo="T1", responsavel=outro)
        with self.assertRaises(ValidationError):
            t.full_clean()

    def test_nao_pode_atribuir_gestor_como_responsavel(self):
        """RF06 – gestor não pode ser responsável por uma tarefa."""
        from django.core.exceptions import ValidationError
        t = Tarefa(projeto=self.projeto, titulo="T1", responsavel=self.gestor)
        with self.assertRaises(ValidationError):
            t.full_clean()

    def test_dependencia_valida(self):
        """RF04/RF05 – dependência entre tarefas do mesmo projeto é válida."""
        t1 = Tarefa.objects.create(projeto=self.projeto, titulo="T1")
        t2 = Tarefa.objects.create(projeto=self.projeto, titulo="T2")
        dep = DependenciaTarefa(predecessora=t1, sucessora=t2)
        dep.full_clean()  # não deve lançar exceção

    def test_dependencia_propria_invalida(self):
        """Tarefa não pode depender de si própria."""
        from django.core.exceptions import ValidationError
        t = Tarefa.objects.create(projeto=self.projeto, titulo="T1")
        dep = DependenciaTarefa(predecessora=t, sucessora=t)
        with self.assertRaises(ValidationError):
            dep.full_clean()

    def test_validacao_precedencia_bloqueia_transicao(self):
        """RF05 – tarefa não pode transitar para EM_EXECUCAO se predecessora não concluída."""
        t1 = Tarefa.objects.create(projeto=self.projeto, titulo="T1", estado=Tarefa.Estado.POR_INICIAR)
        t2 = Tarefa.objects.create(projeto=self.projeto, titulo="T2")
        DependenciaTarefa.objects.create(predecessora=t1, sucessora=t2)
        pode, erro = t2.pode_transitar_estado(Tarefa.Estado.EM_EXECUCAO)
        self.assertFalse(pode)
        self.assertIsNotNone(erro)

    def test_validacao_precedencia_permite_transicao_apos_conclusao(self):
        """RF05 – tarefa pode transitar se predecessora estiver concluída."""
        t1 = Tarefa.objects.create(projeto=self.projeto, titulo="T1", estado=Tarefa.Estado.CONCLUIDA)
        t2 = Tarefa.objects.create(projeto=self.projeto, titulo="T2")
        DependenciaTarefa.objects.create(predecessora=t1, sucessora=t2)
        pode, erro = t2.pode_transitar_estado(Tarefa.Estado.EM_EXECUCAO)
        self.assertTrue(pode)


# ===========================================================================
# Testes de integração – Views
# ===========================================================================

class ViewsGestorTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.gestor = criar_gestor()
        self.client.login(username="gestor", password="teste123")

    def test_dashboard_acessivel(self):
        """Dashboard deve ser acessível a utilizador autenticado."""
        r = self.client.get(reverse("dashboard"))
        self.assertEqual(r.status_code, 200)

    def test_criar_projeto_get(self):
        """Formulário de criação de projeto deve retornar 200."""
        r = self.client.get(reverse("criar_projeto"))
        self.assertEqual(r.status_code, 200)

    def test_criar_projeto_post(self):
        """POST válido deve criar projeto e redirecionar."""
        r = self.client.post(reverse("criar_projeto"), {
            "nome": "Proj Teste",
            "descricao": "",
            "data_inicio": "2026-01-01",
            "data_fim_prevista": "2026-06-30",
            "estado": "ATIVO",
        })
        self.assertEqual(Projeto.objects.count(), 1)
        p = Projeto.objects.first()
        self.assertRedirects(r, reverse("detalhe_projeto", args=[p.id]))

    def test_criar_projeto_cria_tarefa_raiz(self):
        """Criação de projeto deve criar automaticamente uma tarefa raiz (RF03)."""
        self.client.post(reverse("criar_projeto"), {
            "nome": "Proj Raiz",
            "descricao": "",
            "data_inicio": "2026-01-01",
            "data_fim_prevista": "2026-06-30",
            "estado": "ATIVO",
        })
        p = Projeto.objects.first()
        self.assertEqual(p.tarefas.count(), 1)
        self.assertIsNone(p.tarefas.first().tarefa_pai)

    def test_detalhe_projeto_acessivel(self):
        """Detalhe do projeto deve retornar 200."""
        p = criar_projeto(self.gestor)
        r = self.client.get(reverse("detalhe_projeto", args=[p.id]))
        self.assertEqual(r.status_code, 200)

    def test_exportar_csv(self):
        """Exportação CSV deve retornar ficheiro com content-type correto."""
        p = criar_projeto(self.gestor)
        r = self.client.get(reverse("exportar_csv", args=[p.id]))
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r["Content-Type"])


class ViewsColaboradorTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.gestor = criar_gestor()
        self.colaborador = criar_colaborador()
        self.projeto = criar_projeto(self.gestor)
        self.projeto.participantes.add(self.colaborador)
        self.client.login(username="colab", password="teste123")

    def test_minhas_tarefas_acessivel(self):
        """Área do colaborador deve ser acessível."""
        r = self.client.get(reverse("minhas_tarefas"))
        self.assertEqual(r.status_code, 200)

    def test_colaborador_nao_pode_criar_projeto(self):
        """Colaborador não deve poder criar projetos."""
        r = self.client.get(reverse("criar_projeto"))
        self.assertEqual(r.status_code, 403)

    def test_atualizar_tarefa_colaborador(self):
        """Colaborador deve conseguir atualizar o estado da sua tarefa."""
        t = Tarefa.objects.create(
            projeto=self.projeto,
            titulo="Tarefa colab",
            responsavel=self.colaborador,
        )
        r = self.client.post(reverse("atualizar_tarefa_colaborador", args=[t.id]), {
            "estado": "EM_EXECUCAO",
            "esforco_real": "3",
        })
        t.refresh_from_db()
        self.assertEqual(t.estado, Tarefa.Estado.EM_EXECUCAO)


class AutenticacaoTest(TestCase):
    def test_redirect_sem_login(self):
        """Utilizador não autenticado deve ser redirecionado para login."""
        r = Client().get(reverse("dashboard"))
        self.assertRedirects(r, "/login/?next=/")

    def test_login_valido(self):
        """Login com credenciais válidas deve redirecionar para dashboard."""
        criar_gestor("u1")
        c = Client()
        r = c.post("/login/", {"username": "u1", "password": "teste123"})
        self.assertRedirects(r, "/")


class SuperuserGestorTest(TestCase):
    """Superutilizador deve ter acesso de gestor mesmo com papel=COLABORADOR."""

    def setUp(self):
        self.client = Client()
        self.admin = Utilizador.objects.create_superuser(
            username="admin_test", password="admin123",
            papel=Utilizador.Papel.COLABORADOR,
        )
        self.client.login(username="admin_test", password="admin123")

    def test_superuser_pode_criar_projeto(self):
        r = self.client.get(reverse("criar_projeto"))
        self.assertEqual(r.status_code, 200)

    def test_superuser_pode_criar_utilizador(self):
        r = self.client.get(reverse("criar_utilizador"))
        self.assertEqual(r.status_code, 200)


class NotasTarefaTest(TestCase):
    """Campo notas deve ser guardado e visível."""

    def setUp(self):
        self.client = Client()
        self.gestor = criar_gestor()
        self.projeto = criar_projeto(self.gestor)
        self.client.login(username="gestor", password="teste123")

    def test_notas_guardadas(self):
        t = Tarefa.objects.create(projeto=self.projeto, titulo="T notas", notas="Nota de teste")
        t.refresh_from_db()
        self.assertEqual(t.notas, "Nota de teste")

    def test_detalhe_tarefa_mostra_notas(self):
        t = Tarefa.objects.create(projeto=self.projeto, titulo="T notas", notas="Nota visível")
        r = self.client.get(reverse("detalhe_tarefa", args=[t.id]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Nota visível")


class ApagarTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.gestor = criar_gestor()
        self.projeto = criar_projeto(self.gestor)
        self.client.login(username="gestor", password="teste123")

    def test_apagar_tarefa(self):
        t = Tarefa.objects.create(projeto=self.projeto, titulo="Para apagar")
        r = self.client.post(reverse("apagar_tarefa", args=[t.id]))
        self.assertFalse(Tarefa.objects.filter(id=t.id).exists())
        self.assertRedirects(r, reverse("detalhe_projeto", args=[self.projeto.id]))

    def test_apagar_projeto(self):
        p = criar_projeto(self.gestor, nome="Apagar este")
        r = self.client.post(reverse("apagar_projeto", args=[p.id]))
        self.assertFalse(Projeto.objects.filter(id=p.id).exists())
        self.assertRedirects(r, reverse("lista_projetos"))

    def test_colaborador_nao_pode_apagar_tarefa(self):
        colab = criar_colaborador()
        self.projeto.participantes.add(colab)
        t = Tarefa.objects.create(projeto=self.projeto, titulo="T")
        c = Client()
        c.login(username="colab", password="teste123")
        r = c.post(reverse("apagar_tarefa", args=[t.id]))
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Tarefa.objects.filter(id=t.id).exists())


class PesquisaProjetosTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.gestor = criar_gestor()
        self.client.login(username="gestor", password="teste123")
        criar_projeto(self.gestor, nome="Alpha")
        criar_projeto(self.gestor, nome="Beta")

    def test_filtro_por_nome(self):
        r = self.client.get(reverse("lista_projetos") + "?q=Alpha")
        self.assertContains(r, "Alpha")
        self.assertNotContains(r, "Beta")

    def test_filtro_por_estado(self):
        r = self.client.get(reverse("lista_projetos") + "?estado=ATIVO")
        self.assertEqual(r.status_code, 200)


class AlterarPasswordTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.gestor = criar_gestor()
        self.client.login(username="gestor", password="teste123")

    def test_pagina_acessivel(self):
        r = self.client.get(reverse("alterar_password"))
        self.assertEqual(r.status_code, 200)

    def test_alterar_password_valida(self):
        r = self.client.post(reverse("alterar_password"), {
            "old_password": "teste123",
            "new_password1": "NovaPass456!",
            "new_password2": "NovaPass456!",
        })
        self.assertRedirects(r, reverse("dashboard"))
        self.gestor.refresh_from_db()
        self.assertTrue(self.gestor.check_password("NovaPass456!"))
