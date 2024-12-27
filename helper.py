import ccxt
import sys

import keys
from config import Config

# exchange object
exchange = ccxt.mexc({
    'apiKey': keys.API_KEY,
    'secret': keys.SECRET_KEY
})

# exchange.set_sandbox_mode(True)  # enable sandbox mode

def cancel_orders():
    # Cancel all orders for the symbol
    exchange.cancel_all_orders(Config.SYMBOL)

    print("cancelled orders")

def view_orders():
    # Retrieve all active orders for the symbol
    orders = exchange.fetch_orders(Config.SYMBOL)

    # Print the orders data
    for order in orders:
        order_info = order['info']
        print(f"{order_info['symbol']} | {order_info['orderId']} | {order_info['side']} | {order_info['status']} | {order_info['price']}")

def balance():
    print(f"USDT: {exchange.fetch_balance()['USDT']}")

if __name__ == "__main__":
    # get function name as cli-arg
    globals()[sys.argv[1]]()