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
    app.connect("127.0.0.1", 7497, clientId=1)  # Paper trading port
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
    contract.right = right  # 'P' for Put option
    contract.multiplier = "100"
    return contract

# Step 4: Create Order Function
def create_order(action, quantity, order_type="MKT", stop_price=None):
    order = Order()
    order.action = action  # 'BUY' or 'SELL'
    order.orderType = order_type  # 'MKT' for market order or 'STP' for stop-loss
    order.totalQuantity = quantity
    order.transmit = True

    if stop_price:
        order.auxPrice = stop_price  # Set stop-loss price

    return order

# Step 5: Execute Bear Put Spread Strategy
def bear_put_spread(app, symbol, higher_strike, lower_strike, expiry):
    # Define the option contracts
    buy_put = create_option_contract(symbol, higher_strike, 'P', expiry)  # Buy higher strike put
    sell_put = create_option_contract(symbol, lower_strike, 'P', expiry)  # Sell lower strike put

    print("Placing Bear Put Spread Orders...")

    # Place the buy and sell orders
    app.placeOrder(app.nextOrderId, buy_put, create_order("BUY", 1))
    app.nextOrderId += 1
    app.placeOrder(app.nextOrderId, sell_put, create_order("SELL", 1))
    app.nextOrderId += 1

# Step 6: Monitor Stop Loss on Sold Put Leg
def monitor_stop_loss(app, symbol, lower_strike, expiry, stop_loss_price):
    sell_put = create_option_contract(symbol, lower_strike, 'P', expiry)

    print(f"Setting stop loss on the sold put at {stop_loss_price}...")
    
    # Place a stop-loss order on the sold put
    stop_loss_order = create_order("BUY", 1, "STP", stop_price=stop_loss_price)
    app.placeOrder(app.nextOrderId, sell_put, stop_loss_order)
    app.nextOrderId += 1

# Step 7: Fetch Market Price (Dummy Implementation)
def get_market_price(symbol):
    # Replace this with real-time market data fetching logic
    return 100  # Example value

# Step 8: Main Execution
if __name__ == "__main__":
    symbol = "AAPL"
    higher_strike = 170  # Higher strike price for the bought put
    lower_strike = 160   # Lower strike price for the sold put
    expiry = "20231020"  # Expiration date in YYYYMMDD format
    stop_loss_price = 5.0  # Example stop loss on the sold put leg

    app = connect_to_tws()

    try:
        # Execute the Bear Put Spread strategy
        bear_put_spread(app, symbol, higher_strike, lower_strike, expiry)

        # Monitor the stop loss on the sold put leg
        monitor_stop_loss(app, symbol, lower_strike, expiry, stop_loss_price)
    finally:
        app.disconnect()
