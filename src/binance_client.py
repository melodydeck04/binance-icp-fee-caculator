"""Binance API Client using python-binance"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from binance.client import Client

logger = logging.getLogger(__name__)


class BinanceClient:
    """Binance API Client"""
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        self.api_key = api_key
        self.api_secret = api_secret
        
        if api_key and api_secret:
            self.client = Client(api_key, api_secret)
        else:
            self.client = None
        
        logger.info(f"BinanceClient initialized")
    
    def get_all_trades(
        self,
        symbol: str,
        start_time: int = None,
        end_time: int = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        获取所有成交记录
        
        Args:
            symbol: 交易对 (e.g., "ICPUSDT")
            start_time: 开始时间 (毫秒时间戳)
            end_time: 结束时间 (毫秒时间戳)
            limit: 每次请求数量上限
            
        Returns:
            成交列表
        """
        if not self.client:
            raise ValueError("API key and secret required")
        
        all_trades = []
        
        # 递归获取所有数据
        while True:
            try:
                params = {
                    "symbol": symbol.upper(),
                    "limit": limit
                }
                
                if start_time:
                    params["startTime"] = start_time
                
                if end_time:
                    params["endTime"] = end_time
                
                data = self.client.get_my_trades(**params)
                
                if not data:
                    break
                
                all_trades.extend(data)
                
                # 如果返回数量小于 limit，说明已经获取完毕
                if len(data) < limit:
                    break
                
                # 更新 startTime 为最后一条记录的时间 + 1
                start_time = int(data[-1]["time"]) + 1
                
            except Exception as e:
                logger.error(f"Error fetching trades: {e}")
                break
        
        return all_trades
    
    def get_trade_fees(
        self,
        symbol: str,
        start_time: int = None,
        end_time: int = None
    ) -> Dict:
        """
        获取交易手续费
        
        Args:
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            手续费统计
        """
        trades = self.get_all_trades(symbol, start_time, end_time)
        
        usdt_fees = 0.0
        bnb_fees = 0.0
        
        for trade in trades:
            commission = float(trade.get("commission", 0))
            commission_asset = trade.get("commissionAsset", "")
            
            if commission_asset == "USDT":
                usdt_fees += commission
            elif commission_asset == "BNB":
                bnb_fees += commission
        
        return {
            "total_trades": len(trades),
            "usdt_fees": usdt_fees,
            "bnb_fees": bnb_fees,
            "trades": trades
        }
    
    def get_daily_bnb_price(self, date: str) -> Optional[float]:
        """
        获取指定日期的 BNB 价格
        
        Args:
            date: 日期 (格式: "2024-01-01")
            
        Returns:
            BNB 价格 (USDT)
        """
        try:
            # 转换为时间戳
            dt = datetime.strptime(date, "%Y-%m-%d")
            start_ts = int(dt.timestamp() * 1000)
            end_ts = int((dt + timedelta(days=1)).timestamp() * 1000)
            
            # 获取 K 线数据
            klines = self.client.get_klines(
                symbol="BNBUSDT",
                interval="1d",
                startTime=start_ts,
                endTime=end_ts,
                limit=1
            )
            
            if klines and len(klines) > 0:
                # 收盘价
                return float(klines[0][4])
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to get BNB price for {date}: {e}")
            return None
    
    def get_bnb_prices_for_dates(self, dates: List[str]) -> Dict[str, float]:
        """
        获取多个日期的 BNB 价格
        
        Args:
            dates: 日期列表
            
        Returns:
            {日期: 价格}
        """
        prices = {}
        
        for date in dates:
            price = self.get_daily_bnb_price(date)
            if price:
                prices[date] = price
        
        return prices
    
    def calculate_weighted_fees(
        self,
        symbol: str,
        start_time: int,
        end_time: int
    ) -> Dict:
        """
        计算加权手续费
        
        Args:
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            计算结果
        """
        # 获取所有交易
        fee_data = self.get_trade_fees(symbol, start_time, end_time)
        
        # 收集所有交易日期
        trade_dates = set()
        for trade in fee_data["trades"]:
            trade_time = datetime.fromtimestamp(trade["time"] / 1000)
            trade_dates.add(trade_time.strftime("%Y-%m-%d"))
        
        # 获取 BNB 价格
        bnb_prices = self.get_bnb_prices_for_dates(list(trade_dates))
        
        # 按日期汇总 BNB 手续费
        daily_bnb_fees = {}
        for trade in fee_data["trades"]:
            trade_time = datetime.fromtimestamp(trade["time"] / 1000)
            date = trade_time.strftime("%Y-%m-%d")
            commission_asset = trade.get("commissionAsset", "")
            
            if commission_asset == "BNB":
                commission = float(trade.get("commission", 0))
                daily_bnb_fees[date] = daily_bnb_fees.get(date, 0) + commission
        
        # 计算加权 BNB 手续费 (转换为 USDT)
        bnb_fees_in_usdt = 0.0
        for date, bnb_amount in daily_bnb_fees.items():
            if date in bnb_prices:
                bnb_fees_in_usdt += bnb_amount * bnb_prices[date]
        
        # 总手续费 (USDT)
        total_fees_usdt = fee_data["usdt_fees"] + bnb_fees_in_usdt
        
        return {
            "symbol": symbol,
            "start_time": datetime.fromtimestamp(start_time / 1000).strftime("%Y-%m-%d %H:%M"),
            "end_time": datetime.fromtimestamp(end_time / 1000).strftime("%Y-%m-%d %H:%M"),
            "total_trades": fee_data["total_trades"],
            "usdt_fees": fee_data["usdt_fees"],
            "bnb_fees": fee_data["bnb_fees"],
            "bnb_prices": bnb_prices,
            "bnb_fees_in_usdt": bnb_fees_in_usdt,
            "total_fees_usdt": total_fees_usdt
        }
