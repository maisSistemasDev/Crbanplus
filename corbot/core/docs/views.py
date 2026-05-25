from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def api_docs(request):
    """
    Documentação da API do CorbanPlus.
    """
    null = None
    return render(request, 'docs/api_docs.html', {
        'title': 'Documentação da API CorbanPlus',
        'endpoints': [
            {
                'name': 'Autenticação',
                'endpoints': [
                    {
                        'url': '/api/token/',
                        'method': 'POST',
                        'description': 'Obter token JWT',
                        'request_example': {
                            'cpf': '123.456.789-00',
                            'password': 'senha123'
                        },
                        'response_example': {
                            'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                            'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                        }
                    },
                    {
                        'url': '/api/token/refresh/',
                        'method': 'POST',
                        'description': 'Renovar token JWT',
                        'request_example': {
                            'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                        },
                        'response_example': {
                            'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                        }
                    }
                ]
            },
            {
                'name': 'Empresas',
                'endpoints': [
                    {
                        'url': '/api/companies/',
                        'method': 'GET',
                        'description': 'Listar empresas (filtradas por permissão)',
                        'response_example': [
                            {
                                'id': '123e4567-e89b-12d3-a456-426614174000',
                                'name': 'Empresa Exemplo',
                                'trading_name': 'Exemplo Ltda',
                                'cnpj': '12.345.678/0001-90',
                                'logo': '/media/company_logos/logo.png',
                                'primary_color': '#3498db',
                                'secondary_color': '#2c3e50',
                                'accent_color': '#e74c3c',
                                'settings': {},
                                'email': 'contato@exemplo.com',
                                'phone': '(11) 1234-5678',
                                'website': 'https://exemplo.com',
                                'address': 'Rua Exemplo, 123',
                                'city': 'São Paulo',
                                'state': 'SP',
                                'zip_code': '01234-567',
                                'is_active': True
                            }
                        ]
                    },
                    {
                        'url': '/api/companies/',
                        'method': 'POST',
                        'description': 'Criar nova empresa (apenas Admin)',
                        'request_example': {
                            'name': 'Nova Empresa',
                            'trading_name': 'Nova Ltda',
                            'cnpj': '98.765.432/0001-10',
                            'primary_color': '#3498db',
                            'secondary_color': '#2c3e50',
                            'accent_color': '#e74c3c',
                            'email': 'contato@novaempresa.com',
                            'phone': '(11) 9876-5432',
                            'website': 'https://novaempresa.com'
                        },
                        'response_example': {
                            'id': '123e4567-e89b-12d3-a456-426614174001',
                            'name': 'Nova Empresa',
                            'trading_name': 'Nova Ltda',
                            'cnpj': '98.765.432/0001-10',
                            'logo': null,
                            'primary_color': '#3498db',
                            'secondary_color': '#2c3e50',
                            'accent_color': '#e74c3c',
                            'settings': {},
                            'email': 'contato@novaempresa.com',
                            'phone': '(11) 9876-5432',
                            'website': 'https://novaempresa.com',
                            'address': null,
                            'city': null,
                            'state': null,
                            'zip_code': null,
                            'is_active': True
                        }
                    },
                    {
                        'url': '/api/companies/{id}/',
                        'method': 'GET',
                        'description': 'Obter detalhes de uma empresa',
                        'response_example': {
                            'id': '123e4567-e89b-12d3-a456-426614174000',
                            'name': 'Empresa Exemplo',
                            'trading_name': 'Exemplo Ltda',
                            'cnpj': '12.345.678/0001-90',
                            'logo': '/media/company_logos/logo.png',
                            'primary_color': '#3498db',
                            'secondary_color': '#2c3e50',
                            'accent_color': '#e74c3c',
                            'settings': {},
                            'email': 'contato@exemplo.com',
                            'phone': '(11) 1234-5678',
                            'website': 'https://exemplo.com',
                            'address': 'Rua Exemplo, 123',
                            'city': 'São Paulo',
                            'state': 'SP',
                            'zip_code': '01234-567',
                            'is_active': True
                        }
                    },
                    {
                        'url': '/api/companies/{id}/',
                        'method': 'PUT/PATCH',
                        'description': 'Atualizar empresa (apenas Admin)',
                        'request_example': {
                            'name': 'Empresa Atualizada',
                            'primary_color': '#2980b9'
                        },
                        'response_example': {
                            'id': '123e4567-e89b-12d3-a456-426614174000',
                            'name': 'Empresa Atualizada',
                            'trading_name': 'Exemplo Ltda',
                            'cnpj': '12.345.678/0001-90',
                            'logo': '/media/company_logos/logo.png',
                            'primary_color': '#2980b9',
                            'secondary_color': '#2c3e50',
                            'accent_color': '#e74c3c',
                            'settings': {},
                            'email': 'contato@exemplo.com',
                            'phone': '(11) 1234-5678',
                            'website': 'https://exemplo.com',
                            'address': 'Rua Exemplo, 123',
                            'city': 'São Paulo',
                            'state': 'SP',
                            'zip_code': '01234-567',
                            'is_active': True
                        }
                    },
                    {
                        'url': '/api/companies/{id}/',
                        'method': 'DELETE',
                        'description': 'Excluir empresa (apenas Admin)',
                        'response_example': {
                            'detail': 'Empresa excluída com sucesso.'
                        }
                    }
                ]
            },
            {
                'name': 'Usuários',
                'endpoints': [
                    {
                        'url': '/api/users/',
                        'method': 'GET',
                        'description': 'Listar usuários (filtrados por hierarquia)',
                        'response_example': [
                            {
                                'id': 1,
                                'cpf': '123.456.789-00',
                                'email': 'gerente@exemplo.com',
                                'first_name': 'Nome',
                                'last_name': 'Sobrenome',
                                'role': 'gerente',
                                'leader': null,
                                'company': '123e4567-e89b-12d3-a456-426614174000',
                                'company_name': 'Empresa Exemplo',
                                'is_active': True,
                                'is_gerente': True,
                                'is_lider': False,
                                'is_vendedor': False,
                                'leader_name': null
                            }
                        ]
                    },
                    {
                        'url': '/api/users/',
                        'method': 'POST',
                        'description': 'Criar novo usuário (apenas Gerente)',
                        'request_example': {
                            'cpf': '987.654.321-00',
                            'email': 'vendedor@exemplo.com',
                            'password': 'senha123',
                            'first_name': 'Novo',
                            'last_name': 'Vendedor',
                            'role': 'vendedor',
                            'leader': 2,
                            'company': '123e4567-e89b-12d3-a456-426614174000',
                            'extra_data': {
                                'rg': '12.345.678-9',
                                'phone': '(11) 98765-4321'
                            }
                        },
                        'response_example': {
                            'id': 3,
                            'cpf': '987.654.321-00',
                            'email': 'vendedor@exemplo.com',
                            'first_name': 'Novo',
                            'last_name': 'Vendedor',
                            'role': 'vendedor',
                            'leader': 2,
                            'company': '123e4567-e89b-12d3-a456-426614174000',
                            'company_name': 'Empresa Exemplo',
                            'is_active': True,
                            'is_gerente': False,
                            'is_lider': False,
                            'is_vendedor': True,
                            'extra_data': {
                                'rg': '12.345.678-9',
                                'phone': '(11) 98765-4321',
                                'rg_emission_date': null,
                                'rg_emission_organ': null,
                                'birth_date': null,
                                'address': null,
                                'city': null,
                                'state': null,
                                'zip_code': null
                            }
                        }
                    },
                    {
                        'url': '/api/users/{id}/',
                        'method': 'GET',
                        'description': 'Obter detalhes de um usuário',
                        'response_example': {
                            'id': 1,
                            'cpf': '123.456.789-00',
                            'email': 'gerente@exemplo.com',
                            'first_name': 'Nome',
                            'last_name': 'Sobrenome',
                            'role': 'gerente',
                            'leader': null,
                            'company': '123e4567-e89b-12d3-a456-426614174000',
                            'company_name': 'Empresa Exemplo',
                            'is_active': True,
                            'is_gerente': True,
                            'is_lider': False,
                            'is_vendedor': False,
                            'extra_data': {
                                'rg': '12.345.678-9',
                                'rg_emission_date': '2010-01-01',
                                'rg_emission_organ': 'SSP',
                                'birth_date': '1990-01-01',
                                'phone': '(11) 98765-4321',
                                'address': 'Rua Exemplo, 123',
                                'city': 'São Paulo',
                                'state': 'SP',
                                'zip_code': '01234-567'
                            }
                        }
                    },
                    {
                        'url': '/api/users/{id}/',
                        'method': 'PUT/PATCH',
                        'description': 'Atualizar usuário (apenas Gerente)',
                        'request_example': {
                            'first_name': 'Nome Atualizado',
                            'extra_data': {
                                'phone': '(11) 91234-5678'
                            }
                        },
                        'response_example': {
                            'id': 1,
                            'cpf': '123.456.789-00',
                            'email': 'gerente@exemplo.com',
                            'first_name': 'Nome Atualizado',
                            'last_name': 'Sobrenome',
                            'role': 'gerente',
                            'leader': null,
                            'company': '123e4567-e89b-12d3-a456-426614174000',
                            'company_name': 'Empresa Exemplo',
                            'is_active': True,
                            'is_gerente': True,
                            'is_lider': False,
                            'is_vendedor': False,
                            'extra_data': {
                                'rg': '12.345.678-9',
                                'rg_emission_date': '2010-01-01',
                                'rg_emission_organ': 'SSP',
                                'birth_date': '1990-01-01',
                                'phone': '(11) 91234-5678',
                                'address': 'Rua Exemplo, 123',
                                'city': 'São Paulo',
                                'state': 'SP',
                                'zip_code': '01234-567'
                            }
                        }
                    },
                    {
                        'url': '/api/users/{id}/',
                        'method': 'DELETE',
                        'description': 'Excluir usuário (apenas Gerente)',
                        'response_example': {
                            'detail': 'Usuário excluído com sucesso.'
                        }
                    },
                    {
                        'url': '/api/users/vendedores/',
                        'method': 'GET',
                        'description': 'Listar vendedores (Gerente vê todos, Líder vê apenas os seus)',
                        'response_example': [
                            {
                                'id': 3,
                                'cpf': '987.654.321-00',
                                'email': 'vendedor@exemplo.com',
                                'first_name': 'Novo',
                                'last_name': 'Vendedor',
                                'role': 'vendedor',
                                'leader': 2,
                                'company': '123e4567-e89b-12d3-a456-426614174000',
                                'company_name': 'Empresa Exemplo',
                                'is_active': True,
                                'is_gerente': False,
                                'is_lider': False,
                                'is_vendedor': True,
                                'leader_name': 'Nome Líder'
                            }
                        ]
                    },
                    {
                        'url': '/api/users/lideres/',
                        'method': 'GET',
                        'description': 'Listar líderes (apenas Gerente)',
                        'response_example': [
                            {
                                'id': 2,
                                'cpf': '456.789.123-00',
                                'email': 'lider@exemplo.com',
                                'first_name': 'Nome',
                                'last_name': 'Líder',
                                'role': 'lider',
                                'leader': null,
                                'company': '123e4567-e89b-12d3-a456-426614174000',
                                'company_name': 'Empresa Exemplo',
                                'is_active': True,
                                'is_gerente': False,
                                'is_lider': True,
                                'is_vendedor': False,
                                'leader_name': null
                            }
                        ]
                    },
                    {
                        'url': '/api/users/{id}/change_leader/',
                        'method': 'POST',
                        'description': 'Alterar líder de um vendedor (apenas Gerente)',
                        'request_example': {
                            'leader_id': 2
                        },
                        'response_example': {
                            'detail': 'Líder alterado com sucesso.'
                        }
                    }
                ]
            }
        ]
    }) 