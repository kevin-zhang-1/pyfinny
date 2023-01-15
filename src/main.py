from tqdm import tqdm
from dotenv import load_dotenv
import json
import requests
import os
import sqlite3
import xlsxwriter
import openpyxl

load_dotenv()
API_KEY = os.getenv("API_KEY")


statement_types = [
    "balance-sheet-statement",
    "cash-flow-statement",
    "income-statement",
    "quote",
]


def get_company_tickers(
    filename: str = "companies.txt", ticker_dirname: str = "tickers"
) -> list[str]:
    """
    Reads a file of tickers and returns a list of tickers
    """
    companies = []
    filepath = os.path.join(ticker_dirname, filename)
    with open(filepath, "r") as f:
        for line in f:
            companies.append(line.strip())
    return companies


def _load_from_json(
    company: str, statement_type: str, data_dirname: str = "data"
) -> list[dict[str, int | str]]:
    """
    Loads data from local json file and returns a dictionary
    """
    filepath = os.path.join(data_dirname, f"{statement_type}.json")
    with open(filepath, "r") as f:
        data = json.load(f)
    return data[company]


def _fetch_from_api(company: str, statement_type: str) -> list[dict[str, int | str]]:
    """
    Fetches data from the API and returns a dictionary
    """
    url = f"https://financialmodelingprep.com/api/v3/{statement_type}/{company}?apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()
    return data


def _save_to_db(
    data: dict,
    statement_type: str,
    db_path: str = "/Users/lawrencelim/Projects/python-projects/pyfinny/financial_data.db",
):

    # Create a hashmap of the statement types
    name_map = {
        "balance-sheet-statement": "balance_sheet",
        "cash-flow-statement": "cash_flow_statement",
        "income-statement": "income_statement",
        "quote": "quote",
    }

    # Create data tuple and VALUES string
    data_tuple = tuple(data.values())
    values = "(" + "?, " * (len(data) - 1) + "?)"

    # Insert data into database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        f"INSERT INTO {name_map[statement_type]} VALUES {values}", data_tuple
    )
    conn.commit()


def get_financials(
    companies: list[str],
) -> None:
    """
    Fetches data with API and writes to local sqlite3 database
    """
    for statement_type in statement_types:
        for company in tqdm(companies, desc=f"Writing {statement_type} data"):
            financial_statement_data = _fetch_from_api(company, statement_type)
            # financial_statement_data = _load_from_json(company, statement_type)
            for year_index in range(len(financial_statement_data)):
                _save_to_db(financial_statement_data[year_index], statement_type)


def _comparable_analysis_helper(
    company: str,
    db_path: str = "/Users/lawrencelim/Projects/python-projects/pyfinny/financial_data.db",
) -> tuple:
    """
    Writes data from sqlite3 database to xlsx file
    """

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    quote_dict = {
        "price": 0.0,
        "marketCap": 0,
    }
    income_statement_dict = {
        "netIncome": 0,
        "revenue": 0,
        "ebitda": 0,
        "depreciationAndAmortization": 0,
    }
    balance_sheet_dict = {
        "cashAndCashEquivalents": 0,
        "totalDebt": 0,
    }
    cash_flow_statement_dict = {}

    # Fetch corresponding data from database and add it to the dictionary
    for value_type in quote_dict:
        cursor.execute(f"SELECT {value_type} FROM quote WHERE symbol = '{company}'")
        quote_dict[value_type] = cursor.fetchone()[0]
    for value_type in income_statement_dict:
        cursor.execute(
            f"SELECT {value_type} FROM income_statement WHERE symbol = '{company}'"
        )
        income_statement_dict[value_type] = cursor.fetchone()[0]
    for value_type in balance_sheet_dict:
        cursor.execute(
            f"SELECT {value_type} FROM balance_sheet WHERE symbol = '{company}'"
        )
        balance_sheet_dict[value_type] = cursor.fetchone()[0]
    for value_type in cash_flow_statement_dict:
        cursor.execute(
            f"SELECT {value_type} FROM cash_flow_statement WHERE symbol = {company}"
        )
        cash_flow_statement_dict[value_type] = cursor.fetchone()[0]

    return (
        quote_dict,
        income_statement_dict,
        balance_sheet_dict,
        cash_flow_statement_dict,
    )


def comparables_analysis(companies: list[str]) -> None:
    """
    Writes data from sqlite3 database to xlsx file
    """
    for company in companies:
        (
            quote_dict,
            income_statement_dict,
            balance_sheet_dict,
            cash_flow_statement_dict,
        ) = _comparable_analysis_helper(company)

        price = quote_dict["price"]
        marketCap = quote_dict["marketCap"]
        ev = (
            marketCap
            + balance_sheet_dict["totalDebt"]
            - balance_sheet_dict["cashAndCashEquivalents"]
        )
        ebitda = income_statement_dict["ebitda"]
        ebit = ebitda - income_statement_dict["depreciationAndAmortization"]
        revenue = income_statement_dict["revenue"]
        earnings = income_statement_dict["netIncome"]


def load_companies():
    companies = get_company_tickers()
    get_financials(companies)


def main():
    # companies = get_company_tickers()
    # comparables_analysis(companies)
    get_financials(['NVDA'])


if __name__ == "__main__":
    main()
