"""
Mockdata dos principais bancos nacionais do Brasil
Códigos FEBRABAN para identificação dos bancos
"""

BANCOS_NACIONAIS = [
    {
        "nome": "Banco do Brasil S.A.",
        "codigo": "001",
        "ativo": True
    },
    {
        "nome": "Banco Central do Brasil",
        "codigo": "002", 
        "ativo": True
    },
    {
        "nome": "Banco da Amazônia S.A.",
        "codigo": "003",
        "ativo": True
    },
    {
        "nome": "Banco do Nordeste do Brasil S.A.",
        "codigo": "004",
        "ativo": True
    },
    {
        "nome": "Banco Nacional de Desenvolvimento Econômico e Social",
        "codigo": "007",
        "ativo": True
    },
    {
        "nome": "Banco Meridional do Brasil",
        "codigo": "008",
        "ativo": True
    },
    {
        "nome": "Banco Regional de Brasília S.A.",
        "codigo": "070",
        "ativo": True
    },
    {
        "nome": "Banco de Brasília S.A.",
        "codigo": "070",
        "ativo": True
    },
    {
        "nome": "Banco Inter S.A.",
        "codigo": "077",
        "ativo": True
    },
    {
        "nome": "Banco do Estado de Sergipe S.A.",
        "codigo": "047",
        "ativo": True
    },
    {
        "nome": "Banco Cooperativo Sicredi S.A.",
        "codigo": "748",
        "ativo": True
    },
    {
        "nome": "Banco Cooperativo do Brasil S.A.",
        "codigo": "756",
        "ativo": True
    },
    {
        "nome": "Banco Original S.A.",
        "codigo": "212",
        "ativo": True
    },
    {
        "nome": "Banco Pan S.A.",
        "codigo": "623",
        "ativo": True
    },
    {
        "nome": "Banco Itaú S.A.",
        "codigo": "341",
        "ativo": True
    },
    {
        "nome": "Banco Bradesco S.A.",
        "codigo": "237",
        "ativo": True
    },
    {
        "nome": "Banco Santander (Brasil) S.A.",
        "codigo": "033",
        "ativo": True
    },
    {
        "nome": "Caixa Econômica Federal",
        "codigo": "104",
        "ativo": True
    },
    {
        "nome": "Banco Safra S.A.",
        "codigo": "422",
        "ativo": True
    },
    {
        "nome": "Banco Votorantim S.A.",
        "codigo": "655",
        "ativo": True
    },
    {
        "nome": "Banco BTG Pactual S.A.",
        "codigo": "208",
        "ativo": True
    },
    {
        "nome": "Banco C6 S.A.",
        "codigo": "336",
        "ativo": True
    },
    {
        "nome": "Banco Digio S.A.",
        "codigo": "335",
        "ativo": True
    },
    {
        "nome": "Banco Next S.A.",
        "codigo": "237",
        "ativo": True
    },
    {
        "nome": "Banco Neon S.A.",
        "codigo": "735",
        "ativo": True
    },
    {
        "nome": "Banco Nubank S.A.",
        "codigo": "260",
        "ativo": True
    },
    {
        "nome": "Banco PicPay S.A.",
        "codigo": "380",
        "ativo": True
    },
    {
        "nome": "Banco Stone S.A.",
        "codigo": "197",
        "ativo": True
    },
    {
        "nome": "Banco Will S.A.",
        "codigo": "280",
        "ativo": True
    },
    {
        "nome": "Banco Agibank S.A.",
        "codigo": "121",
        "ativo": True
    },
    {
        "nome": "Banco Alfa S.A.",
        "codigo": "025",
        "ativo": True
    },
    {
        "nome": "Banco Banrisul S.A.",
        "codigo": "041",
        "ativo": True
    },
    {
        "nome": "Banco BV S.A.",
        "codigo": "655",
        "ativo": True
    },
    {
        "nome": "Banco Daycoval S.A.",
        "codigo": "707",
        "ativo": True
    },
    {
        "nome": "Banco Fibra S.A.",
        "codigo": "224",
        "ativo": True
    },
    {
        "nome": "Banco Genial S.A.",
        "codigo": "125",
        "ativo": True
    },
    {
        "nome": "Banco Guanabara S.A.",
        "codigo": "612",
        "ativo": True
    },
    {
        "nome": "Banco Itaucard S.A.",
        "codigo": "376",
        "ativo": True
    },
    {
        "nome": "Banco Modal S.A.",
        "codigo": "746",
        "ativo": True
    },
    {
        "nome": "Banco Pine S.A.",
        "codigo": "643",
        "ativo": True
    },
    {
        "nome": "Banco Rendimento S.A.",
        "codigo": "633",
        "ativo": True
    },
    {
        "nome": "Banco Sofisa S.A.",
        "codigo": "637",
        "ativo": True
    },
    {
        "nome": "Banco Topázio S.A.",
        "codigo": "082",
        "ativo": True
    },
    {
        "nome": "Banco Triângulo S.A.",
        "codigo": "634",
        "ativo": True
    },
    {
        "nome": "Banco Unicred S.A.",
        "codigo": "136",
        "ativo": True
    },
    {
        "nome": "Banco Xp S.A.",
        "codigo": "348",
        "ativo": True
    }
]

# Função para obter banco por código
def get_banco_por_codigo(codigo):
    """
    Retorna o banco correspondente ao código informado
    """
    for banco in BANCOS_NACIONAIS:
        if banco["codigo"] == codigo:
            return banco
    return None

# Função para obter banco por nome
def get_banco_por_nome(nome):
    """
    Retorna o banco correspondente ao nome informado (busca parcial)
    """
    for banco in BANCOS_NACIONAIS:
        if nome.lower() in banco["nome"].lower():
            return banco
    return None

# Função para obter todos os bancos ativos
def get_bancos_ativos():
    """
    Retorna apenas os bancos marcados como ativos
    """
    return [banco for banco in BANCOS_NACIONAIS if banco["ativo"]]

# Função para obter lista de códigos
def get_codigos_bancos():
    """
    Retorna apenas os códigos dos bancos
    """
    return [banco["codigo"] for banco in BANCOS_NACIONAIS]

# Função para obter lista de nomes
def get_nomes_bancos():
    """
    Retorna apenas os nomes dos bancos
    """
    return [banco["nome"] for banco in BANCOS_NACIONAIS] 