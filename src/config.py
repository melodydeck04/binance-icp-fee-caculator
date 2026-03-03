"""Configuration loader"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration manager"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        
        if self.config_path.exists():
            self._load_config()
        
        self._apply_env_overrides()
    
    def _load_config(self):
        """Load config from YAML"""
        with open(self.config_path, 'r') as f:
            self._config = yaml.safe_load(f) or {}
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides"""
        # API 1
        if api_key := os.getenv("BINANCE_API_KEY_1"):
            self._config.setdefault("binance", {}).setdefault("api1", {})["api_key"] = api_key
        if api_secret := os.getenv("BINANCE_API_SECRET_1"):
            self._config["binance"]["api1"]["api_secret"] = api_secret
        
        # API 2
        if api_key := os.getenv("BINANCE_API_KEY_2"):
            self._config["binance"]["api2"]["api_key"] = api_key
        if api_secret := os.getenv("BINANCE_API_SECRET_2"):
            self._config["binance"]["api2"]["api_secret"] = api_secret
    
    def get(self, key: str, default=None):
        """Get config value by dot notation"""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value
    
    @property
    def api1(self) -> Dict[str, str]:
        return self._config.get("binance", {}).get("api1", {})
    
    @property
    def api2(self) -> Dict[str, str]:
        return self._config.get("binance", {}).get("api2", {})
    
    @property
    def rebate_rate(self) -> float:
        return self.get("rebate.rebate_rate", 0.4)
    
    @property
    def share_rate(self) -> float:
        return self.get("rebate.share_rate", 0.3)
    
    @property
    def symbol(self) -> str:
        return self.get("symbol", "ICPUSDT")
