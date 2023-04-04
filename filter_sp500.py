from tickers_info import filter_sp500_by_quants, filter_tickers_by_quants, print_tickers

if __name__ == "__main__":
    filtered = filter_sp500_by_quants()
    filtered = filter_tickers_by_quants(filtered)
    print_tickers(filtered)
