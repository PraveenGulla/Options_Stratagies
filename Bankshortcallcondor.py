import time
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from threading import Thread

# Step 1: Define IB API Client Class
class IBApi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

    def error(self, reqId, errorCode, errorString):
        print(f"Error {reqId} - {errorCode}: {errorString}")

    def nextValidId(self, orderId):
        self.nextOrderId = orderId

# Step 2: Connect to TWS
def connect_to_tws():
    app = IBApi()
    app.connect("127.0.0.1", 7497, clientId=1)  # Connect to paper trading port
    app.nextOrderId = None

    # Start the IBAPI client thread
    api_thread = Thread(target=app.run)
    api_thread.start()

    # Wait for connection
    while app.nextOrderId is None:
        time.sleep(0.1)

    return app

# Step 3: Create Option Contracts
def create_option_contract(symbol, strike, right, expiry):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "OPT"
    contract.exchange = "SMART"
    contract.currency = "USD"
    contract.lastTradeDateOrContractMonth = expiry
    contract.strike = strike
    contract.right = right  # 'C' for Call
    contract.multiplier = "100"
    return contract

# Step 4: Create Order Function
def create_order(action, quantity):
    order = Order()
    order.action = action  # 'BUY' or 'SELL'
    order.orderType = "MKT"
    order.totalQuantity = quantity
    order.transmit = True
    return order

# Step 5: Execute Short Call Condor Strategy
def short_call_condor(app, symbol, strikes, expiry):
    itm_call_buy = create_option_contract(symbol, strikes[0], 'C', expiry)  # ITM Buy
    itm_call_sell = create_option_contract(symbol, strikes[1], 'C', expiry)  # ITM Sell
    otm_call_sell = create_option_contract(symbol, strikes[2], 'C', expiry)  # OTM Sell
    otm_call_buy = create_option_contract(symbol, strikes[3], 'C', expiry)  # OTM Buy

    print("Placing Short Call Condor Orders...")

    # Place the orders
    app.placeOrder(app.nextOrderId, itm_call_buy, create_order("BUY", 1))
    app.nextOrderId += 1
    app.placeOrder(app.nextOrderId, itm_call_sell, create_order("SELL", 1))
    app.nextOrderId += 1
    app.placeOrder(app.nextOrderId, otm_call_sell, create_order("SELL", 1))
    app.nextOrderId += 1
    app.placeOrder(app.nextOrderId, otm_call_buy, create_order("BUY", 1))
    app.nextOrderId += 1

# Step 6: Monitor Market for Re-entry Conditions
def monitor_and_reenter(app, symbol, strikes, expiry, reentry_threshold=5):
    current_price = get_market_price(symbol)  # Assume a function that fetches the current market price
    initial_price = current_price

    while True:
        time.sleep(60)  # Monitor every minute
        current_price = get_market_price(symbol)

        # If market moves beyond re-entry threshold, exit and re-enter
        if abs(current_price - initial_price) >= reentry_threshold:
            print("Re-entry triggered. Exiting and re-entering...")
            close_positions(app)
            short_call_condor(app, symbol, strikes, expiry)
            initial_price = current_price  # Reset the initial price

# Step 7: Close Existing Positions
def close_positions(app):
    print("Closing existing positions...")
    # This function closes all open positions, either through offsetting orders or app.reqGlobalCancel().

# Step 8: Fetch Market Price (Dummy Implementation)
def get_market_price(symbol):
    # Replace with real market data fetching logic via IBAPI or another data provider
    return 100  # Example value

# Step 9: Main Execution
if __name__ == "__main__":
    symbol = "AAPL"
    strikes = [165, 170, 175, 180]  # Example ITM and OTM strikes
    expiry = "20231020"  # Expiration date in YYYYMMDD format

    app = connect_to_tws()

    try:
        # Execute the Short Call Condor strategy
        short_call_condor(app, symbol, strikes, expiry)

        # Monitor the market and re-enter if necessary
        monitor_and_reenter(app, symbol, strikes, expiry)
    finally:
        app.disconnect()
