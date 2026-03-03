"""Main entry point"""
import argparse
import logging
from datetime import datetime
from typing import Tuple

from .config import Config
from .binance_client import BinanceClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_time(time_str: str) -> int:
    """Parse time string to milliseconds timestamp"""
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(time_str, fmt)
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue
    
    raise ValueError(f"Invalid time format: {time_str}")


def calculate_rebate(total_fees: float, rebate_rate: float = 0.4) -> float:
    """计算返佣金额"""
    return total_fees * rebate_rate


def calculate_share(rebate: float, share_rate: float = 0.3) -> float:
    """计算每人分成"""
    return rebate * share_rate


def process_single_api(
    api_key: str,
    api_secret: str,
    symbol: str,
    start_time: str,
    end_time: str,
    rebate_rate: float,
    share_rate: float
) -> Tuple[str, dict]:
    """
    处理单个 API 的手续费计算
    
    Returns:
        (api_name, result_dict)
    """
    client = BinanceClient(api_key, api_secret)
    
    # 解析时间
    start_ms = parse_time(start_time)
    end_ms = parse_time(end_time)
    
    logger.info(f"Fetching trades from {start_time} to {end_time}...")
    
    # 计算手续费
    result = client.calculate_weighted_fees(symbol, start_ms, end_ms)
    
    # 计算返佣
    result["rebate"] = calculate_rebate(result["total_fees_usdt"], rebate_rate)
    result["share_per_person"] = calculate_share(result["rebate"], share_rate)
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Binance ICP-USDT Fee Calculator")
    
    # API 配置
    parser.add_argument("--api-key", "-k", help="Binance API Key")
    parser.add_argument("--api-secret", "-s", help="Binance API Secret")
    
    # 第二组 API (可选)
    parser.add_argument("--api-key-2", "-k2", help="Binance API Key (Second)")
    parser.add_argument("--api-secret-2", "-s2", help="Binance API Secret (Second)")
    
    # 时间范围
    parser.add_argument("--start", required=True, help="Start time (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End time (YYYY-MM-DD)")
    
    # 交易对
    parser.add_argument("--symbol", default="ICPUSDT", help="Trading pair (default: ICPUSDT)")
    parser.add_argument("--symbol-2", default="", help="Trading pair for API 2 (e.g., ICPUSDC)")
    
    # 返佣比例
    parser.add_argument("--rebate-rate", type=float, default=0.4, help="Rebate rate (default: 0.4)")
    parser.add_argument("--share-rate", type=float, default=0.3, help="Share rate (default: 0.3)")
    
    # 配置文件
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    
    args = parser.parse_args()
    
    # 加载配置
    config = Config(args.config)
    
    # 获取 API 密钥
    api1_key = args.api_key or config.api1.get("api_key", "")
    api1_secret = args.api_secret or config.api1.get("api_secret", "")
    
    api2_key = args.api_key_2 or config.api2.get("api_key", "")
    api2_secret = args.api_secret_2 or config.api2.get("api_secret", "")
    
    # 使用配置文件中的时间 (如果命令行没有指定)
    start_time = args.start or config.get("start_time") or ""
    end_time = args.end or config.get("end_time") or ""
    
    if not start_time or not end_time:
        parser.error("Start and end time are required")
    
    # 使用配置中的比例
    rebate_rate = args.rebate_rate
    share_rate = args.share_rate
    
    # 交易对 (支持不同交易对)
    symbol1 = args.symbol
    symbol2 = args.symbol_2 or args.symbol  # 如果没指定就用第一个
    
    results = []
    
    # 处理 API1
    if api1_key and api1_secret:
        logger.info("=" * 50)
        logger.info("Processing API 1...")
        logger.info("=" * 50)
        
        result1 = process_single_api(
            api1_key, api1_secret, symbol, start_time, end_time,
            rebate_rate, share_rate
        )
        results.append(("API 1", result1))
    
    # 处理 API2
    if api2_key and api2_secret:
        logger.info("=" * 50)
        logger.info("Processing API 2...")
        logger.info("=" * 50)
        
        result2 = process_single_api(
            api2_key, api2_secret, symbol2, start_time, end_time,
            rebate_rate, share_rate
        )
        results.append(("API 2", result2))
    
    # 打印汇总结果
    logger.info("=" * 60)
    logger.info("FINAL SUMMARY")
    logger.info("=" * 60)
    
    total_fees = 0.0
    total_rebate = 0.0
    total_share = 0.0
    
    for name, result in results:
        print(f"\n--- {name} ---")
        print(f"  交易对: {result['symbol']}")
        print(f"  时间范围: {result['start_time']} ~ {result['end_time']}")
        print(f"  总交易笔数: {result['total_trades']}")
        print(f"  USDT 手续费: ${result['usdt_fees']:.4f}")
        print(f"  BNB 手续费: {result['bnb_fees']:.6f} BNB")
        print(f"  BNB 折合 USDT: ${result['bnb_fees_in_usdt']:.4f}")
        print(f"  总手续费 (USDT): ${result['total_fees_usdt']:.4f}")
        print(f"  返佣 (40%): ${result['rebate']:.4f}")
        print(f"  每人分成 (30%): ${result['share_per_person']:.4f}")
        
        total_fees += result['total_fees_usdt']
        total_rebate += result['rebate']
        total_share += result['share_per_person']
    
    if len(results) > 1:
        print(f"\n=== TOTAL (All APIs) ===")
        print(f"  总手续费: ${total_fees:.4f}")
        print(f"  总返佣: ${total_rebate:.4f}")
        print(f"  每人总分成: ${total_share:.4f}")


if __name__ == "__main__":
    main()
