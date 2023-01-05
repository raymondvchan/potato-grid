import ccxt
import time
import sys
import logging
import json
import os

import keys, config

## logging
# Set the log level to DEBUG
logging.basicConfig(level=logging.INFO)

# Set the log format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create a file handler and set the log format
file_handler = logging.FileHandler(config.LOG_FILE)
file_handler.setFormatter(formatter)

# Add the file handler to the logger
logger = logging.getLogger()
logger.addHandler(file_handler)


# exchange object
exchange = ccxt.binance({
    'apiKey': keys.API_KEY,
    'secret': keys.SECRET_KEY
})

exchange.set_sandbox_mode(True)  # enable sandbox mode

ticker = exchange.fetch_ticker(config.SYMBOL)

buy_orders = []
sell_orders = []

def write_order_log(new_data, side):

    # open json file
    with open(config.ORDER_LOG, 'r+') as file:
        try:
            # read existing data
            file_data = json.load(file)
        except ValueError:
            # file_data = [[], []]
            file_data = {
                'buy': [],
                'sell': []
            }

        # add new data
        file_data[side] = new_data

        # write updated data to file
        file.seek(0)
        json.dump(file_data, file)

def create_buy_order(symbol, size, price):
    logger.info("==> submitting market limit buy order at {}".format(price))
    order = exchange.create_limit_buy_order(symbol, size, price)
    buy_orders.append(order['info'])

def create_sell_order(symbol, size, price):
    logger.info("==> submitting market limit sell order at {}".format(price))
    order = exchange.create_limit_sell_order(symbol, size, price)
    sell_orders.append(order['info'])

def init():
    global buy_orders, sell_orders

    if os.path.exists(config.ORDER_LOG):
        with open(config.ORDER_LOG, 'r+') as file:
            # read existing data
            file_data = json.load(file)

            # read existing orders
            buy_orders = file_data['buy']
            sell_orders = file_data['sell']
    else:
        # create new file if not exist
        open(config.ORDER_LOG, 'a').close()

def main():
    logger.info('=> Starting grid trading bot')

    global buy_orders, sell_orders
    
    if not buy_orders:
        # place inital buy orders
        for i in range(config.NUM_BUY_GRID_LINES):
            price = ticker['bid'] - (config.GRID_SIZE * (i + 1))
            create_buy_order(config.SYMBOL, config.POSITION_SIZE, price)
        
        # write order logs to file
        write_order_log(buy_orders, 'buy')

        # place initial sell orders
        for i in range(config.NUM_SELL_GRID_LINES):
            price = ticker['bid'] + (config.GRID_SIZE * (i + 1))
            create_sell_order(config.SYMBOL, config.POSITION_SIZE, price)

        # write order logs to file
        write_order_log(sell_orders, 'sell')

    while True:
        closed_order_ids = []

        # check if buy order is closed
        for buy_order in buy_orders:
            logger.info("=> checking buy order {}".format(buy_order['orderId']))
            try:
                order = exchange.fetch_order(buy_order['orderId'], config.SYMBOL)
            except Exception as e:
                logger.error(e)
                logger.warning("=> request failed, retrying")
                continue
                
            order_info = order['info']

            if order_info['status'] == config.CLOSED_ORDER_STATUS:
                closed_order_ids.append(order_info['orderId'])
                logger.info("=> buy order executed at {}".format(order_info['price']))
                new_sell_price = float(order_info['price']) + config.GRID_SIZE
                logger.info("=> creating new limit sell order at {}".format(new_sell_price))
                create_sell_order(config.SYMBOL, config.POSITION_SIZE, new_sell_price)

            time.sleep(config.CHECK_ORDERS_FREQUENCY)

        # check if sell order is closed
        for sell_order in sell_orders:
            logger.info("=> checking sell order {}".format(sell_order['orderId']))
            try:
                order = exchange.fetch_order(sell_order['orderId'], config.SYMBOL)
            except Exception as e:
                logger.error(e)
                logger.warning("=> request failed, retrying")
                continue
                
            order_info = order['info']

            if order_info['status'] == config.CLOSED_ORDER_STATUS:
                closed_order_ids.append(order_info['orderId'])
                logger.info("=> sell order executed at {}".format(order_info['price']))
                new_buy_price = float(order_info['price']) - config.GRID_SIZE
                logger.info("=> creating new limit buy order at {}".format(new_buy_price))
                create_buy_order(config.SYMBOL, config.POSITION_SIZE, new_buy_price)

            time.sleep(config.CHECK_ORDERS_FREQUENCY)

        # remove closed orders from list
        for order_id in closed_order_ids:
            buy_orders = [buy_order for buy_order in buy_orders if buy_order['orderId'] != order_id]
            sell_orders = [sell_order for sell_order in sell_orders if sell_order['orderId'] != order_id]
        
        # write order logs to file
        write_order_log(buy_orders, 'buy')
        write_order_log(sell_orders, 'sell')

        # exit if no sell orders are left
        if len(sell_orders) == 0:
            sys.exit("stopping bot, nothing left to sell")

if __name__ == "__main__":
    init()
    main()