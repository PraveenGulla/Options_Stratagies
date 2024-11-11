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

    # Start the IBAPI client in a separate thread
    api_thread = Thread(target=app.run)
    api_thread.start()

    # Wait for connection
    while app.nextOrderId is None:
        time.sleep(0.1)

    return app

# Step 3: Create Option Contract
def create_option_contract(symbol, strike, right, expiry):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "OPT"
    contract.exchange = "SMART"
    contract.currency = "USD"
    contract.lastTradeDateOrContractMonth = expiry
    contract.strike = strike
    contract.right = right  # 'C' for Call, 'P' for Put
    contract.multiplier = "100"
    return contract

# Step 4: Create Order Function
def create_order(action, quantity, order_type="MKT", stop_price=None):
    order = Order()
    order.action = action  # 'SELL' for initial order
    order.orderType = order_type  # 'MKT' for market order, 'STP' for stop loss
    order.totalQuantity = quantity
    order.transmit = True

    if stop_price:
        order.auxPrice = stop_price  # Set stop-loss price

    return order

# Step 5: Execute Short Straddle Strategy
def short_straddle(app, symbol, strike, expiry):
    # Define the option contracts (Call and Put with the same strike and expiry)
    call_option = create_option_contract(symbol, strike, 'C', expiry)
    put_option = create_option_contract(symbol, strike, 'P', expiry)

    print("Placing Short Straddle Orders...")

    # Sell the call and put options
    app.placeOrder(app.nextOrderId, call_option, create_order("SELL", 1))
    app.nextOrderId += 1
    app.placeOrder(app.nextOrderId, put_option, create_order("SELL", 1))
    app.nextOrderId += 1

# Step 6: Monitor Stop Losses for Both Legs
def monitor_stop_loss(app, symbol, strike, expiry, stop_loss_call, stop_loss_put):
    call_option = create_option_contract(symbol, strike, 'C', expiry)
    put_option = create_option_contract(symbol, strike, 'P', expiry)

    print(f"Setting stop losses on the call and put options...")

    # Place stop-loss orders
    call_stop_loss_order = create_order("BUY", 1, "STP", stop_price=stop_loss_call)
    app.placeOrder(app.nextOrderId, call_option, call_stop_loss_order)
    app.nextOrderId += 1

    put_stop_loss_order = create_order("BUY", 1, "STP", stop_price=stop_loss_put)
    app.placeOrder(app.nextOrderId, put_option, put_stop_loss_order)
    app.nextOrderId += 1

# Step 7: Fetch Market Price (Dummy Function)
def get_market_price(symbol):
    # Replace with actual market data fetching logic via IBAPI
    return 100  # Example placeholder

# Step 8: Main Execution
if __name__ == "__main__":
    symbol = "AAPL"
    strike = 170  # Strike price for both call and put
    expiry = "20231020"  # Expiration date in YYYYMMDD format
    stop_loss_call = 5.0  # Stop loss for the call option
    stop_loss_put = 5.0   # Stop loss for the put option

    app = connect_to_tws()

    try:
        # Execute the Short Straddle strategy
        short_straddle(app, symbol, strike, expiry)

        # Monitor stop losses on both legs
        monitor_stop_loss(app, symbol, strike, expiry, stop_loss_call, stop_loss_put)
    finally:
        app.disconnect()
