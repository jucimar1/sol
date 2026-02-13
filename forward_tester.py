#!/usr/bin/env python3
"""
MÓDULO DE FORWARD TESTING AVANÇADO
Simula operações reais com gestão de risco e notificações
"""

import pandas as pd
import numpy as np
from datetime import datetime
import time
from telegram_notifier import TelegramNotifier

class ForwardTester:
    def __init__(self, position_size=40.0, fees=0.0015, stop_loss=0.8, 
                 take_profit=1.5, volume_min=75000, trading_hours=None,
                 enable_telegram=False, telegram_token='', telegram_chat_id=''):
        self.position_size = position_size
        self.fees = fees
        self.stop_loss_pct = stop_loss / 100
        self.take_profit_pct = take_profit / 100
        self.volume_min = volume_min
        self.trading_hours = trading_hours or [[7, 10], [12, 16]]
        self.trades = []
        self.equity_curve = []
        self.enable_telegram = enable_telegram
        self.telegram = TelegramNotifier() if enable_telegram else None
        
        if enable_telegram and telegram_token:
            self.telegram.set_credentials(telegram_token, telegram_chat_id)
    
    def calculate_indicators(self, df):
        """Calcula indicadores técnicos"""
        df = df.copy()
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_diff'] = df['macd'] - df['macd_signal']
        df['macd_prev'] = df['macd_diff'].shift(1)
        df['macd_bullish'] = (df['macd_diff'] > 0) & (df['macd_prev'] <= 0)
        df['macd_bearish'] = (df['macd_diff'] < 0) & (df['macd_prev'] >= 0)
        
        # EMAs
        df['ema6'] = df['close'].ewm(span=6, adjust=False).mean()
        df['ema7'] = df['close'].ewm(span=7, adjust=False).mean()
        df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
        
        # Bollinger
        df['bb_mid'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_high'] = df['bb_mid'] + (df['bb_std'] * 2)
        df['bb_low'] = df['bb_mid'] - (df['bb_std'] * 2)
        df['bb_width'] = ((df['bb_high'] - df['bb_low']) / df['close']) * 100
        df['bb_width_prev'] = df['bb_width'].shift(1)
        df['bb_expanding'] = ((df['bb_width'] - df['bb_width_prev']) / 
                             df['bb_width_prev'].replace(0, np.nan) * 100) > 0.5
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, np.nan)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Volume
        df['volume_usdt'] = df['volume'] * df['close']
        
        return df.fillna(0)
    
    def is_trading_hour(self, timestamp):
        """Verifica horário de trading"""
        hour = timestamp.hour
        return any(start <= hour < end for start, end in self.trading_hours)
    
    def run(self, df, days_to_test=None, simulate_real_time=False):
        """Executa forward testing"""
        if days_to_test and len(df) > 100:
            cutoff = df['timestamp'].max() - pd.Timedelta(days=days_to_test)
            df = df[df['timestamp'] >= cutoff].copy()
        
        df = self.calculate_indicators(df)
        position = None
        entry_price = None
        entry_time = None
        
        # Capital inicial
        initial_price = df['close'].iloc[0]
        capital = self.position_size * initial_price
        self.equity_curve = [(df['timestamp'].iloc[0].isoformat(), capital)]
        
        print(f"🔬 Iniciando forward testing com {self.position_size} SOL...")
        
        for i in range(30, len(df)):
            row = df.iloc[i]
            ts = row['timestamp']
            price = row['close']
            
            # Filtros
            if not self.is_trading_hour(ts):
                continue
            if row['volume_usdt'] < self.volume_min:
                continue
            if not row['bb_expanding']:
                continue
            
            # Entrada
            if position is None:
                # LONG
                if row['macd_bullish'] and price > row['ema6'] and row['ema7'] > row['ema21']:
                    position = 'LONG'
                    entry_price = price * (1 + self.fees)
                    entry_time = ts
                    
                    if self.enable_telegram and self.telegram:
                        self.telegram.send_trade_signal('LONG', price, row, capital)
                    
                    if simulate_real_time:
                        time.sleep(0.1)  # Simula delay real
                    continue
                
                # SHORT
                if row['macd_bearish'] and price < row['ema6'] and row['ema7'] < row['ema21']:
                    position = 'SHORT'
                    entry_price = price * (1 - self.fees)
                    entry_time = ts
                    
                    if self.enable_telegram and self.telegram:
                        self.telegram.send_trade_signal('SHORT', price, row, capital)
                    
                    if simulate_real_time:
                        time.sleep(0.1)
                    continue
            
            # Saída
            if position:
                sl = entry_price * (1 - self.stop_loss_pct) if position == 'LONG' else entry_price * (1 + self.stop_loss_pct)
                tp = entry_price * (1 + self.take_profit_pct) if position == 'LONG' else entry_price * (1 - self.take_profit_pct)
                
                exit_trade = False
                exit_price = None
                reason = ""
                
                if position == 'LONG':
                    if price <= sl:
                        exit_trade = True
                        exit_price = price * (1 - self.fees)
                        reason = 'STOP_LOSS'
                    elif price >= tp:
                        exit_trade = True
                        exit_price = price * (1 - self.fees)
                        reason = 'TAKE_PROFIT'
                else:
                    if price >= sl:
                        exit_trade = True
                        exit_price = price * (1 + self.fees)
                        reason = 'STOP_LOSS'
                    elif price <= tp:
                        exit_trade = True
                        exit_price = price * (1 + self.fees)
                        reason = 'TAKE_PROFIT'
                
                if exit_trade:
                    pnl_usdt = (exit_price - entry_price) * self.position_size if position == 'LONG' else (entry_price - exit_price) * self.position_size
                    pnl_pct = (pnl_usdt / (entry_price * self.position_size)) * 100
                    capital += pnl_usdt
                    
                    self.trades.append({
                        'side': position,
                        'entry': entry_price,
                        'exit': exit_price,
                        'pnl_usdt': pnl_usdt,
                        'pnl_pct': pnl_pct,
                        'reason': reason,
                        'entry_time': entry_time.isoformat(),
                        'exit_time': ts.isoformat(),
                        'duration_min': (ts - entry_time).total_seconds() / 60
                    })
                    
                    self.equity_curve.append((ts.isoformat(), capital))
                    
                    if self.enable_telegram and self.telegram:
                        self.telegram.send_trade_close(position, pnl_pct, reason, capital)
                    
                    position = None
        
        return self.generate_report(capital, initial_price)
    
    def generate_report(self, final_capital, initial_price):
        """Gera relatório completo"""
        if not self.trades:
            return {'error': 'Nenhum trade executado'}
        
        df_trades = pd.DataFrame(self.trades)
        wins = len(df_trades[df_trades['pnl_pct'] > 0])
        losses = len(df_trades[df_trades['pnl_pct'] <= 0])
        
        equity = pd.Series([e[1] for e in self.equity_curve])
        rolling_max = equity.expanding().max()
        drawdown = (equity - rolling_max) / rolling_max * 100
        
        return {
            'trades': len(df_trades),
            'wins': wins,
            'losses': losses,
            'win_rate': (wins / len(df_trades) * 100) if len(df_trades) > 0 else 0,
            'avg_win': df_trades[df_trades['pnl_pct'] > 0]['pnl_pct'].mean() if wins > 0 else 0,
            'avg_loss': df_trades[df_trades['pnl_pct'] <= 0]['pnl_pct'].mean() if losses > 0 else 0,
            'profit_factor': abs(df_trades[df_trades['pnl_pct'] > 0]['pnl_pct'].sum() / 
                               df_trades[df_trades['pnl_pct'] <= 0]['pnl_pct'].sum()) if losses > 0 else 0,
            'expectancy': df_trades['pnl_pct'].mean(),
            'total_return_pct': ((final_capital - (self.position_size * initial_price)) / 
                               (self.position_size * initial_price)) * 100,
            'max_drawdown_pct': drawdown.min(),
            'final_capital': final_capital,
            'initial_capital': self.position_size * initial_price,
            'trades_df': df_trades,
            'equity_curve': self.equity_curve
        }
