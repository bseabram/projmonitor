from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Utilizador(AbstractUser):
    class Papel(models.TextChoices):
        GESTOR_PROJETO = "GESTOR_PROJETO", "Gestor de Projeto"
        COLABORADOR = "COLABORADOR", "Colaborador"

    papel = models.CharField(
        max_length=30,
        choices=Papel.choices,
        default=Papel.COLABORADOR,
    )

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_papel_display()})"


class Projeto(models.Model):
    class Estado(models.TextChoices):
        ATIVO = "ATIVO", "Ativo"
        CONCLUIDO = "CONCLUIDO", "Concluído"
        ARQUIVADO = "ARQUIVADO", "Arquivado"

    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    data_inicio = models.DateField(default=timezone.localdate)
    data_fim_prevista = models.DateField(null=True, blank=True)
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.ATIVO,
    )
    participantes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="projetos",
        blank=True,
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="projetos_criados",
        on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ["-data_inicio"]

    def tarefas_finais(self):
        return self.tarefas.filter(subtarefas__isnull=True).distinct()

    def percentagem_conclusao(self):
        tarefas = self.tarefas_finais()
        total = tarefas.count()
        if total == 0:
            return 0
        concluidas = tarefas.filter(estado=Tarefa.Estado.CONCLUIDA).count()
        return round((concluidas / total) * 100, 2)

    def desvio_esforco(self):
        tarefas = self.tarefas_finais()
        estimado = sum(t.esforco_estimado or 0 for t in tarefas)
        real = sum(t.esforco_real or 0 for t in tarefas)
        if estimado == 0:
            return None
        return round(((real - estimado) / estimado) * 100, 2)

    def tarefas_em_atraso(self):
        return [t for t in self.tarefas_finais() if t.esta_atrasada()]

    def nivel_risco(self):
        desvio = self.desvio_esforco()
        atrasadas = len(self.tarefas_em_atraso())
        if atrasadas > 2 or (desvio is not None and desvio > 20):
            return "Risco elevado"
        if atrasadas > 0 or (desvio is not None and desvio >= 10):
            return "Risco médio"
        return "Risco baixo"

    def nivel_risco_css(self):
        nivel = self.nivel_risco()
        if nivel == "Risco elevado":
            return "danger"
        if nivel == "Risco médio":
            return "warning"
        return "success"

    def __str__(self):
        return self.nome


class Tarefa(models.Model):
    class Estado(models.TextChoices):
        POR_INICIAR = "POR_INICIAR", "Por iniciar"
        EM_EXECUCAO = "EM_EXECUCAO", "Em execução"
        CONCLUIDA = "CONCLUIDA", "Concluída"

    projeto = models.ForeignKey(
        Projeto, related_name="tarefas", on_delete=models.CASCADE
    )
    tarefa_pai = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="subtarefas",
        on_delete=models.CASCADE,
    )
    titulo = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.POR_INICIAR,
    )
    prazo = models.DateField(null=True, blank=True)
    esforco_estimado = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        verbose_name="Esforço estimado (h)"
    )
    esforco_real = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        verbose_name="Esforço real (h)"
    )
    notas = models.TextField(blank=True, verbose_name="Notas")
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="tarefas_atribuidas",
        on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ["tarefa_pai__id", "id"]

    def is_tarefa_final(self):
        return not self.subtarefas.exists()

    def esta_atrasada(self):
        if not self.prazo:
            return False
        return (
            self.is_tarefa_final()
            and self.estado != self.Estado.CONCLUIDA
            and timezone.localdate() > self.prazo
        )

    def predecessoras(self):
        return Tarefa.objects.filter(
            dependencias_como_predecessora__sucessora=self
        )

    def pode_transitar_estado(self, novo_estado):
        """Valida se a tarefa pode transitar para o novo estado (respeita precedências)."""
        if novo_estado in (self.Estado.EM_EXECUCAO, self.Estado.CONCLUIDA):
            for pred in self.predecessoras():
                if pred.estado != self.Estado.CONCLUIDA:
                    return False, f"A tarefa predecessora '{pred.titulo}' ainda não está concluída."
        return True, None

    def clean(self):
        if self.responsavel:
            if self.responsavel.papel != Utilizador.Papel.COLABORADOR:
                raise ValidationError("A tarefa só pode ser atribuída a um colaborador.")
            if self.projeto_id and not self.projeto.participantes.filter(
                id=self.responsavel_id
            ).exists():
                raise ValidationError("O colaborador deve estar associado ao projeto.")

    def nivel_arvore(self):
        """Retorna o nível de profundidade na hierarquia (0 = raiz)."""
        nivel = 0
        pai = self.tarefa_pai
        while pai is not None:
            nivel += 1
            pai = pai.tarefa_pai
        return nivel

    def __str__(self):
        return self.titulo


class DependenciaTarefa(models.Model):
    predecessora = models.ForeignKey(
        Tarefa,
        related_name="dependencias_como_predecessora",
        on_delete=models.CASCADE,
    )
    sucessora = models.ForeignKey(
        Tarefa,
        related_name="dependencias_como_sucessora",
        on_delete=models.CASCADE,
    )

    class Meta:
        unique_together = ("predecessora", "sucessora")

    def clean(self):
        if self.predecessora_id == self.sucessora_id:
            raise ValidationError("Uma tarefa não pode depender de si própria.")
        if self.predecessora.projeto_id != self.sucessora.projeto_id:
            raise ValidationError(
                "As tarefas dependentes devem pertencer ao mesmo projeto."
            )

    def __str__(self):
        return f"{self.predecessora} → {self.sucessora}"
