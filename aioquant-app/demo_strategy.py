# -*- coding:utf-8 -*-
import asyncio
from aioquant.datas.market_data import SpreadData
from aioquant.event import EventSpread
from aioquant.utils.warning import WarningSubscribe, WarningMessage
from aioquant import const
from aioquant import quant
from aioquant.utils import logger, tools
from aioquant.configure import config
from aioquant.utils.command import CommandPublish, CommandSubscribe
from aioquant.market import Orderbook
from aioquant.market import Funding
from aioquant.trade import Trade
from aioquant.position import Position
from aioquant.order import Order
from aioquant.asset import Asset
from aioquant.order import ORDER_ACTION_BUY, ORDER_ACTION_SELL
from aioquant.order import (ORDER_STATUS_SUBMITTED,
                            ORDER_STATUS_PARTIAL_FILLED,
                            ORDER_STATUS_FILLED,
                            ORDER_STATUS_CANCELED,
                            ORDER_STATUS_FAILED)
from aioquant.order import (ORDER_TYPE_LIMIT,
                            ORDER_TYPE_MARKET,
                            ORDER_TYPE_IOC,
                            ORDER_TYPE_FOK,
                            ORDER_TYPE_POST_ONLY)
from aioquant.order import (ORDER_ACTION_BUY,
                            ORDER_ACTION_SELL,
                            TRADE_TYPE_BUY_OPEN,
                            TRADE_TYPE_SELL_OPEN,
                            TRADE_TYPE_SELL_CLOSE,
                            TRADE_TYPE_BUY_CLOSE)
from aioquant.error import Error
from aioquant.tasks import SingleTask, LoopRunTask
from aioquant.utils.decorator import async_method_locker
from aioquant.utils.tools import TranslateQuantity
from aioquant.utils.mongo import MongoDBBase
from aioquant.markets.binance_swap import BinanceSwapMarket as BinanceSwapMarket
from aioquant.markets.gate_swap import GateSwapMarket as GateSwapMarket
from aioquant.markets.huobi_swap import HuobiSwapMarket as HuobiSwapMarket
from aioquant.markets.okex_swap import OKExSwapMarket as OkexSwapMarket
from aioquant.markets.okex_swap_v5 import OKExV5SwapMarket as OKExV5SwapMarket


class MyStrategy:
    """
    For Test Websocket Connection to the frontend.
    """

    def __init__(self):
        """
        初始化
        """
        # 初始化变量
        self.status = {}  # The read-only status
        self.params = {}  # The changable params

        # Init the value
        self.status['exchanges_connected'] = 4
        self.status['profitable_trades'] = 38
        self.status['overall_pnl_usd'] = 283
        self.status['fees_paid'] = 591
        self.status['trade_allow'] = True

        # Init the params
        self.params["binance_on"] = True
        self.params["huobi_on"] = True
        self.params["okx_leverage"] = 1.5
        self.params["bitmex_on"] = True
        self.params["max_positon"] = 10000
        self.params["trade_direction"] = "OPEN"

        SingleTask.run(self.initialize)  # 初始化

    async def initialize(self, *args, **kwargs):
        """ Initialize the strategy with several functions.
        """

        cc = {
            "symbols": [{"name": ["BTC-USDT-SWAP", "ETH-USDT-SWAP"], "type":"swap"}],
            "channels": ['orderbook'],
            "orderbook_refresh": config.ORDERBOOK_REFRESH,  # False -> incremental, True: 全量
            "platform": 'binance_swap',
            "orderbook_update_callback": self.on_event_orderbook_update,
            "orderbook_length": config.ORDERBOOK_LENGTH,
        }
        BinanceSwapMarket(**cc)  # FOR DEMO, NO USE

        CommandSubscribe(self.on_event_command_callback)
        LoopRunTask.register(self.publish_command, 1)
        LoopRunTask.register(self.publish_log, 1)

    @staticmethod
    def transform_params(params: dict):
        """
        Translate the Params for Frontend Parsing

        Example: 
            Input:
                params = {
                    'binance_on': True,
                    'max_position': 1500,
                    'max_leverage': 1.5,
                    'trade_direction': 'LONG'
                }

            Output:
                result = [
                    ['binance_on', True, 'bool'],
                    ['max_position', 1500, 'int'],
                    ['max_leverage', 1.5, 'float'],
                    ['trade_direction', 'LONG', 'str']
                ]
        """
        try:
            _ = []
            for i in params.items():
                _.append([i[0], i[1], type(i[1]).__name__])
            return _
        except:
            logger.error("`self.params` error! Cannot transform it!")
            return _

    @staticmethod
    def logging(msg, level="info", *args, **kwargs):
        """
        Logging the Msg and send it to frontend!
        Args:
            msg: The logger.content
            level: info, warning, error.
        """
        _level = level if level else 'info'
        d = {
            'logging': {
                'level': _level, 'msg': msg, "ts": tools.get_cur_timestamp()
            }
        }

        if level == "error":
            logger.error(msg)
        elif level == "warning":
            logger.warn(msg)
        else:
            logger.info(msg)
        CommandPublish.publish(target="frontend", message=d)

    async def publish_command(self, *args, **kwargs):
        """
        Routinely send status data to frontend!
        Just for test!
        """
        logger.info("Sending Status and Params to frontend!")
        # The msg to be sent to frontend. - Routine
        self.status['fees_paid'] = tools.get_cur_timestamp()
        message = {
            "status": self.status,
            "params": self.transform_params(self.params)
        }

        CommandPublish.publish(target="frontend", message=message)

    async def publish_log(self, *args, **kwargs):
        logger.info("Running Publish log")
        await asyncio.sleep(0.1)
        self.logging("This is a test = info- msg", level='info')
        await asyncio.sleep(0.1)
        self.logging("This is a test = warning- msg", level='warning')
        await asyncio.sleep(0.1)
        self.logging("This is a test = error- msg", level='error')

    @async_method_locker("on_event_init_callback.locker", timeout=15)
    async def on_event_command_callback(self, data, **kwargs):
        """
        Do something when program received command from frontend.
        """
        target = data.target
        if target != 'backend':
            return
        message = data.message
        logger.info(message)
        if not message.get('request'):
            return
        # Change the params on request
        requests: dict = message['request']
        self.params.update(requests)

        # Msg to be sent to frontend
        _msg = {
            'response': 'success'
        }
        CommandPublish.publish(target="frontend", message=_msg)

    @async_method_locker("on_event_init_callback.locker", timeout=15)
    async def on_event_init_callback(self, success: bool, **kwargs):
        """各交易所各交易对的trade对象初始化是否成功
        """
        logger.info("success:", success, "kwargs:", kwargs, caller=self)

    @async_method_locker("on_event_error_callback.locker", timeout=15)
    async def on_event_error_callback(self, error, **kwargs):
        """
        各交易所各交易对trade对象运行错误回调
        """
        logger.info("error:", error, "kwargs:", kwargs, caller=self)

    @async_method_locker("on_event_orderbook_update.locker", timeout=15)
    async def on_event_orderbook_update(self, orderbook: Orderbook):
        """
        订单薄更新回调
        self.orderbook 本地记录
        """
        # logger.info(orderbook)
        pass
