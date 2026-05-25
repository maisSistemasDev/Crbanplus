#!/bin/bash

# Script shell para criar um superusuário no sistema Corbot
# Execute: ./create_admin.sh


# Dados do administrador (customize conforme necessário)
CPF="13007481767"
EMAIL="danielproença@gmail.com"
PASSWORD="rosacruz89D!"
NOME="Auto Promotora"
SOBRENOME="Admin"
EMPRESA="Auto Promotora"
CNPJ="51.057.418/0001-76"

# Executar o script de criação de superusuário
python3 add_superuser.py \
  --cpf "$CPF" \
  --email "$EMAIL" \
  --password "$PASSWORD" \
  --nome "$NOME" \
  --sobrenome "$SOBRENOME" \
  --empresa "$EMPRESA" \
  --cnpj "$CNPJ"

# Instruções finais
echo ""
echo "Se o usuário foi criado com sucesso, você pode fazer login com:"
echo "CPF: $CPF"
echo "Senha: $PASSWORD"
echo ""
echo "IMPORTANTE: Altere a senha padrão após o primeiro login!" 