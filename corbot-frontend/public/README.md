# Pasta Public - Assets Estáticos

Esta pasta contém arquivos estáticos que são servidos diretamente na raiz do site.

## Logo do Sistema (Whitelabel)

Para personalizar a logo do sistema:

1. **Adicione sua logo nesta pasta** (`public/`)
   - Formatos suportados: PNG, JPG, SVG
   - Exemplos de nomes: `logo.png`, `logo.svg`, `marca.png`

2. **Configure no arquivo `.env`**
   ```env
   SYSTEM_LOGO_URL=/logo.png
   ```
   
   Ou se colocar em uma subpasta:
   ```env
   SYSTEM_LOGO_URL=/assets/logo.svg
   ```

3. **Reinicie os containers**
   ```bash
   sudo docker compose restart web frontend
   ```

## Estrutura de Exemplo

```
public/
├── README.md (este arquivo)
├── logo.png            # Logo principal (configure: SYSTEM_LOGO_URL=/logo.png)
├── favicon.ico         # Favicon do site
└── assets/
    └── logo-dark.svg   # Logo alternativa (configure: SYSTEM_LOGO_URL=/assets/logo-dark.svg)
```

## Recomendações

- **Tamanho**: 200-400px de largura (altura proporcional)
- **Formato**: SVG (escalável) ou PNG com fundo transparente
- **Peso**: Máximo 500KB para melhor performance
- **Proporção**: Horizontal (tipo logotipo) funciona melhor que quadrada

## Acessando os Arquivos

Arquivos nesta pasta são acessíveis diretamente:
- `public/logo.png` → `http://seusite.com/logo.png`
- `public/assets/icone.svg` → `http://seusite.com/assets/icone.svg`
