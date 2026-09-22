-- 10+ SQL Exploratory Queries covering data completeness and distributions

-- Q1: Total Company Count
SELECT COUNT(*) AS total_companies FROM companies;

-- Q2: Company Count by Broad Sector
SELECT s.broad_sector, COUNT(*) AS num_companies, ROUND(SUM(s.index_weight_pct), 2) AS total_weight_pct
FROM sectors s
GROUP BY s.broad_sector
ORDER BY num_companies DESC;

-- Q3: Annual History Span per Company (Min, Max, Total Years)
SELECT p.company_id, MIN(p.year) AS earliest_year, MAX(p.year) AS latest_year, COUNT(p.year) AS num_years
FROM profitandloss p
GROUP BY p.company_id
ORDER BY num_years DESC, p.company_id ASC;

-- Q4: Companies with Less than 10 Years Coverage
SELECT company_id, COUNT(*) AS year_count
FROM profitandloss
GROUP BY company_id
HAVING year_count < 10;

-- Q5: Top 10 Revenue Generators (Latest Year)
SELECT p.company_id, c.company_name, s.broad_sector, p.sales AS sales_cr, p.net_profit AS net_profit_cr
FROM profitandloss p
JOIN companies c ON p.company_id = c.id
JOIN sectors s ON c.id = s.company_id
WHERE p.year = (SELECT MAX(year) FROM profitandloss)
ORDER BY p.sales DESC
LIMIT 10;

-- Q6: Top 10 Net Profit Margins (Latest Year, Sales > 1000 Cr)
SELECT p.company_id, c.company_name, p.sales, p.net_profit, ROUND((p.net_profit / p.sales) * 100, 2) AS npm_pct
FROM profitandloss p
JOIN companies c ON p.company_id = c.id
WHERE p.year = (SELECT MAX(year) FROM profitandloss) AND p.sales > 1000
ORDER BY npm_pct DESC
LIMIT 10;

-- Q7: Debt-Free Companies (Borrowings = 0 in Latest Year)
SELECT b.company_id, c.company_name, b.borrowings, (b.equity_capital + b.reserves) AS total_equity
FROM balancesheet b
JOIN companies c ON b.company_id = c.id
WHERE b.year = (SELECT MAX(year) FROM balancesheet) AND (b.borrowings = 0 OR b.borrowings IS NULL)
ORDER BY total_equity DESC;

-- Q8: Cash Flow Positive Companies (CFO > 0 for 5 Consecutive Years)
SELECT company_id, COUNT(*) AS positive_cfo_years
FROM cashflow
WHERE operating_activity > 0 AND year >= '2020-03'
GROUP BY company_id
HAVING positive_cfo_years >= 5
ORDER BY positive_cfo_years DESC;

-- Q9: Annual Reports Document Count per Company
SELECT d.company_id, COUNT(d.annual_report) AS report_count, MIN(d.year) AS first_doc_yr, MAX(d.year) AS last_doc_yr
FROM documents d
GROUP BY d.company_id
ORDER BY report_count DESC;

-- Q10: Peer Group Distribution and Benchmark Companies
SELECT peer_group_name, COUNT(company_id) AS total_members,
       MAX(CASE WHEN is_benchmark = 1 THEN company_id ELSE NULL END) AS benchmark_company
FROM peer_groups
GROUP BY peer_group_name;

-- Q11: Foreign Key Integrity Check (Should Return 0 rows)
PRAGMA foreign_key_check;
