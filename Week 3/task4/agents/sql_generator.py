from __future__ import annotations

import re

from config import Config
from agents.llm import call_llm_with_rotation
from prompts import CORRECTION_SYSTEM_PROMPT, GENERATOR_SYSTEM_PROMPT, SCHEMA_CONTEXT


class SQLGeneratorAgent:
    """Compiles natural language questions and plans into pure read-only PostgreSQL queries."""

    def generate(self, question: str, plan: str) -> str:
        if Config.has_llm_credentials():
            try:
                prompt = GENERATOR_SYSTEM_PROMPT.format(
                    schema_context=SCHEMA_CONTEXT,
                    plan=plan,
                    question=question,
                )
                raw_sql = call_llm_with_rotation(prompt, temperature=0.1)
                return self._clean_sql(raw_sql)
            except Exception:
                pass

        return self._heuristic_generate(question)

    def self_correct(self, question: str, plan: str, failed_sql: str, error_message: str) -> str:
        if Config.has_llm_credentials():
            try:
                prompt = CORRECTION_SYSTEM_PROMPT.format(
                    schema_context=SCHEMA_CONTEXT,
                    question=question,
                    plan=plan,
                    failed_sql=failed_sql,
                    error_message=error_message,
                )
                fixed_sql = call_llm_with_rotation(prompt, temperature=0.1)
                return self._clean_sql(fixed_sql)
            except Exception:
                pass

        return self._repair_with_rules(question, failed_sql, error_message)

    def _clean_sql(self, sql_string: str) -> str:
        if not sql_string:
            return ""

        cleaned = sql_string.strip()
        if cleaned.startswith("```sql"):
            cleaned = cleaned[6:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return cleaned.strip().rstrip(";") + ";"

    def _heuristic_generate(self, question: str) -> str:
        normalized = question.lower()

        if self._mentions_customers(normalized) and self._mentions_count(normalized):
            country = self._extract_country(normalized)
            where_clause = f' WHERE "country" = \'{country}\'' if country else ""
            return self._clean_sql(f'SELECT COUNT(*) AS customer_count FROM customers{where_clause}')

        if self._mentions_product_lines(normalized) and self._mentions_average(normalized):
            return self._clean_sql(
                'SELECT pl."productLine", ROUND(AVG(p."buyPrice"), 2) AS average_buy_price '
                'FROM products p '
                'JOIN productlines pl ON p."productLine" = pl."productLine" '
                'GROUP BY pl."productLine" '
                'ORDER BY average_buy_price DESC'
            )

        if self._mentions_products(normalized):
            if self._mentions_average(normalized):
                return self._clean_sql(
                    'SELECT pl."productLine", ROUND(AVG(p."buyPrice"), 2) AS average_buy_price '
                    'FROM products p '
                    'JOIN productlines pl ON p."productLine" = pl."productLine" '
                    'GROUP BY pl."productLine" '
                    'ORDER BY average_buy_price DESC'
                )
            if self._mentions_top(normalized):
                return self._clean_sql(
                    'SELECT p."productName", p."productLine", p."buyPrice", p."MSRP" '
                    'FROM products p '
                    'ORDER BY p."MSRP" DESC '
                    'LIMIT 10'
                )
            return self._clean_sql(
                'SELECT p."productCode", p."productName", p."productLine", p."buyPrice", p."MSRP", p."quantityInStock" '
                'FROM products p '
                'ORDER BY p."productName" '
                'LIMIT 50'
            )

        if self._mentions_payments(normalized):
            if self._mentions_sum(normalized) or self._mentions_total(normalized):
                return self._clean_sql(
                    'SELECT c."customerName", ROUND(SUM(pay."amount"), 2) AS total_payments '
                    'FROM payments pay '
                    'JOIN customers c ON pay."customerNumber" = c."customerNumber" '
                    'GROUP BY c."customerName" '
                    'ORDER BY total_payments DESC '
                    'LIMIT 10'
                )
            return self._clean_sql(
                'SELECT pay."customerNumber", pay."checkNumber", pay."paymentDate", pay."amount" '
                'FROM payments pay '
                'ORDER BY pay."paymentDate" DESC '
                'LIMIT 50'
            )

        if self._mentions_orders(normalized):
            if self._mentions_count(normalized):
                status = self._extract_status(normalized)
                where_clause = f' WHERE o."status" = \'{status}\'' if status else ""
                return self._clean_sql('SELECT COUNT(*) AS order_count FROM orders o' + where_clause)
            if self._mentions_customers(normalized):
                return self._clean_sql(
                    'SELECT o."orderNumber", o."orderDate", o."status", c."customerName" '
                    'FROM orders o '
                    'JOIN customers c ON o."customerNumber" = c."customerNumber" '
                    'ORDER BY o."orderDate" DESC '
                    'LIMIT 50'
                )
            return self._clean_sql(
                'SELECT o."orderNumber", o."orderDate", o."requiredDate", o."shippedDate", o."status" '
                'FROM orders o '
                'ORDER BY o."orderDate" DESC '
                'LIMIT 50'
            )

        if self._mentions_employees(normalized):
            return self._clean_sql(
                'SELECT e."employeeNumber", e."firstName", e."lastName", e."jobTitle", o."city", o."country" '
                'FROM employees e '
                'JOIN offices o ON e."officeCode" = o."officeCode" '
                'ORDER BY e."lastName", e."firstName"'
            )

        return self._clean_sql('SELECT p."productCode", p."productName", p."productLine", p."MSRP" FROM products p ORDER BY p."productName" LIMIT 20')

    def _repair_with_rules(self, question: str, failed_sql: str, error_message: str) -> str:
        if "does not exist" in error_message.lower() or "syntax error" in error_message.lower():
            return self._heuristic_generate(question)
        if not failed_sql.strip().lower().startswith(("select", "with")):
            return self._heuristic_generate(question)
        return self._clean_sql(failed_sql)

    def _mentions_customers(self, question: str) -> bool:
        return "customer" in question or "clients" in question

    def _mentions_orders(self, question: str) -> bool:
        return "order" in question

    def _mentions_products(self, question: str) -> bool:
        return any(token in question for token in ["product", "stock", "msrp", "buy price", "vendor"])

    def _mentions_product_lines(self, question: str) -> bool:
        return "product line" in question or "productline" in question or "product lines" in question

    def _mentions_payments(self, question: str) -> bool:
        return "payment" in question or "paid" in question or "revenue" in question or "amount" in question

    def _mentions_employees(self, question: str) -> bool:
        return "employee" in question or "sales rep" in question or "office" in question

    def _mentions_count(self, question: str) -> bool:
        return any(token in question for token in ["how many", "count", "number of"])

    def _mentions_average(self, question: str) -> bool:
        return any(token in question for token in ["average", "avg", "mean"])

    def _mentions_sum(self, question: str) -> bool:
        return any(token in question for token in ["sum", "total", "revenue"])

    def _mentions_total(self, question: str) -> bool:
        return "total" in question

    def _mentions_top(self, question: str) -> bool:
        return any(token in question for token in ["top", "highest", "largest", "most"])

    def _extract_country(self, question: str) -> str | None:
        match = re.search(r"from\s+([a-zA-Z\s]+)$", question)
        if match:
            return match.group(1).strip().upper()
        if "usa" in question:
            return "USA"
        if "uk" in question or "united kingdom" in question:
            return "UK"
        if "france" in question:
            return "FRANCE"
        if "canada" in question:
            return "CANADA"
        return None

    def _extract_status(self, question: str) -> str | None:
        for status in ["shipped", "cancelled", "resolved", "on hold", "in process"]:
            if status in question:
                return status.title()
        return None
