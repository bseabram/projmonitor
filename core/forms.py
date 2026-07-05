from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import DependenciaTarefa, Projeto, Tarefa, Utilizador


class UtilizadorForm(UserCreationForm):
    class Meta:
        model = Utilizador
        fields = ["username", "first_name", "last_name", "email", "papel", "password1", "password2"]


class ProjetoForm(forms.ModelForm):
    class Meta:
        model = Projeto
        fields = ["nome", "descricao", "data_inicio", "data_fim_prevista", "estado"]
        widgets = {
            "data_inicio": forms.DateInput(attrs={"type": "date"}),
            "data_fim_prevista": forms.DateInput(attrs={"type": "date"}),
            "descricao": forms.Textarea(attrs={"rows": 3}),
        }


class TarefaForm(forms.ModelForm):
    class Meta:
        model = Tarefa
        fields = ["titulo", "descricao", "estado", "prazo", "esforco_estimado", "esforco_real", "responsavel", "notas"]
        widgets = {
            "prazo": forms.DateInput(attrs={"type": "date"}),
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "notas": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, projeto=None, **kwargs):
        super().__init__(*args, **kwargs)
        if projeto:
            self.fields["responsavel"].queryset = projeto.participantes.filter(
                papel=Utilizador.Papel.COLABORADOR
            )
        else:
            self.fields["responsavel"].queryset = Utilizador.objects.none()
        self.fields["responsavel"].required = False


class TarefaColaboradorForm(forms.ModelForm):
    """Formulário simplificado para o colaborador atualizar o estado e esforço real."""
    class Meta:
        model = Tarefa
        fields = ["estado", "esforco_real", "notas"]
        widgets = {
            "notas": forms.Textarea(attrs={"rows": 3}),
        }


class SubtarefaForm(forms.ModelForm):
    class Meta:
        model = Tarefa
        fields = ["titulo", "descricao", "prazo", "esforco_estimado"]
        widgets = {
            "prazo": forms.DateInput(attrs={"type": "date"}),
            "descricao": forms.Textarea(attrs={"rows": 3}),
        }


class DependenciaForm(forms.ModelForm):
    class Meta:
        model = DependenciaTarefa
        fields = ["predecessora"]

    def __init__(self, *args, tarefa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tarefa:
            # Exclui a própria tarefa e tarefas que já dependem desta (evitar ciclos simples)
            self.fields["predecessora"].queryset = Tarefa.objects.filter(
                projeto=tarefa.projeto
            ).exclude(id=tarefa.id)


class AdicionarParticipanteForm(forms.Form):
    utilizador = forms.ModelChoiceField(
        queryset=Utilizador.objects.filter(papel=Utilizador.Papel.COLABORADOR),
        label="Colaborador",
    )
