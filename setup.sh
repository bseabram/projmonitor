#!/bin/bash
# Script de configuração rápida do projeto

echo "=== Configuração do Sistema de Monitorização ==="

# 1. Criar e ativar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Criar migrações e aplicar
python manage.py makemigrations core
python manage.py migrate

# 4. Criar superutilizador gestor
echo ""
echo "Criar utilizador gestor (papel: GESTOR_PROJETO):"
python manage.py shell -c "
from core.models import Utilizador
if not Utilizador.objects.filter(username='admin').exists():
    u = Utilizador.objects.create_superuser('admin', 'admin@exemplo.pt', 'admin123')
    u.papel = Utilizador.Papel.GESTOR_PROJETO
    u.save()
    print('Utilizador admin criado (password: admin123)')
else:
    print('Utilizador admin já existe')
"

echo ""
echo "=== Configuração concluída ==="
echo "Para iniciar o servidor: python manage.py runserver"
echo "Aceder em: http://127.0.0.1:8000"
echo "Admin Django: http://127.0.0.1:8000/admin"
