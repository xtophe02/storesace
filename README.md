# StoreSace - Retail Analytics Database

Sistema de análise de vendas para rede de retalho portuguesa com dados de 2020-2026.

## Estrutura de Dados

### Tabelas Principais

- **items** - Catálogo de produtos (~40k artigos)
- **stores** - Lojas (Braga, Fafe, Quintã, Loja Online)
- **da_stores_date** - Vendas diárias por loja (particionado por ano)
- **da_items_stores_date** - Vendas diárias por artigo/loja (particionado por mês)

### Métricas Disponíveis

- Quantidade vendida, receita líquida, descontos
- Custos e margens (latest_price_cost, price_average_cost)
- Quebras, devoluções (credits), desperdícios
- Número de vendas e clientes

## Quick Start

### 1. Iniciar Base de Dados

```bash
docker compose up -d
```

Isto cria:
- PostgreSQL 16 em localhost:5432
- pgAdmin (opcional) em localhost:5050

### 2. Importar Dados

```bash
./import_database.py
```

O script:
- Cria o schema `prod_515383678`
- Importa tabelas mestras (items, stores)
- Cria 9 partições anuais para da_stores_date
- Cria 72+ partições mensais para da_items_stores_date
- Verifica a importação

**Tempo estimado**: 5-15 minutos (dependendo do hardware)

### 3. Conectar à Base de Dados

```bash
# Via psql
docker exec -it storesace_db psql -U storesace -d storesace

# Definir schema
SET search_path TO prod_515383678;

# Query exemplo
SELECT name, code FROM stores;
```

**Credenciais:**
- Host: localhost
- Port: 5432
- Database: storesace
- Schema: prod_515383678
- User: storesace
- Password: storesace_dev

## Queries Exemplo

### Vendas de Hoje

```sql
SET search_path TO prod_515383678;

SELECT
    s.name,
    d.nr_sales,
    d.nr_persons,
    d.total_net as receita_liquida,
    d.total_doc as total_com_iva
FROM da_stores_date d
JOIN stores s ON s.id = d.store_id
WHERE d.date = CURRENT_DATE;
```

### Top 10 Artigos (Por Receita)

```sql
SET search_path TO prod_515383678;

SELECT
    i.description,
    i.pcode,
    SUM(d.total_quantity) as qtd_total,
    SUM(d.total_net) as receita_liquida,
    SUM(d.total_net - (d.total_quantity * d.latest_price_cost)) as margem_estimada
FROM da_items_stores_date d
JOIN items i ON i.id = d.item_id
WHERE d.date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY i.id, i.description, i.pcode
ORDER BY receita_liquida DESC
LIMIT 10;
```

### Comparação Ano Anterior

```sql
SET search_path TO prod_515383678;

SELECT
    s.name as loja,
    SUM(CASE WHEN EXTRACT(YEAR FROM d.date) = EXTRACT(YEAR FROM CURRENT_DATE)
        THEN d.total_net ELSE 0 END) as vendas_este_ano,
    SUM(CASE WHEN EXTRACT(YEAR FROM d.date) = EXTRACT(YEAR FROM CURRENT_DATE) - 1
        THEN d.total_net ELSE 0 END) as vendas_ano_anterior,
    ROUND(
        (SUM(CASE WHEN EXTRACT(YEAR FROM d.date) = EXTRACT(YEAR FROM CURRENT_DATE) THEN d.total_net ELSE 0 END) -
         SUM(CASE WHEN EXTRACT(YEAR FROM d.date) = EXTRACT(YEAR FROM CURRENT_DATE) - 1 THEN d.total_net ELSE 0 END)) /
        NULLIF(SUM(CASE WHEN EXTRACT(YEAR FROM d.date) = EXTRACT(YEAR FROM CURRENT_DATE) - 1 THEN d.total_net ELSE 0 END), 0) * 100,
        2
    ) as variacao_percentual
FROM da_stores_date d
JOIN stores s ON s.id = d.store_id
WHERE d.date >= (CURRENT_DATE - INTERVAL '2 years')
GROUP BY s.name
ORDER BY vendas_este_ano DESC;
```

### Artigos com Prejuízo

```sql
SET search_path TO prod_515383678;

-- Artigos onde custo > preço de venda (sem IVA)
SELECT
    i.description,
    i.pcode,
    AVG(d.latest_price_cost) as custo_medio,
    AVG(d.total_price / NULLIF(d.total_quantity, 0)) as preco_venda_medio,
    SUM(d.total_quantity) as qtd_vendida_30d
FROM da_items_stores_date d
JOIN items i ON i.id = d.item_id
WHERE d.date >= CURRENT_DATE - INTERVAL '30 days'
  AND d.total_quantity > 0
GROUP BY i.id, i.description, i.pcode
HAVING AVG(d.latest_price_cost) > AVG(d.total_price / NULLIF(d.total_quantity, 0))
ORDER BY qtd_vendida_30d DESC;
```

### Período da Páscoa

```sql
SET search_path TO prod_515383678;

-- Exemplo para Páscoa 2024 (28 Mar - 31 Mar)
SELECT
    s.name,
    SUM(d.total_net) as vendas_pascoa,
    SUM(d.nr_sales) as num_vendas,
    SUM(d.nr_persons) as num_clientes
FROM da_stores_date d
JOIN stores s ON s.id = d.store_id
WHERE d.date BETWEEN '2024-03-28' AND '2024-03-31'
GROUP BY s.name
ORDER BY vendas_pascoa DESC;
```

## Próximos Passos

### Objetivos do Ivo

1. **BI Queries** ✓
   - Vendas de hoje
   - Vendas por período (Páscoa, etc.)
   - Comparação YoY
   - Top artigos
   - Artigos com prejuízo

2. **AI Integration** (TODO)
   - Natural language to SQL (LLM)
   - Forecasting (time series)
   - Recommendations (pattern analysis)

### Desenvolvimento

```bash
# Criar ambiente Python para AI/ML
python3 -m venv venv
source venv/bin/activate
pip install pandas numpy scikit-learn openai psycopg2-binary

# Adicionar ferramentas de visualização
pip install plotly dash streamlit
```

## Estrutura do Projeto

```
storesace/
├── DUMP/                    # SQL dumps (100+ ficheiros)
├── docker-compose.yml       # PostgreSQL + pgAdmin
├── import_database.py       # Script de importação
├── README.md               # Este ficheiro
└── (futuros)
    ├── queries/            # SQL queries úteis
    ├── nlp/                # Natural language to SQL
    ├── forecast/           # Time series forecasting
    └── dashboard/          # Streamlit/Dash app
```

## Notas Técnicas

- **Particionamento**: Da_stores_date por ano, da_items_stores_date por mês
- **Encoding**: UTF-8
- **Timezone**: Europe/Lisbon (stores) e America/Sao_Paulo (loja inativa)
- **Schema**: Django ORM original (prod_515383678)

## Manutenção

### Backup

```bash
docker exec storesace_db pg_dump -U storesace -d storesace -F c -f /tmp/backup.dump
docker cp storesace_db:/tmp/backup.dump ./backup-$(date +%Y%m%d).dump
```

### Reset Database

```bash
docker compose down -v  # Remove volumes
docker compose up -d
./import_database.py    # Re-import
```

## Suporte

Problemas com importação:
1. Verificar logs: `docker compose logs postgres`
2. Verificar conexão: `docker exec storesace_db pg_isready`
3. Re-importar tabela específica (editar import_database.py)
