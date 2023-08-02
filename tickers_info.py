import argparse
from datetime import datetime, timedelta

import pandas
import urllib3
from tabulate import tabulate
from tqdm import tqdm
from yahooquery import Ticker
import numpy as np

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def print_info(ticker):
    # Definition of Terms: https://johnsonandjohnson.gcs-web.com/static-files/f2c6ced8-e949-499f-be2d-f651f6a9e083
    ticker = ticker.replace(".", "-").upper()
    data = Ticker(ticker, validate=True, verify=False)

    balance_sheet = data.balance_sheet()
    income_statement = data.income_statement(trailing=False)

    if not data.summary_detail:
        print(f"Ticker {ticker} not found")
        return
    elif isinstance(balance_sheet, str):
        print(f"Ticker {ticker} has no balance sheet")
        return

    res = []
    for i in range(len(balance_sheet)):
        bs = balance_sheet.iloc[[i]]

        as_of_day = bs["asOfDate"].item()
        start = as_of_day - timedelta(days=7)

        history = data.history(start=start, end=as_of_day + timedelta(days=1))
        close_price = history.iloc[[i]]["close"].item()

        ord_shares_num = bs.get("OrdinarySharesNumber", pandas.Series(0)).item()
        # total_equity = bs.get("TotalEquityGrossMinorityInterest", pandas.Series(0)).item()
        # preferred_stock_equity = bs.get("PreferredStockEquity", pandas.Series(0)).item()
        common_stock_equity = bs.get(
            "CommonStockEquity", pandas.Series(0)
        ).item()  # book value

        in_stat = income_statement.iloc[[i]]
        net_income_common_stock = in_stat.get(
            "NetIncomeCommonStockholders", pandas.Series(0)
        ).item()
        total_revenue = in_stat.get("TotalRevenue", pandas.Series(0)).item()

        fiscal_res = {
            "Ticker": ticker,
            "As of Day": as_of_day.strftime("%Y-%m-%d"),
            "Close Price($)": close_price,
            "E/P(%)": net_income_common_stock / (ord_shares_num * close_price) * 100,
            "P/B": ord_shares_num * close_price / common_stock_equity,
            "P/E": ord_shares_num * close_price / net_income_common_stock,
            "P/S": ord_shares_num * close_price / total_revenue,
            "EPS($)": in_stat.get("BasicEPS")
            if not in_stat.get("BasicEPS").isnull().item()
            else net_income_common_stock / ord_shares_num,
            "D. EPS($)": in_stat.get("DilutedEPS", pandas.Series(0)).item(),
            "ROS(%)": net_income_common_stock / total_revenue * 100,
            "ROEq(%)": net_income_common_stock / common_stock_equity * 100,
        }
        res.append(fiscal_res)

    # Get the latest values
    summary = data.summary_detail[list(data.summary_detail.keys())[0]]
    prev_close_price = summary["previousClose"]
    latest_res = {
        "Ticker": ticker,
        "As of Day": datetime.today().strftime("%Y-%m-%d"),
        "Close Price($)": prev_close_price,
        "P/B": ord_shares_num * prev_close_price / common_stock_equity,
        "Div. Y.(%)": summary.get("trailingAnnualDividendYield", 0.0) * 100,
        "5y Div. Y.(%)": summary.get("fiveYearAvgDividendYield", 0.0),
        "P/E": ord_shares_num * prev_close_price / net_income_common_stock,
        "E/P(%)": net_income_common_stock / (ord_shares_num * prev_close_price) * 100,
        "P/S": ord_shares_num * prev_close_price / total_revenue,
        # "ROS(%)": net_income_common_stock / total_revenue * 100,
        # "ROE(%)": net_income_common_stock / common_stock_equity * 100,
    }
    res.append(latest_res)
    return res


def get_latest_values(ticker):
    ticker = ticker.replace(".", "-").upper()
    data = Ticker(ticker, validate=True, verify=False)

    if not data.summary_detail:
        print(f"Ticker {ticker} not found")
        return
    elif isinstance(data.balance_sheet(), str):
        print(f"Ticker {ticker} has no balance sheet")
        return

    i = len(data.balance_sheet()) - 1
    bs = data.balance_sheet().iloc[[i]]

    ord_shares_num = bs.get("OrdinarySharesNumber", pandas.Series(0)).item()
    common_stock_equity = bs.get(
        "CommonStockEquity", pandas.Series(0)
    ).item()  # book value

    in_stat = data.income_statement(trailing=False).iloc[[i]]
    net_income_common_stock = in_stat.get(
        "NetIncomeCommonStockholders", pandas.Series(0)
    ).item()
    total_revenue = in_stat.get("TotalRevenue", pandas.Series(0)).item()

    summary = data.summary_detail[list(data.summary_detail.keys())[0]]
    prev_close_price = summary["previousClose"]
    latest_res = {
        "Ticker": ticker,
        "As of Day": datetime.today().strftime("%Y-%m-%d"),
        "Close Price($)": prev_close_price,
        "P/B": ord_shares_num * prev_close_price / common_stock_equity,
        "Div. Y.(%)": summary.get("trailingAnnualDividendYield", 0.0) * 100,
        "5y Div. Y.(%)": summary.get("fiveYearAvgDividendYield", 0.0),
        "P/E": ord_shares_num * prev_close_price / net_income_common_stock,
        "E/P(%)": net_income_common_stock / (ord_shares_num * prev_close_price) * 100,
        "P/S": ord_shares_num * prev_close_price / total_revenue,
    }

    return latest_res


def get_tickers_by_user_input():
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker", help="Ticker symbol(s)", nargs="+")
    args = parser.parse_args()

    tickers = args.ticker if isinstance(args.ticker, list) else [args.ticker]
    return tickers


def print_tickers(tickers):
    for ticker in tickers:
        res = print_info(ticker.upper())
        table = tabulate(
            res,
            tablefmt="fancy_grid",
            headers="keys",
            missingval='"',
            floatfmt=".2f",
        )
        print(table)


def filter_tickers_by_quants(tickers):
    filtered = []
    for ticker in tqdm(tickers):
        try:
            res = print_info(ticker.upper())
            is_earn_positive = np.array(
                [isinstance(r["P/E"], float) and r["P/E"] > 0 for r in res]
            ).all()
            if not is_earn_positive:
                continue
            is_book_positive = np.array(
                [isinstance(r["P/B"], float) and r["P/B"] > 0 for r in res]
            ).all()
            if not is_book_positive:
                continue
            ep = np.array(
                [r["E/P(%)"] if isinstance(r["E/P(%)"], float) else 0.0 for r in res]
            )
            fy_div_y = res[-1]["5y Div. Y.(%)"]
            if not (isinstance(fy_div_y, float) and fy_div_y >= 4.0) and not (
                (ep > 5.0).all()
                and ((1 + ep / 100).prod() ** (1 / len(ep)) - 1 > 0.09).all()
            ):
                continue
            filtered.append(ticker)
        except Exception as e:
            print(f"Error: {ticker} - {e}")
    return filtered


def filter_sp500_by_quants():
    tickers = pandas.read_html(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", header=0
    )[0]
    tickers = tickers.Symbol.tolist()

    filtered = []
    for ticker in tqdm(tickers):
        values = get_latest_values(ticker.upper())
        if isinstance(values, dict) and (
            values["P/B"] < 1.5
            or (
                values["P/E"] < 15
                and values["P/E"] * values["P/B"] <= 22.5
                and values["P/E"] > 0.0
            )
        ):
            filtered.append(values["Ticker"])

    return filtered


if __name__ == "__main__":
    tickers = get_tickers_by_user_input()
    print_tickers(tickers)
