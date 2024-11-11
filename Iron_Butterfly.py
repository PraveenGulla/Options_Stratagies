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
        self.nextOrderId = None
        self.contract_details = {}

    def error(self, reqId, errorCode, errorString):
        print(f"Error {reqId} - {errorCode}: {errorString}")

    def nextValidId(self, orderId):
        self.nextOrderId = orderId

    def contractDetails(self, reqId, contractDetails):
        self.contract_details[reqId] = contractDetails

# Step 2: Connect to TWS
def connect_to_tws():
    app = IBApi()
    app.connect("127.0.0.1", 7497, clientId=112)  # Paper trading port

    # Start the IBAPI client thread
    api_thread = Thread(target=app.run)
    api_thread.start()

    # Wait for connection
    while app.nextOrderId is None:
        time.sleep(0.1)

    return app

# Step 3: Create Option Contracts with Verification
def create_option_contract(app, symbol, strike, right, expiry):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "OPT"
    contract.exchange = "SMART"
    contract.currency = "USD"
    contract.lastTradeDateOrContractMonth = expiry
    contract.strike = strike
    contract.right = right  # 'C' for Call, 'P' for Put
    contract.multiplier = "100"
    
    # Request contract details to verify
    reqId = app.nextOrderId
    app.contract_details[reqId] = None
    app.reqContractDetails(reqId, contract)
    time.sleep(1)  # Wait for response

    if app.contract_details[reqId] is None:
        print(f"Contract not found for {symbol} with strike {strike} and expiry {expiry}")
        return None
    else:
        return contract

# Step 4: Create Order Function
def create_order(action, quantity):
    order = Order()
    order.action = action  # 'BUY' or 'SELL'
    order.orderType = "MKT"
    order.totalQuantity = quantity
    order.transmit = True
    order.eTradeOnly = ''
    order.firmQuoteOnly = ''
    return order

# Step 5: Define Iron Butterfly Strategy Execution
def iron_butterfly(app, symbol, atm_strike, otm_strike, expiry):
    atm_call = create_option_contract(app, symbol, atm_strike, 'C', expiry)
    atm_put = create_option_contract(app, symbol, atm_strike, 'P', expiry)
    otm_call = create_option_contract(app, symbol, otm_strike + 10, 'C', expiry)
    otm_put = create_option_contract(app, symbol, otm_strike - 10, 'P', expiry)

    if not all([atm_call, atm_put, otm_call, otm_put]):
        print("One or more contracts not found; unable to place orders.")
        return

    print("Placing Iron Butterfly Orders...")

    # Sell ATM call and put
    app.placeOrder(app.nextOrderId, atm_call, create_order("SELL", 1))
    app.nextOrderId += 1
    app.placeOrder(app.nextOrderId, atm_put, create_order("SELL", 1))
    app.nextOrderId += 1

    # Buy OTM call and put
    app.placeOrder(app.nextOrderId, otm_call, create_order("BUY", 1))
    app.nextOrderId += 1
    app.placeOrder(app.nextOrderId, otm_put, create_order("BUY", 1))
    app.nextOrderId += 1

# Step 6: Monitor Market and Re-entry Logic (Simplified Example)
def monitor_and_reenter(app, symbol, atm_strike, expiry, reentry_threshold=5):
    initial_price = get_market_price(symbol)
    while True:
        time.sleep(60)  # Check every minute
        current_price = get_market_price(symbol)

        if abs(current_price - initial_price) >= reentry_threshold:
            print("Re-entry triggered. Exiting current position and re-entering...")
            close_positions(app)
            iron_butterfly(app, symbol, atm_strike, atm_strike, expiry)
            initial_price = current_price

# Step 7: Function to Close Existing Positions
def close_positions(app):
    print("Closing existing positions...")
    app.reqGlobalCancel()  # Cancel all open orders

# Step 8: Fetch Market Price (Dummy Function)
def get_market_price(symbol):
    return 200  # Example static price; replace with actual market data function if available

# Step 9: Main Execution
if __name__ == "__main__":
    symbol = "AAPL"  # S&P 500 ETF
    atm_strike = 250  # Example ATM strike price
    otm_strike = 200  # Example OTM strike price
    expiry = "20241115"  # YYYYMMDD format for third Friday in November

    app = connect_to_tws()

    try:
        iron_butterfly(app, symbol, atm_strike, otm_strike, expiry)
        monitor_and_reenter(app, symbol, atm_strike, expiry)
    finally:
        app.disconnect()
