-- StoreSace Business Intelligence Queries
-- Responde às perguntas do Ivo Marinho

SET search_path TO prod_515383678;

-- ============================================
-- 1. Quanto vendi hoje?
-- ============================================
SELECT
    s.name AS loja,
    d.date AS data,
    d.nr_sales AS num_vendas,
    d.nr_persons AS num_clientes,
    d.total_quantity AS quantidade_total,
    d.total_net AS vendas_sem_iva,
    d.total_doc AS vendas_com_iva,
    d.total_discount AS descontos
FROM da_stores_date d
JOIN stores s ON s.id = d.store_id
WHERE d.date = CURRENT_DATE
  AND s.status = 1  -- Apenas lojas ativas
ORDER BY d.total_net DESC;

-- ============================================
-- 2. Quanto vendi na Páscoa deste ano?
-- ============================================
-- Nota: Páscoa 2025 = 20 Abril (6ª feira antes é 18 Abr)
-- Período: 18-20 Abril 2025
SELECT
    'Páscoa 2025 (18-20 Abr)' AS periodo,
    COUNT(DISTINCT d.date) AS dias,
    SUM(d.nr_sales) AS total_vendas,
    SUM(d.nr_persons) AS total_clientes,
    SUM(d.total_quantity) AS quantidade_total,
    SUM(d.total_net) AS vendas_sem_iva,
    SUM(d.total_doc) AS vendas_com_iva,
    ROUND(AVG(d.total_net), 2) AS media_diaria
FROM da_stores_date d
JOIN stores s ON s.id = d.store_id
WHERE d.date BETWEEN '2025-04-18' AND '2025-04-20'
  AND s.status = 1;

-- Por loja
SELECT
    s.name AS loja,
    SUM(d.total_net) AS vendas_pascoa_2025,
    SUM(d.nr_sales) AS num_vendas,
    ROUND(SUM(d.total_net) / NULLIF(SUM(d.nr_sales), 0), 2) AS ticket_medio
FROM da_stores_date d
JOIN stores s ON s.id = d.store_id
WHERE d.date BETWEEN '2025-04-18' AND '2025-04-20'
  AND s.status = 1
GROUP BY s.name
ORDER BY vendas_pascoa_2025 DESC;

-- ============================================
-- 3. Quanto vendi na Loja X?
-- ============================================
-- Exemplo: Loja - Braga (últimos 30 dias)
SELECT
    s.name AS loja,
    d.date AS data,
    d.nr_sales AS vendas,
    d.nr_persons AS clientes,
    d.total_net AS receita,
    d.total_discount AS descontos
FROM da_stores_date d
JOIN stores s ON s.id = d.store_id
WHERE s.name = 'Loja - Braga'
  AND d.date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY d.date DESC;

-- Total por loja (ano corrente)
SELECT
    s.name AS loja,
    COUNT(*) AS dias_operacao,
    SUM(d.nr_sales) AS total_vendas,
    SUM(d.nr_persons) AS total_clientes,
    SUM(d.total_net) AS receita_total,
    ROUND(AVG(d.total_net), 2) AS media_diaria,
    ROUND(SUM(d.total_net) / NULLIF(SUM(d.nr_sales), 0), 2) AS ticket_medio
FROM da_stores_date d
JOIN stores s ON s.id = d.store_id
WHERE EXTRACT(YEAR FROM d.date) = EXTRACT(YEAR FROM CURRENT_DATE)
  AND s.status = 1
GROUP BY s.name
ORDER BY receita_total DESC;

-- ============================================
-- 4. Como está a minha evolução face ao ano anterior?
-- ============================================
WITH vendas_comparacao AS (
    SELECT
        s.id AS store_id,
        s.name AS loja,
        EXTRACT(YEAR FROM d.date) AS ano,
        EXTRACT(MONTH FROM d.date) AS mes,
        SUM(d.total_net) AS vendas_mes
    FROM da_stores_date d
    JOIN stores s ON s.id = d.store_id
    WHERE d.date >= (CURRENT_DATE - INTERVAL '2 years')
      AND s.status = 1
    GROUP BY s.id, s.name, EXTRACT(YEAR FROM d.date), EXTRACT(MONTH FROM d.date)
)
SELECT
    loja,
    mes,
    SUM(CASE WHEN ano = EXTRACT(YEAR FROM CURRENT_DATE) THEN vendas_mes ELSE 0 END) AS vendas_2025,
    SUM(CASE WHEN ano = EXTRACT(YEAR FROM CURRENT_DATE) - 1 THEN vendas_mes ELSE 0 END) AS vendas_2024,
    ROUND(
        (SUM(CASE WHEN ano = EXTRACT(YEAR FROM CURRENT_DATE) THEN vendas_mes ELSE 0 END) -
         SUM(CASE WHEN ano = EXTRACT(YEAR FROM CURRENT_DATE) - 1 THEN vendas_mes ELSE 0 END)),
        2
    ) AS diferenca,
    ROUND(
        (SUM(CASE WHEN ano = EXTRACT(YEAR FROM CURRENT_DATE) THEN vendas_mes ELSE 0 END) -
         SUM(CASE WHEN ano = EXTRACT(YEAR FROM CURRENT_DATE) - 1 THEN vendas_mes ELSE 0 END)) /
        NULLIF(SUM(CASE WHEN ano = EXTRACT(YEAR FROM CURRENT_DATE) - 1 THEN vendas_mes ELSE 0 END), 0) * 100,
        2
    ) AS variacao_pct
FROM vendas_comparacao
WHERE mes <= EXTRACT(MONTH FROM CURRENT_DATE)
GROUP BY loja, mes
ORDER BY loja, mes;

-- Resumo anual
SELECT
    s.name AS loja,
    EXTRACT(YEAR FROM d.date) AS ano,
    SUM(d.total_net) AS vendas_anuais,
    SUM(d.nr_sales) AS num_vendas,
    SUM(d.nr_persons) AS num_clientes,
    ROUND(AVG(d.total_net), 2) AS media_diaria
FROM da_stores_date d
JOIN stores s ON s.id = d.store_id
WHERE d.date >= (CURRENT_DATE - INTERVAL '5 years')
  AND s.status = 1
GROUP BY s.name, EXTRACT(YEAR FROM d.date)
ORDER BY s.name, ano;

-- ============================================
-- 5. Qual o meu melhor artigo?
-- ============================================
-- Por receita (últimos 30 dias)
SELECT
    i.description AS artigo,
    i.pcode AS codigo,
    SUM(d.total_quantity) AS qtd_vendida,
    SUM(d.total_net) AS receita_total,
    SUM(d.total_price) AS preco_total,
    ROUND(AVG(d.latest_price_cost), 2) AS custo_medio,
    ROUND(SUM(d.total_net - (d.total_quantity * d.latest_price_cost)), 2) AS margem_total,
    ROUND(
        (SUM(d.total_net - (d.total_quantity * d.latest_price_cost)) /
         NULLIF(SUM(d.total_net), 0)) * 100,
        2
    ) AS margem_pct
FROM da_items_stores_date d
JOIN items i ON i.id = d.item_id
WHERE d.date >= (SELECT MAX(date) - INTERVAL '30 days' FROM da_items_stores_date)
GROUP BY i.id, i.description, i.pcode
ORDER BY receita_total DESC
LIMIT 20;

-- Por margem
SELECT
    i.description AS artigo,
    i.pcode AS codigo,
    SUM(d.total_quantity) AS qtd_vendida,
    SUM(d.total_net) AS receita_total,
    ROUND(SUM(d.total_net - (d.total_quantity * d.latest_price_cost)), 2) AS margem_total,
    ROUND(
        (SUM(d.total_net - (d.total_quantity * d.latest_price_cost)) /
         NULLIF(SUM(d.total_net), 0)) * 100,
        2
    ) AS margem_pct
FROM da_items_stores_date d
JOIN items i ON i.id = d.item_id
WHERE d.date >= (SELECT MAX(date) - INTERVAL '30 days' FROM da_items_stores_date)
  AND d.total_quantity > 0
GROUP BY i.id, i.description, i.pcode
HAVING SUM(d.total_quantity) > 10  -- Mínimo 10 unidades vendidas
ORDER BY margem_total DESC
LIMIT 20;

-- Por quantidade
SELECT
    i.description AS artigo,
    i.pcode AS codigo,
    SUM(d.total_quantity) AS qtd_vendida,
    SUM(d.total_net) AS receita_total,
    ROUND(AVG(d.total_net / NULLIF(d.total_quantity, 0)), 2) AS preco_medio,
    COUNT(DISTINCT d.store_id) AS lojas_que_venderam
FROM da_items_stores_date d
JOIN items i ON i.id = d.item_id
WHERE d.date >= (SELECT MAX(date) - INTERVAL '30 days' FROM da_items_stores_date)
  AND d.total_quantity > 0
GROUP BY i.id, i.description, i.pcode
ORDER BY qtd_vendida DESC
LIMIT 20;

-- ============================================
-- 6. Tenho artigos a perder dinheiro?
-- ============================================
-- Artigos onde custo > preço de venda (sem IVA)
SELECT
    i.description AS artigo,
    i.pcode AS codigo,
    COUNT(*) AS ocorrencias,
    SUM(d.total_quantity) AS qtd_vendida,
    ROUND(AVG(d.latest_price_cost), 4) AS custo_medio,
    ROUND(AVG(d.total_price / NULLIF(d.total_quantity, 0)), 4) AS preco_venda_medio,
    ROUND(
        AVG(d.total_price / NULLIF(d.total_quantity, 0)) - AVG(d.latest_price_cost),
        4
    ) AS margem_unitaria,
    ROUND(
        SUM(d.total_net - (d.total_quantity * d.latest_price_cost)),
        2
    ) AS prejuizo_total
FROM da_items_stores_date d
JOIN items i ON i.id = d.item_id
WHERE d.date >= (SELECT MAX(date) - INTERVAL '30 days' FROM da_items_stores_date)
  AND d.total_quantity > 0
  AND d.latest_price_cost > 0
GROUP BY i.id, i.description, i.pcode
HAVING AVG(d.latest_price_cost) > AVG(d.total_price / NULLIF(d.total_quantity, 0))
ORDER BY prejuizo_total ASC;

-- Artigos com margens negativas ou muito baixas
SELECT
    i.description AS artigo,
    i.pcode AS codigo,
    SUM(d.total_quantity) AS qtd_vendida,
    SUM(d.total_net) AS receita,
    SUM(d.total_quantity * d.latest_price_cost) AS custo_total,
    ROUND(SUM(d.total_net - (d.total_quantity * d.latest_price_cost)), 2) AS margem_total,
    ROUND(
        (SUM(d.total_net - (d.total_quantity * d.latest_price_cost)) /
         NULLIF(SUM(d.total_net), 0)) * 100,
        2
    ) AS margem_pct
FROM da_items_stores_date d
JOIN items i ON i.id = d.item_id
WHERE d.date >= (SELECT MAX(date) - INTERVAL '30 days' FROM da_items_stores_date)
  AND d.total_quantity > 0
GROUP BY i.id, i.description, i.pcode
HAVING (SUM(d.total_net - (d.total_quantity * d.latest_price_cost)) /
        NULLIF(SUM(d.total_net), 0)) < 0.1  -- Margem < 10%
ORDER BY margem_pct ASC;

-- ============================================
-- EXTRAS: Análises Adicionais
-- ============================================

-- Top lojas por performance
SELECT
    s.name AS loja,
    COUNT(DISTINCT d.date) AS dias_operacao,
    SUM(d.total_net) AS receita_total,
    ROUND(AVG(d.total_net), 2) AS receita_media_dia,
    SUM(d.nr_sales) AS total_vendas,
    ROUND(SUM(d.total_net) / NULLIF(SUM(d.nr_sales), 0), 2) AS ticket_medio,
    SUM(d.nr_persons) AS total_clientes,
    ROUND(SUM(d.nr_sales)::NUMERIC / NULLIF(SUM(d.nr_persons), 0), 2) AS vendas_por_cliente
FROM da_stores_date d
JOIN stores s ON s.id = d.store_id
WHERE d.date >= CURRENT_DATE - INTERVAL '30 days'
  AND s.status = 1
GROUP BY s.name
ORDER BY receita_total DESC;

-- Tendência de vendas (últimas 12 semanas)
SELECT
    DATE_TRUNC('week', d.date) AS semana,
    COUNT(DISTINCT s.id) AS lojas_ativas,
    SUM(d.nr_sales) AS total_vendas,
    SUM(d.nr_persons) AS total_clientes,
    SUM(d.total_net) AS receita_total,
    ROUND(AVG(d.total_net), 2) AS media_diaria
FROM da_stores_date d
JOIN stores s ON s.id = d.store_id
WHERE d.date >= CURRENT_DATE - INTERVAL '12 weeks'
  AND s.status = 1
GROUP BY DATE_TRUNC('week', d.date)
ORDER BY semana DESC;

-- Dias da semana (performance)
SELECT
    TO_CHAR(d.date, 'Day') AS dia_semana,
    EXTRACT(DOW FROM d.date) AS dia_num,
    COUNT(*) AS ocorrencias,
    SUM(d.total_net) AS receita_total,
    ROUND(AVG(d.total_net), 2) AS receita_media,
    SUM(d.nr_sales) AS total_vendas,
    SUM(d.nr_persons) AS total_clientes
FROM da_stores_date d
JOIN stores s ON s.id = d.store_id
WHERE d.date >= CURRENT_DATE - INTERVAL '90 days'
  AND s.status = 1
GROUP BY TO_CHAR(d.date, 'Day'), EXTRACT(DOW FROM d.date)
ORDER BY dia_num;
