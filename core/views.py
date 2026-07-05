import csv
import json
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    AdicionarParticipanteForm,
    DependenciaForm,
    ProjetoForm,
    SubtarefaForm,
    TarefaColaboradorForm,
    TarefaForm,
    UtilizadorForm,
)
from .models import DependenciaTarefa, Projeto, Tarefa, Utilizador


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_gestor(user):
    return user.is_superuser or user.papel == Utilizador.Papel.GESTOR_PROJETO


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    if is_gestor(request.user):
        projetos = Projeto.objects.filter(participantes=request.user) | \
                   Projeto.objects.filter(criado_por=request.user)
        projetos = projetos.distinct()
    else:
        projetos = Projeto.objects.filter(participantes=request.user)

    context = {
        "projetos": projetos,
        "total_projetos": projetos.count(),
        "projetos_ativos": projetos.filter(estado=Projeto.Estado.ATIVO).count(),
    }
    return render(request, "core/dashboard.html", context)


# ---------------------------------------------------------------------------
# Projetos
# ---------------------------------------------------------------------------

@login_required
def lista_projetos(request):
    if is_gestor(request.user):
        projetos = (Projeto.objects.filter(participantes=request.user) |
                    Projeto.objects.filter(criado_por=request.user)).distinct()
    else:
        projetos = Projeto.objects.filter(participantes=request.user)

    q = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "").strip()
    if q:
        projetos = projetos.filter(nome__icontains=q)
    if estado:
        projetos = projetos.filter(estado=estado)

    paginator = Paginator(projetos, 10)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "core/lista_projetos.html", {
        "page_obj": page,
        "projetos": page.object_list,
        "q": q,
        "estado": estado,
        "estados": Projeto.Estado.choices,
    })


@login_required
def criar_projeto(request):
    if not is_gestor(request.user):
        return HttpResponseForbidden("Apenas gestores podem criar projetos.")
    if request.method == "POST":
        form = ProjetoForm(request.POST)
        if form.is_valid():
            projeto = form.save(commit=False)
            projeto.criado_por = request.user
            projeto.save()
            projeto.participantes.add(request.user)
            # Criar tarefa raiz
            Tarefa.objects.create(
                projeto=projeto,
                titulo=f"Trabalho global – {projeto.nome}",
                descricao="Tarefa raiz do projeto. Decomponha em subtarefas.",
            )
            messages.success(request, "Projeto criado com sucesso.")
            return redirect("detalhe_projeto", projeto_id=projeto.id)
    else:
        form = ProjetoForm()
    return render(request, "core/form_projeto.html", {"form": form, "titulo": "Novo Projeto"})


@login_required
def apagar_projeto(request, projeto_id):
    projeto = get_object_or_404(Projeto, id=projeto_id)
    if not is_gestor(request.user):
        return HttpResponseForbidden()
    if request.method == "POST":
        projeto.delete()
        messages.success(request, "Projeto apagado.")
        return redirect("lista_projetos")
    return render(request, "core/confirmar_apagar.html", {"objeto": projeto, "tipo": "projeto"})


@login_required
def editar_projeto(request, projeto_id):
    projeto = get_object_or_404(Projeto, id=projeto_id)
    if not is_gestor(request.user):
        return HttpResponseForbidden()
    if request.method == "POST":
        form = ProjetoForm(request.POST, instance=projeto)
        if form.is_valid():
            form.save()
            messages.success(request, "Projeto atualizado.")
            return redirect("detalhe_projeto", projeto_id=projeto.id)
    else:
        form = ProjetoForm(instance=projeto)
    return render(request, "core/form_projeto.html", {"form": form, "titulo": "Editar Projeto", "projeto": projeto})


@login_required
def detalhe_projeto(request, projeto_id):
    projeto = get_object_or_404(Projeto, id=projeto_id)
    tarefas_raiz = projeto.tarefas.filter(tarefa_pai__isnull=True)
    atrasadas = projeto.tarefas_em_atraso()
    context = {
        "projeto": projeto,
        "tarefas_raiz": tarefas_raiz,
        "atrasadas": atrasadas,
        "desvio": projeto.desvio_esforco(),
        "conclusao": projeto.percentagem_conclusao(),
        "risco": projeto.nivel_risco(),
        "risco_css": projeto.nivel_risco_css(),
        "is_gestor": is_gestor(request.user),
    }
    return render(request, "core/detalhe_projeto.html", context)


@login_required
def gantt_projeto(request, projeto_id):
    projeto = get_object_or_404(Projeto, id=projeto_id)

    hoje = date.today()
    data_inicio = projeto.data_inicio
    data_fim    = projeto.data_fim_prevista or hoje

    tarefas = list(projeto.tarefas.all().order_by('id'))

    # Build maps for start-date calculation based on predecessors
    task_map   = {t.id: t for t in tarefas}
    pred_map   = {}   # task_id -> [predecessor_id, ...]
    for t in tarefas:
        pred_map[t.id] = list(
            t.dependencias_como_sucessora.values_list('predecessora_id', flat=True)
        )

    # Compute start: max(effective_end of predecessors) or project start
    # effective_end = max(computed_start[p], task.prazo) to avoid start > end clamping
    computed_start = {}
    computed_end   = {}

    def get_end(tid):
        if tid in computed_end:
            return computed_end[tid]
        start = get_start(tid)
        prazo = task_map[tid].prazo if tid in task_map else None
        computed_end[tid] = max(start, prazo) if prazo else start
        return computed_end[tid]

    def get_start(tid):
        if tid in computed_start:
            return computed_start[tid]
        preds = pred_map.get(tid, [])
        if not preds:
            computed_start[tid] = data_inicio
        else:
            ends = [get_end(p) for p in preds if p in task_map]
            computed_start[tid] = max(ends) if ends else data_inicio
        return computed_start[tid]

    for t in tarefas:
        get_start(t.id)
        get_end(t.id)

    # Short label: T01, T02, ...
    task_label = {t.id: 'T%02d' % (i + 1) for i, t in enumerate(tarefas)}

    tarefas_data = []
    for t in tarefas:
        ini = computed_start[t.id]
        fim = t.prazo or data_fim
        if ini > fim:
            fim = ini

        estado_css = {
            'CONCLUIDA':   'success',
            'EM_EXECUCAO': 'warning',
            'POR_INICIAR': 'secondary',
        }.get(t.estado, 'secondary')

        predecessoras = pred_map[t.id]
        pred_labels   = [task_label[p] for p in predecessoras if p in task_label]

        duracao = max(1, (fim - ini).days)

        tarefas_data.append({
            'id':           t.id,
            'ref':          task_label[t.id],
            'titulo':       t.titulo,
            'estado':       t.get_estado_display() if hasattr(t, 'get_estado_display') else t.estado,
            'estado_css':   estado_css,
            'inicio':       ini.isoformat(),
            'fim':          fim.isoformat(),
            'duracao':      duracao,
            'responsavel':  str(t.responsavel) if t.responsavel else '—',
            'concluida':    t.estado == 'CONCLUIDA',
            'em_curso':     t.estado in ('EM_EXECUCAO',),
            'predecessoras': predecessoras,
            'pred_labels':  pred_labels,
        })

    context = {
        'projeto':      projeto,
        'tarefas_json': json.dumps(tarefas_data),
        'data_inicio':  data_inicio.isoformat(),
        'data_fim':     data_fim.isoformat(),
        'is_gestor':    is_gestor(request.user),
    }
    return render(request, 'core/gantt_projeto.html', context)


# ---------------------------------------------------------------------------
# Colaboradores
# ---------------------------------------------------------------------------

@login_required
def adicionar_participante(request, projeto_id):
    projeto = get_object_or_404(Projeto, id=projeto_id)
    if not is_gestor(request.user):
        return HttpResponseForbidden()
    if request.method == "POST":
        form = AdicionarParticipanteForm(request.POST)
        if form.is_valid():
            utilizador = form.cleaned_data["utilizador"]
            projeto.participantes.add(utilizador)
            messages.success(request, f"{utilizador} adicionado ao projeto.")
            return redirect("detalhe_projeto", projeto_id=projeto.id)
    else:
        form = AdicionarParticipanteForm()
    return render(request, "core/form_participante.html", {"form": form, "projeto": projeto})


@login_required
def remover_participante(request, projeto_id, utilizador_id):
    projeto = get_object_or_404(Projeto, id=projeto_id)
    if not is_gestor(request.user):
        return HttpResponseForbidden()
    utilizador = get_object_or_404(Utilizador, id=utilizador_id)
    projeto.participantes.remove(utilizador)
    messages.success(request, f"{utilizador} removido do projeto.")
    return redirect("detalhe_projeto", projeto_id=projeto.id)


# ---------------------------------------------------------------------------
# Tarefas
# ---------------------------------------------------------------------------

@login_required
def detalhe_tarefa(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, id=tarefa_id)
    return render(request, "core/detalhe_tarefa.html", {
        "tarefa": tarefa,
        "is_gestor": is_gestor(request.user),
    })


@login_required
def criar_tarefa(request, projeto_id):
    projeto = get_object_or_404(Projeto, id=projeto_id)
    if not is_gestor(request.user):
        return HttpResponseForbidden()
    if request.method == "POST":
        form = TarefaForm(request.POST, projeto=projeto)
        if form.is_valid():
            tarefa = form.save(commit=False)
            tarefa.projeto = projeto
            tarefa.save()
            messages.success(request, "Tarefa criada.")
            return redirect("detalhe_projeto", projeto_id=projeto.id)
    else:
        form = TarefaForm(projeto=projeto)
    return render(request, "core/form_tarefa.html", {"form": form, "projeto": projeto, "titulo": "Nova Tarefa"})


@login_required
def editar_tarefa(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, id=tarefa_id)
    projeto = tarefa.projeto
    if not is_gestor(request.user):
        return HttpResponseForbidden()
    if request.method == "POST":
        form = TarefaForm(request.POST, instance=tarefa, projeto=projeto)
        if form.is_valid():
            novo_estado = form.cleaned_data.get("estado")
            pode, erro = tarefa.pode_transitar_estado(novo_estado)
            if not pode:
                form.add_error("estado", erro)
            else:
                form.save()
                messages.success(request, "Tarefa atualizada.")
                return redirect("detalhe_projeto", projeto_id=projeto.id)
    else:
        form = TarefaForm(instance=tarefa, projeto=projeto)
    return render(request, "core/form_tarefa.html", {"form": form, "projeto": projeto, "titulo": "Editar Tarefa", "tarefa": tarefa})


@login_required
def decompor_tarefa(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, id=tarefa_id)
    if not is_gestor(request.user):
        return HttpResponseForbidden()
    if tarefa.estado == Tarefa.Estado.CONCLUIDA:
        messages.error(request, "Não é possível decompor uma tarefa concluída.")
        return redirect("detalhe_projeto", projeto_id=tarefa.projeto.id)
    if tarefa.responsavel:
        messages.error(request, "Retire o responsável antes de decompor a tarefa.")
        return redirect("detalhe_projeto", projeto_id=tarefa.projeto.id)
    if request.method == "POST":
        form = SubtarefaForm(request.POST)
        if form.is_valid():
            subtarefa = form.save(commit=False)
            subtarefa.projeto = tarefa.projeto
            subtarefa.tarefa_pai = tarefa
            subtarefa.save()
            messages.success(request, "Subtarefa criada.")
            return redirect("detalhe_projeto", projeto_id=tarefa.projeto.id)
    else:
        form = SubtarefaForm()
    return render(request, "core/form_decomposicao.html", {"form": form, "tarefa": tarefa})


@login_required
def apagar_tarefa(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, id=tarefa_id)
    projeto = tarefa.projeto
    if not is_gestor(request.user):
        return HttpResponseForbidden()
    if request.method == "POST":
        tarefa.delete()
        messages.success(request, "Tarefa apagada.")
        return redirect("detalhe_projeto", projeto_id=projeto.id)
    return render(request, "core/confirmar_apagar.html", {"objeto": tarefa, "tipo": "tarefa", "projeto": projeto})


@login_required
def adicionar_dependencia(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, id=tarefa_id)
    if not is_gestor(request.user):
        return HttpResponseForbidden()
    if request.method == "POST":
        form = DependenciaForm(request.POST, tarefa=tarefa)
        if form.is_valid():
            dep = form.save(commit=False)
            dep.sucessora = tarefa
            try:
                dep.full_clean()
                dep.save()
                messages.success(request, "Dependência adicionada.")
            except Exception as e:
                messages.error(request, str(e))
            return redirect("detalhe_projeto", projeto_id=tarefa.projeto.id)
    else:
        form = DependenciaForm(tarefa=tarefa)
    return render(request, "core/form_dependencia.html", {"form": form, "tarefa": tarefa})


@login_required
def remover_dependencia(request, dep_id):
    dep = get_object_or_404(DependenciaTarefa, id=dep_id)
    projeto_id = dep.sucessora.projeto.id
    if not is_gestor(request.user):
        return HttpResponseForbidden()
    dep.delete()
    messages.success(request, "Dependência removida.")
    return redirect("detalhe_projeto", projeto_id=projeto_id)


# ---------------------------------------------------------------------------
# Área do colaborador
# ---------------------------------------------------------------------------

@login_required
def minhas_tarefas(request):
    qs = Tarefa.objects.filter(responsavel=request.user).order_by("prazo")
    paginator = Paginator(qs, 10)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "core/minhas_tarefas.html", {"tarefas": page.object_list, "page_obj": page})


@login_required
def atualizar_tarefa_colaborador(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, id=tarefa_id, responsavel=request.user)
    if request.method == "POST":
        form = TarefaColaboradorForm(request.POST, instance=tarefa)
        if form.is_valid():
            novo_estado = form.cleaned_data.get("estado")
            pode, erro = tarefa.pode_transitar_estado(novo_estado)
            if not pode:
                form.add_error("estado", erro)
            else:
                form.save()
                messages.success(request, "Tarefa atualizada.")
                return redirect("minhas_tarefas")
    else:
        form = TarefaColaboradorForm(instance=tarefa)
    return render(request, "core/form_tarefa_colaborador.html", {"form": form, "tarefa": tarefa})


# ---------------------------------------------------------------------------
# Exportação CSV
# ---------------------------------------------------------------------------

@login_required
def exportar_csv(request, projeto_id):
    projeto = get_object_or_404(Projeto, id=projeto_id)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="projeto_{projeto.id}.csv"'
    response.write("﻿")  # BOM para Excel reconhecer UTF-8

    writer = csv.writer(response)
    writer.writerow(["Relatório do Projeto"])
    writer.writerow(["Projeto", projeto.nome])
    writer.writerow(["Estado", projeto.get_estado_display()])
    writer.writerow(["Data de início", projeto.data_inicio])
    writer.writerow(["Data prevista de conclusão", projeto.data_fim_prevista or "N/D"])
    writer.writerow(["Percentagem de conclusão (%)", projeto.percentagem_conclusao()])
    desvio = projeto.desvio_esforco()
    writer.writerow(["Desvio de esforço (%)", desvio if desvio is not None else "N/A"])
    writer.writerow(["Nível de risco", projeto.nivel_risco()])
    writer.writerow([])
    writer.writerow(["Tarefa", "Estado", "Prazo", "Esforço estimado (h)",
                     "Esforço real (h)", "Responsável", "Em atraso"])
    for tarefa in projeto.tarefas_finais():
        writer.writerow([
            tarefa.titulo,
            tarefa.get_estado_display(),
            tarefa.prazo or "",
            tarefa.esforco_estimado,
            tarefa.esforco_real,
            tarefa.responsavel.get_full_name() if tarefa.responsavel else "",
            "Sim" if tarefa.esta_atrasada() else "Não",
        ])
    return response


# ---------------------------------------------------------------------------
# Gestão de utilizadores (admin simplificado)
# ---------------------------------------------------------------------------

@login_required
def alterar_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password alterada com sucesso.")
            return redirect("dashboard")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "core/alterar_password.html", {"form": form})


@login_required
def criar_utilizador(request):
    if not is_gestor(request.user):
        return HttpResponseForbidden()
    if request.method == "POST":
        form = UtilizadorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Utilizador criado com sucesso.")
            return redirect("dashboard")
    else:
        form = UtilizadorForm()
    return render(request, "core/form_utilizador.html", {"form": form})
