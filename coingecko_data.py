#!/usr/bin/env python3
"""
MÓDULO DE DADOS COINGECKO
Busca dados OHLC para backtest e forward testing
"""

import requests
import pandas as pd
from datetime import datetime, timezone

class CoinGeckoData:
    """Busca dados históricos da CoinGecko"""
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def get_ohlc_days(self, coin_id, days, vs_currency="usd"):
        """
        Obtém dados OHLC para múltiplos dias
        days=1 → 1m | days=7 → 5m | days>7 → 15m
        """
        url = f"{self.BASE_URL}/coins/{coin_id}/ohlc"
        params = {
            'vs_currency': vs_currency,
            'days': days
        }
        
        print(f"📥 Baixando {days} dias de dados {coin_id.upper()}/USD...")
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                raise ValueError("Nenhum dado retornado")
            
            # Converte para DataFrame
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # Volume estimado
            df['volume'] = ((df['high'] - df['low']) / df['close'] * 100000).clip(1000, 500000)
            
            print(f"✅ Dados carregados: {len(df)} candles")
            return df
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro na API CoinGecko: {e}")
            raise
