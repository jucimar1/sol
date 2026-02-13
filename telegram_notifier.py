#!/usr/bin/env python3
"""
NOTIFICADOR TELEGRAM PARA FORWARD TESTING
Envia alertas de trades, divergências e relatórios
"""

import requests
import json
from datetime import datetime

class TelegramNotifier:
    def __init__(self):
        self.token = None
        self.chat_id = None
        self.base_url = None
    
    def set_credentials(self, token, chat_id):
        """Configura credenciais Telegram"""
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
    
    def send_message(self, text, parse_mode='Markdown'):
        """Envia mensagem básica"""
        if not self.token or not self.chat_id:
            return
        
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        
        try:
            response = requests.post(url, json=data, timeout=10)
            return response.json()
        except Exception as e:
            print(f"Erro ao enviar Telegram: {e}")
            return None
    
    def send_trade_signal(self, side, price, indicators, capital):
        """Envia alerta de sinal de trade"""
        emoji = "🟢" if side == "LONG" else "🔴"
        direction = "COMPRA" if side == "LONG" else "VENDA"
        
        message = (
            f"{emoji} *SINAL {direction} - FORWARD TESTING*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Preço: ${price:.4f}\n"
            f"⏰ Horário: {datetime.now().strftime('%H:%M:%S')}\n"
            f"📊 Capital: ${capital:.2f}\n\n"
            f"✅ Condições:\n"
            f"   • MACD: {'Bullish' if side == 'LONG' else 'Bearish'}\n"
            f"   • EMA6: {'Preço acima' if side == 'LONG' else 'Preço abaixo'}\n"
            f"   • Bollinger: Expansão\n"
            f"   • Volume: {indicators['volume_usdt']:.0f} USDT\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        
        return self.send_message(message)
    
    def send_trade_close(self, side, pnl_pct, reason, capital):
        """Envia alerta de fechamento de trade"""
        emoji = "✅" if pnl_pct > 0 else "❌"
        performance = "Lucro" if pnl_pct > 0 else "Prejuízo"
        
        reason_text = {
            'STOP_LOSS': 'Stop-Loss',
            'TAKE_PROFIT': 'Take-Profit',
            'TRAILING_STOP': 'Trailing Stop'
        }.get(reason, reason)
        
        message = (
            f"{emoji} *FECHAMENTO - {performance} {abs(pnl_pct):.2f}%*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Motivo: {reason_text}\n"
            f"💰 PNL: {pnl_pct:+.2f}%\n"
            f"📈 Capital: ${capital:.2f}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        
        return self.send_message(message)
    
    def send_divergence_alert(self, divergence):
        """Envia alerta de divergência detectada"""
        emoji = "⚠️" if divergence['severity'] == 'MEDIUM' else "🚨"
        
        message = (
            f"{emoji} *DIVERGÊNCIA DETECTADA*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📉 Tipo: {divergence['type']}\n"
            f"📊 Indicador: {divergence['indicator']}\n"
            f"💰 Preço: ${divergence['price']:.4f}\n"
            f"⏰ Horário: {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"🔍 Detalhes:\n"
            f"   • {divergence['price_action']}\n"
            f"   • {divergence['indicator_action']}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        
        return self.send_message(message)
    
    def send_backtest_report(self, results):
        """Envia relatório completo de backtest"""
        stats = results.get('statistics', {})
        
        message = (
            f"📊 *RELATÓRIO FORWARD TESTING - SOL/USDT*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 Resultados:\n"
            f"   • Trades: {stats.get('total_trades', 0)}\n"
            f"   • Win Rate: {stats.get('win_rate', 0):.1f}%\n"
            f"   • Profit Factor: {stats.get('profit_factor', 0):.2f}\n"
            f"   • Expectativa: {stats.get('expectancy', 0):+.2f}%\n"
            f"   • Retorno Total: {stats.get('total_return', 0):+.2f}%\n"
            f"   • Max Drawdown: {stats.get('max_drawdown', 0):.2f}%\n\n"
            f"⚠️  Divergências:\n"
            f"   • Total: {stats.get('divergence_count', 0)}\n"
            f"   • Taxa: {stats.get('divergence_rate', 0):.1f}%\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        
        return self.send_message(message)
