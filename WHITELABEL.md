# Sistema Whitelabel CorbanPlus

## Visão Geral

O sistema agora suporta whitelabel completo, permitindo personalizar o nome e logo via variáveis de ambiente.

## Configuração

### Backend (.env)

```env
# Whitelabel - Configurações de Branding
SYSTEM_NAME=CorbanPlus
SYSTEM_LOGO_URL=https://example.com/logo.png
```

### Frontend

O frontend consome automaticamente as configurações do backend através do endpoint `/api/config/whitelabel/`.

## Componentes

### Backend

- **Settings** (`corbot/settings.py`): Define `WHITELABEL_SYSTEM_NAME` e `WHITELABEL_LOGO_URL`
- **View** (`core/views/config.py`): Endpoint público `/api/config/whitelabel/`
- **URL** (`core/urls.py`): Rota registrada

### Frontend

- **Context** (`contexts/WhitelabelContext.tsx`): Provider que busca e distribui configurações
- **Componentes**:
  - `SidebarContent.tsx`: Usa logo e nome do whitelabel
  - `LoginForm.tsx`: Exibe nome do sistema
  - `SetupPage.tsx`: Exibe nome do sistema
- **Layouts**: Todos os layouts incluem o WhitelabelProvider

## Como Usar

### 1. Alterar o nome do sistema
```env
SYSTEM_NAME=MeuCorban
```

### 2. Adicionar logo personalizada

Você tem duas opções:

**Opção A: Logo na pasta `public/`** (recomendado)

1. Coloque sua logo em `corbot-frontend/public/` (ex: `logo.png`, `logo.svg`)
2. Configure o caminho relativo no `.env`:
   ```env
   SYSTEM_LOGO_URL=/logo.png
   ```

**Opção B: Logo externa (URL completa)**
```env
SYSTEM_LOGO_URL=https://meudominio.com/logo.png
```

### 3. Reiniciar containers
```bash
sudo docker compose restart web frontend
```

> **Nota**: Arquivos na pasta `public/` são servidos na raiz do site. Uma logo em `public/logo.png` fica acessível em `/logo.png`.

## Valores Padrão

- **Nome**: CorbanPlus
- **Logo**: Inicial do nome em círculo com cor primária

## Endpoints

- `GET /api/config/whitelabel/`: Retorna configurações (público, sem autenticação)
  ```json
  {
    "system_name": "CorbanPlus",
    "logo_url": "https://example.com/logo.png"
  }
  ```
