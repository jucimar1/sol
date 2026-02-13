#!/usr/bin/env python3
"""
ANALISADOR DE DIVERGÊNCIA AVANÇADO
Identifica divergências entre preço e indicadores (MACD, RSI, Volume)
Calcula taxa de erro e impacto nas operações
"""

import pandas as pd
import numpy as np

class DivergenceAnalyzer:
    def __init__(self):
        self.divergences = []
    
    def detect_rsi_divergence(self, df, window=5):
        """Detecta divergência RSI (clássica e oculta)"""
        divergences = []
        
        for i in range(window, len(df) - window):
            # Verifica topos
            if (df['high'].iloc[i] > df['high'].iloc[i-window:i].max() and
                df['high'].iloc[i] > df['high'].iloc[i+1:i+window+1].max()):
                
                # Preço fez topo mais alto
                price_high = df['high'].iloc[i]
                prev_high_idx = df['high'].iloc[i-window:i].idxmax()
                prev_price_high = df['high'].loc[prev_high_idx]
                
                if price_high > prev_price_high:
                    # Verifica RSI
                    rsi_current = df['rsi'].iloc[i]
                    rsi_prev = df['rsi'].loc[prev_high_idx]
                    
                    if rsi_current < rsi_prev - 5:  # RSI divergente
                        divergences.append({
                            'timestamp': df['timestamp'].iloc[i].isoformat(),
                            'type': 'BEARISH',
                            'indicator': 'RSI',
                            'price_action': 'Topo mais alto',
                            'indicator_action': 'Topo mais baixo',
                            'severity': 'HIGH' if rsi_current < 50 else 'MEDIUM',
                            'price': df['close'].iloc[i]
                        })
            
            # Verifica fundos
            if (df['low'].iloc[i] < df['low'].iloc[i-window:i].min() and
                df['low'].iloc[i] < df['low'].iloc[i+1:i+window+1].min()):
                
                price_low = df['low'].iloc[i]
                prev_low_idx = df['low'].iloc[i-window:i].idxmin()
                prev_price_low = df['low'].loc[prev_low_idx]
                
                if price_low < prev_price_low:
                    rsi_current = df['rsi'].iloc[i]
                    rsi_prev = df['rsi'].loc[prev_low_idx]
                    
                    if rsi_current > rsi_prev + 5:  # RSI divergente
                        divergences.append({
                            'timestamp': df['timestamp'].iloc[i].isoformat(),
                            'type': 'BULLISH',
                            'indicator': 'RSI',
                            'price_action': 'Fundo mais baixo',
                            'indicator_action': 'Fundo mais alto',
                            'severity': 'HIGH' if rsi_current > 50 else 'MEDIUM',
                            'price': df['close'].iloc[i]
                        })
        
        return divergences
    
    def detect_macd_divergence(self, df, window=5):
        """Detecta divergência MACD"""
        divergences = []
        
        for i in range(window, len(df) - window):
            # Topos MACD
            if (df['macd'].iloc[i] > df['macd'].iloc[i-window:i].max() and
                df['macd'].iloc[i] > df['macd'].iloc[i+1:i+window+1].max()):
                
                price_high = df['high'].iloc[i]
                prev_high_idx = df['high'].iloc[i-window:i].idxmax()
                prev_price_high = df['high'].loc[prev_high_idx]
                
                if price_high < prev_price_high - (prev_price_high * 0.005):  # Preço não confirma
                    divergences.append({
                        'timestamp': df['timestamp'].iloc[i].isoformat(),
                        'type': 'BEARISH',
                        'indicator': 'MACD',
                        'price_action': 'Preço não confirma topo MACD',
                        'indicator_action': 'MACD topo mais alto',
                        'severity': 'HIGH',
                        'price': df['close'].iloc[i]
                    })
        
        return divergences
    
    def detect_volume_divergence(self, df, window=10):
        """Detecta divergência de volume (volume decrescente em tendência)"""
        divergences = []
        
        for i in range(window, len(df)):
            # Volume decrescente em tendência de alta
            if df['ema7'].iloc[i] > df['ema21'].iloc[i]:  # Tendência alta
                recent_volume = df['volume_usdt'].iloc[i-window:i].mean()
                current_volume = df['volume_usdt'].iloc[i]
                
                if current_volume < recent_volume * 0.7:  # Volume 30% menor
                    divergences.append({
                        'timestamp': df['timestamp'].iloc[i].isoformat(),
                        'type': 'WARNING',
                        'indicator': 'Volume',
                        'price_action': 'Tendência alta com volume decrescente',
                        'indicator_action': 'Volume 30% abaixo da média',
                        'severity': 'MEDIUM',
                        'price': df['close'].iloc[i]
                    })
        
        return divergences
    
    def analyze(self, df, trades_df=None):
        """Análise completa de divergências"""
        all_divergences = []
        
        # Detecta divergências
        rsi_divs = self.detect_rsi_divergence(df)
        macd_divs = self.detect_macd_divergence(df)
        volume_divs = self.detect_volume_divergence(df)
        
        all_divergences.extend(rsi_divs)
        all_divergences.extend(macd_divs)
        all_divergences.extend(volume_divs)
        
        # Correlaciona com trades (se disponível)
        if trades_df is not None and len(all_divergences) > 0:
            for div in all_divergences:
                div_time = pd.to_datetime(div['timestamp'])
                
                # Verifica se divergência impactou algum trade
                for _, trade in trades_df.iterrows():
                    entry_time = pd.to_datetime(trade['entry_time'])
                    exit_time = pd.to_datetime(trade['exit_time'])
                    
                    if entry_time <= div_time <= exit_time:
                        div['impacted_trade'] = True
                        div['trade_side'] = trade['side']
                        div['trade_result'] = 'WIN' if trade['pnl_pct'] > 0 else 'LOSS'
                        break
        
        # Ordena por timestamp
        all_divergences.sort(key=lambda x: x['timestamp'])
        
        return all_divergences
    
    def calculate_error_rates(self, divergences, trades_df):
        """Calcula taxa de erro por indicador"""
        if not divergences or trades_df is None:
            return {}
        
        indicator_stats = {}
        
        for div in divergences:
            indicator = div['indicator']
            if indicator not in indicator_stats:
                indicator_stats[indicator] = {'count': 0, 'impacted_losses': 0}
            
            indicator_stats[indicator]['count'] += 1
            
            if div.get('impacted_trade') and div.get('trade_result') == 'LOSS':
                indicator_stats[indicator]['impacted_losses'] += 1
        
        # Calcula taxas
        for indicator, stats in indicator_stats.items():
            total = stats['count']
            losses = stats['impacted_losses']
            stats['error_rate'] = (losses / total * 100) if total > 0 else 0
            stats['impact_level'] = 'HIGH' if stats['error_rate'] > 60 else 'MEDIUM' if stats['error_rate'] > 40 else 'LOW'
        
        return indicator_stats
