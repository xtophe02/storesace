# StoreSace - AI-Powered Retail Analytics Platform

**Cliente:** Ivo Marinho
**Stack:** PostgreSQL + Python + AI/ML
**Objetivo:** Transformar dados de vendas em insights acionáveis usando AI

---

## 📋 Visão Geral

Sistema de análise inteligente para rede de retalho portuguesa (9 lojas, ~30k produtos, 5+ anos de dados históricos). O objetivo é substituir queries SQL manuais por perguntas em linguagem natural e fornecer previsões automáticas.

### Dados Disponíveis
- **Period:** Agosto 2020 → Dezembro 2025
- **Lojas:** Braga, Fafe, Quintã, Silvares-Guimarães, Matosinhos, S. Francisco, Online
- **Produtos:** 29,929 artigos ativos
- **Transações:** ~8,870 dias × 7 lojas = 62k+ registos diários
- **Granularidade:** Vendas diárias por loja + vendas diárias por produto/loja

### Métricas Disponíveis
- Receita (com/sem IVA)
- Quantidade vendida
- Número de vendas e clientes
- Custos e margens
- Descontos e devoluções
- Quebras e desperdícios

---

## 🎯 Objetivos do Projeto

### Business Goals (Ivo)
1. **Queries em Linguagem Natural**
   - "Quanto vendi hoje?"
   - "Como está a Páscoa vs ano passado?"
   - "Quais os meus artigos problemáticos?"

2. **Análise de Performance**
   - Comparações YoY automáticas
   - Top artigos (receita/margem/volume)
   - Artigos a perder dinheiro
   - Performance por loja

3. **Forecasting**
   - Previsões mensais de vendas
   - Identificar sazonalidade
   - Alertas automáticos (tendências negativas)

4. **Recomendações AI**
   - Otimização de stock
   - Preços dinâmicos
   - Promoções sugeridas
   - Ações corretivas

### Technical Goals
- ✅ PostgreSQL em Docker (portável)
- ✅ Import automatizado de dados
- ✅ Queries BI documentadas
- 🔲 NL2SQL (natural language to SQL)
- 🔲 Time series forecasting
- 🔲 Dashboard interativo
- 🔲 API REST para integração

---

## 📊 Estado Atual

### ✅ Completado (Fase 0)
- Docker Compose com PostgreSQL 16
- Schema criado (prod_515383678)
- Import de master data (stores, items)
- Import parcial de fact tables (3/85 partições)
- Queries BI para todas as perguntas do Ivo
- Documentação básica (README.md)

### 📈 Dados Importados
```
Stores:              9 lojas
Items:          29,929 artigos
da_stores_date:  8,870 registos (2020-2025) ✅
da_items_stores: 90,666 registos (até Out/2020) ⚠️ PARCIAL
```

### ⚠️ Limitações Atuais
- Apenas 3 meses de dados granulares (item-level)
- Sem AI/ML integration
- Queries manuais (SQL direto)
- Sem visualizações

---

## 🚀 Roadmap por Fases

### **Fase 1: Foundation (Data Complete)**
**Tempo:** 1-2 horas
**Prioridade:** ALTA

#### Objetivos
- Completar import de todas as partições (85 total)
- Verificar integridade dos dados
- Criar índices para performance
- Backup completo

#### Deliverables
- [ ] Import de 82 partições restantes de `da_items_stores_date`
- [ ] Validação: MIN/MAX dates, COUNT por ano, gaps
- [ ] Índices otimizados (store_id, item_id, date)
- [ ] Script de backup automático
- [ ] Documentação de estrutura de dados

#### SQL Validation Queries
```sql
-- Verificar coverage temporal
SELECT
    EXTRACT(YEAR FROM date) as ano,
    EXTRACT(MONTH FROM date) as mes,
    COUNT(*) as registos
FROM da_items_stores_date
GROUP BY ano, mes
ORDER BY ano, mes;

-- Identificar gaps
SELECT date::date
FROM generate_series(
    (SELECT MIN(date) FROM da_items_stores_date),
    (SELECT MAX(date) FROM da_items_stores_date),
    '1 day'::interval
) date
WHERE date NOT IN (SELECT DISTINCT date FROM da_items_stores_date);
```

#### Success Criteria
- ✅ Dados de 2020-08 até 2025-12 completos
- ✅ Zero gaps em dias úteis
- ✅ Performance: queries < 2s

---

### **Fase 2: Natural Language Queries (NL2SQL)**
**Tempo:** 4-6 horas
**Prioridade:** ALTA

#### Objetivos
- Transformar perguntas PT/EN em SQL
- Usar Claude API (Sonnet 4.5) ou local LLM
- Validar queries antes de executar
- Cache de queries frequentes

#### Arquitetura
```
User Input → LLM (NL2SQL) → SQL Validator → PostgreSQL → Format Results → User
                ↓
            Query Cache
```

#### Tecnologias
- **LLM:** Claude API (via SDK) ou Ollama local (llama3.1)
- **Validation:** sqlparse + dry-run
- **Cache:** Redis ou SQLite
- **Framework:** Python FastAPI ou Flask

#### Exemplos de Input/Output

| Input (PT)                          | SQL Gerado                                    |
|-------------------------------------|-----------------------------------------------|
| "Quanto vendi hoje?"                | `SELECT SUM(total_net) FROM da_stores_date WHERE date = CURRENT_DATE` |
| "Top 10 artigos de Novembro"       | `SELECT i.description, SUM(d.total_net) FROM da_items_stores_date d JOIN items i...` |
| "Lojas com mais de 1000€/dia"      | `SELECT s.name, AVG(d.total_net) FROM da_stores_date d JOIN stores s...` |

#### Deliverables
- [ ] `nl2sql.py` - Core engine
- [ ] Schema documentation for LLM context
- [ ] 50+ test cases (perguntas → SQL esperado)
- [ ] CLI tool: `./ask.py "Quanto vendi hoje?"`
- [ ] API endpoint: `POST /query` com JSON response

#### Challenges
- **Contexto de datas:** "Páscoa 2025" → calcular data automaticamente
- **Ambiguidade:** "melhor artigo" = receita? margem? volume?
- **Joins:** LLM precisa conhecer relacionamentos (items ↔ da_items_stores_date)
- **Performance:** Queries complexas podem ser lentas

#### Prompt Engineering Example
```python
SYSTEM_PROMPT = """
You are a SQL expert for a Portuguese retail database.

Schema:
- stores: id, name, code
- items: id, description, pcode (product code)
- da_stores_date: store_id, date, total_net, nr_sales, nr_persons
- da_items_stores_date: item_id, store_id, date, total_quantity, total_net, latest_price_cost

Rules:
- Always SET search_path TO prod_515383678;
- Dates in format 'YYYY-MM-DD'
- "Hoje" = CURRENT_DATE
- "Páscoa 2025" = '2025-04-18' to '2025-04-20'
- Join stores using stores.id = da_stores_date.store_id
- Only SELECT, no DELETE/UPDATE/DROP

User question: {question}
Generate only the SQL query, no explanations.
"""
```

---

### **Fase 3: Time Series Forecasting**
**Tempo:** 6-8 horas
**Prioridade:** MÉDIA

#### Objetivos
- Previsões mensais de vendas por loja
- Identificar sazonalidade (Páscoa, Natal, Verão)
- Alertas automáticos (quedas > 15%)
- Confidence intervals

#### Modelos a Testar
1. **Prophet (Meta)** - Recomendado para retail
   - Handles sazonalidade múltipla
   - Holidays automáticos (Portugal)
   - Robust a missing data

2. **ARIMA/SARIMA** - Clássico
   - Melhor para séries estacionárias
   - Requer mais tuning

3. **XGBoost** - ML approach
   - Features: dia da semana, mês, feriados, promoções
   - Bom para capturar padrões não-lineares

#### Features Engineering
```python
# Temporal features
- day_of_week (0-6)
- month (1-12)
- quarter (1-4)
- is_weekend
- is_holiday (Portugal calendar)
- week_of_year
- days_to_easter
- days_to_christmas

# Lag features
- sales_lag_7 (venda 7 dias atrás)
- sales_lag_30
- sales_lag_365 (mesmo dia ano passado)
- rolling_mean_7
- rolling_mean_30

# External
- weather (se disponível)
- local events
```

#### Deliverables
- [ ] `forecast.py` - Training + prediction pipeline
- [ ] Models comparison (Prophet vs ARIMA vs XGBoost)
- [ ] Visualizações: actual vs predicted
- [ ] API endpoint: `GET /forecast/loja/2026-01`
- [ ] Alertas automáticos (email/webhook)

#### Success Metrics
- MAPE < 15% (Mean Absolute Percentage Error)
- Previsões 1-3 meses à frente
- Atualização automática mensal

---

### **Fase 4: Dashboard Interativo**
**Tempo:** 8-12 horas
**Prioridade:** MÉDIA

#### Objetivos
- Visualizações interativas
- Filtros (loja, período, produto)
- Exportação (PDF, Excel)
- Mobile-friendly

#### Tech Stack Options

**Opção A: Streamlit (Recomendado)**
- ✅ Rápido desenvolvimento
- ✅ Python-native
- ✅ Deploy fácil (Docker)
- ❌ Menos customizável

**Opção B: Dash (Plotly)**
- ✅ Mais customizável
- ✅ Production-ready
- ❌ Curva de aprendizagem

**Opção C: Next.js + Recharts**
- ✅ Performance máxima
- ✅ Design moderno
- ❌ Mais tempo de dev

#### Dashboard Sections

1. **Overview**
   - KPIs: vendas hoje, MTD, YTD
   - Comparação YoY
   - Top 5 lojas

2. **Sales Analysis**
   - Gráfico temporal (daily/weekly/monthly)
   - Breakdown por loja
   - Heatmap (dia da semana × hora)

3. **Product Analysis**
   - Top produtos (receita/margem/volume)
   - Artigos com prejuízo
   - Margens por categoria

4. **Forecasting**
   - Previsões próximos 3 meses
   - Confidence intervals
   - Comparação com ano anterior

5. **NL Query**
   - Text input: "Quanto vendi na Páscoa?"
   - Results table + visualização automática

#### Deliverables
- [ ] `dashboard/app.py` - Streamlit app
- [ ] 5 páginas principais
- [ ] Autenticação básica (opcional)
- [ ] Docker image para deploy
- [ ] Deploy em servidor (192.168.0.160)

---

### **Fase 5: AI Recommendations**
**Tempo:** 12-16 horas
**Prioridade:** BAIXA (Future)

#### Objetivos
- Insights automáticos
- Recomendações acionáveis
- Pattern detection

#### Use Cases

1. **Stock Optimization**
   - Produtos a encomendar (previsão de ruptura)
   - Produtos parados (> 90 dias sem venda)
   - Sugestão de transferências entre lojas

2. **Pricing**
   - Artigos com margem < 10% → aumentar preço
   - Produtos com baixa rotação → promoção
   - Price elasticity analysis

3. **Anomaly Detection**
   - Quedas súbitas (> 30%)
   - Picos inexplicados
   - Padrões incomuns

4. **Marketing**
   - Melhor dia para promoções
   - Cross-sell opportunities
   - Customer segmentation (se tiver dados)

#### LLM Agent Architecture
```
Data → Pattern Detection → LLM Analysis → Recommendations → Action Items
                ↓
          Knowledge Base
       (historical patterns)
```

#### Deliverables
- [ ] `recommendations.py` - Recommendation engine
- [ ] Weekly report automático (email)
- [ ] Dashboard tab "Insights"
- [ ] Action tracking (implementado? resultado?)

---

## 🏗️ Arquitetura Técnica Final

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface                        │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Streamlit   │  │ REST API     │  │ CLI Tools     │  │
│  │ Dashboard   │  │ (FastAPI)    │  │ (./ask.py)    │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬───────┘  │
└─────────┼─────────────────┼──────────────────┼──────────┘
          │                 │                  │
          └─────────────────┴──────────────────┘
                            │
          ┌─────────────────▼────────────────────┐
          │       Application Layer              │
          │  ┌──────────┐  ┌──────────────────┐ │
          │  │ NL2SQL   │  │ Forecast Engine  │ │
          │  │ (Claude) │  │ (Prophet/ARIMA)  │ │
          │  └────┬─────┘  └────┬─────────────┘ │
          │       │             │                │
          │  ┌────▼─────────────▼─────────────┐ │
          │  │   Query Builder & Validator    │ │
          │  └────┬───────────────────────────┘ │
          └───────┼──────────────────────────────┘
                  │
          ┌───────▼──────────────────────────────┐
          │         Data Layer                   │
          │  ┌──────────┐      ┌──────────────┐ │
          │  │PostgreSQL│      │ Redis Cache  │ │
          │  │(Docker)  │      │ (optional)   │ │
          │  └──────────┘      └──────────────┘ │
          └──────────────────────────────────────┘
```

---

## 🛠️ Tech Stack Detalhado

### Backend
- **Python 3.12+**
  - pandas, numpy (data manipulation)
  - psycopg2 (PostgreSQL driver)
  - anthropic SDK (Claude API)
  - prophet / statsmodels (forecasting)
  - fastapi (REST API)
  - sqlparse (SQL validation)

### Database
- **PostgreSQL 16** (Docker)
- **pgAdmin 4** (optional, para debugging)

### AI/ML
- **Claude Sonnet 4.5** (NL2SQL)
- **Prophet** (forecasting - primary)
- **XGBoost** (forecasting - alternative)

### Frontend
- **Streamlit** (dashboard rápido)
- **Plotly/Altair** (visualizações)
- **Pandas** (data prep)

### DevOps
- **Docker + Docker Compose**
- **Git** (version control)
- **GitHub Actions** (CI/CD - future)

---

## 📦 Estrutura de Ficheiros

```
storesace/
├── README.md                  # User documentation
├── PROJECT.md                 # This file - strategic planning
├── docker-compose.yml         # PostgreSQL + services
├── .env.example               # Environment variables template
│
├── DUMP/                      # SQL dumps (85+ files)
│   ├── items.sql
│   ├── stores.sql
│   └── da_*.sql
│
├── scripts/
│   ├── import_database.py     # Initial data import
│   ├── query.sh               # Quick query helper
│   └── backup.sh              # Backup automation
│
├── sql/
│   ├── schema.sql             # Database schema
│   ├── indexes.sql            # Performance indexes
│   └── queries_bi.sql         # Business intelligence queries
│
├── src/
│   ├── nl2sql/
│   │   ├── engine.py          # NL to SQL converter
│   │   ├── validator.py       # Query validation
│   │   ├── cache.py           # Query caching
│   │   └── prompts.py         # LLM prompts
│   │
│   ├── forecast/
│   │   ├── prophet_model.py   # Prophet forecasting
│   │   ├── arima_model.py     # ARIMA forecasting
│   │   ├── features.py        # Feature engineering
│   │   └── evaluate.py        # Model evaluation
│   │
│   ├── api/
│   │   ├── main.py            # FastAPI app
│   │   ├── routes/
│   │   │   ├── query.py       # NL query endpoint
│   │   │   └── forecast.py    # Forecast endpoint
│   │   └── models.py          # Pydantic models
│   │
│   ├── dashboard/
│   │   ├── app.py             # Streamlit main
│   │   ├── pages/
│   │   │   ├── overview.py
│   │   │   ├── sales.py
│   │   │   ├── products.py
│   │   │   └── forecast.py
│   │   └── components/
│   │       ├── charts.py
│   │       └── filters.py
│   │
│   └── utils/
│       ├── db.py              # Database connection
│       ├── logger.py          # Logging
│       └── config.py          # Configuration
│
├── tests/
│   ├── test_nl2sql.py
│   ├── test_forecast.py
│   └── test_api.py
│
├── notebooks/
│   ├── exploration.ipynb      # Data exploration
│   ├── forecasting_poc.ipynb  # Forecast experiments
│   └── nl2sql_tests.ipynb     # NL2SQL testing
│
└── docs/
    ├── API.md                 # API documentation
    ├── QUERIES.md             # Query examples
    └── DEPLOYMENT.md          # Deployment guide
```

---

## 🎯 Success Metrics

### Business Metrics
- **Adoption:** Ivo usa o sistema 3+ vezes/semana
- **Time Saving:** Redução de 80% no tempo para obter insights
- **Accuracy:** Forecasts com erro < 15%
- **Coverage:** 100% das perguntas iniciais respondidas

### Technical Metrics
- **Performance:** Queries < 2s (p95)
- **Uptime:** 99%+ (após deploy)
- **Data Freshness:** Dados atualizados diariamente
- **Test Coverage:** 80%+ (critical paths)

---

## ⚠️ Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Import de dados incompleto | Baixa | Alto | Validação automática + testes |
| Claude API costs | Média | Médio | Cache agressivo + fallback local LLM |
| Forecasting impreciso | Média | Médio | Ensemble models + human validation |
| User adoption baixa | Média | Alto | UI intuitiva + training/docs |
| Performance PostgreSQL | Baixa | Médio | Índices + partitioning (já feito) |

---

## 💰 Custos Estimados

### Desenvolvimento
- **Tempo total:** 30-40 horas
- **Custo (se consultoria):** €1,500 - €2,000 @ €50/hora

### Infraestrutura (Mensal)
- **Claude API:** ~€10-20 (com caching)
- **Servidor local:** €0 (já tens RTX 3060)
- **Domain/SSL (opcional):** €5

### Alternativa Local (Zero Cost)
- **Ollama + Llama 3.1** (local LLM)
- **PostgreSQL** (Docker local)
- **Total:** €0/mês

---

## 📅 Timeline Sugerido

### Sprint 1 (Semana 1) - Foundation
- Dia 1-2: Completar import de dados
- Dia 3: Otimização (índices, validação)
- Dia 4: Documentação técnica
- Dia 5: Backup e testes

### Sprint 2 (Semana 2) - NL2SQL
- Dia 1-2: Engine NL2SQL + Claude integration
- Dia 3: Validação e testes
- Dia 4: CLI tool + basic API
- Dia 5: Refinamento prompts

### Sprint 3 (Semana 3) - Forecasting
- Dia 1-2: Prophet model + training
- Dia 3: ARIMA comparison
- Dia 4: Visualizações + API
- Dia 5: Alertas automáticos

### Sprint 4 (Semana 4) - Dashboard
- Dia 1-3: Streamlit app (5 páginas)
- Dia 4: Integração NL2SQL + Forecast
- Dia 5: Deploy + documentação

---

## 🚢 Deployment Strategy

### Desenvolvimento (Laptop)
```bash
docker compose up -d
python src/api/main.py
streamlit run src/dashboard/app.py
```

### Produção (Servidor 192.168.0.160)
```bash
# Copy via SSH
scp -r storesace/ chris@192.168.0.160:~/apps/

# SSH into server
ssh chris@192.168.0.160

# Deploy
cd ~/apps/storesace
docker compose -f docker-compose.prod.yml up -d

# Access
# Dashboard: http://192.168.0.160:8501
# API: http://192.168.0.160:8000
```

### GPU Passthrough (para local LLM)
```yaml
# docker-compose.prod.yml
services:
  ollama:
    image: ollama/ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

---

## 📚 Resources & Learning

### Forecasting
- [Prophet Documentation](https://facebook.github.io/prophet/)
- [Time Series Forecasting with Python](https://www.manning.com/books/time-series-forecasting-in-python-book)

### NL2SQL
- [Text-to-SQL with LLMs](https://arxiv.org/abs/2204.00498)
- [Anthropic Prompt Engineering](https://docs.anthropic.com/claude/docs/prompt-engineering)

### PostgreSQL Performance
- [Use The Index, Luke](https://use-the-index-luke.com/)
- [PostgreSQL Query Performance Insights](https://www.postgresql.org/docs/current/performance-tips.html)

---

## 🤝 Próximos Passos

### Imediato (Esta Sessão)
1. ✅ Brainstorming completo
2. ⏳ Decidir prioridades (Fase 1 vs Fase 2 first?)
3. ⏳ Começar implementação da fase escolhida

### Esta Semana
- Completar Fase 1 (data import)
- POC de NL2SQL (Fase 2)
- Documentar learnings em MEMORY.md

### Próximo Mês
- Fase 2 completa (NL2SQL production-ready)
- Fase 3 POC (forecasting)
- Deploy em servidor

---

## 🎬 Conclusão

Este projeto tem potencial significativo:
- **Business Value:** Redução dramática no tempo para insights
- **Tech Value:** Portfolio piece (AI + Data + Cloud)
- **Learning:** Time series, LLM integration, production ML

**Next Decision Point:** Qual fase começar?
- **Opção A:** Fase 1 (completar dados) - sólido, sem riscos
- **Opção B:** Fase 2 (NL2SQL POC) - mais excitante, validação rápida
- **Opção C:** Híbrido - import básico + NL2SQL POC em paralelo

---

**Documento criado:** 2025-12-14
**Última atualização:** 2025-12-14
**Owner:** Christophe Moreira (xtophe02)
**Vasco Status:** Ready to navigate! ⛵
