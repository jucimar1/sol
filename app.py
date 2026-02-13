#!/usr/bin/env python3
"""
SISTEMA COMPLETO DE FORWARD TESTING - SOL/USDT
✅ Interface Web HTML/JavaScript
✅ Análise de Divergência entre Indicadores
✅ Notificações Telegram
✅ Dashboard de Resultados em Tempo Real
✅ Configuração via Interface Gráfica
"""

from flask import Flask, render_template, jsonify, request
import threading
import json
import os
from datetime import datetime, timedelta
from forward_tester import ForwardTester
from divergence_analyzer import DivergenceAnalyzer
from telegram_notifier import TelegramNotifier

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'  # Mude para produção

# Configurações globais
CONFIG_FILE = 'config.json'
RESULTS_FILE = 'results.json'

# Inicializa módulos
forward_tester = None
divergence_analyzer = DivergenceAnalyzer()
telegram_notifier = TelegramNotifier()

# Carrega ou cria configuração
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        'timeframe': '15m',
        'days': 15,
        'position_size': 40.0,
        'fees': 0.0015,
        'telegram_token': '',
        'telegram_chat_id': '',
        'trading_hours': [[7, 10], [12, 16]],
        'volume_min': 75000,
        'stop_loss_pct': 0.8,
        'take_profit_pct': 1.5,
        'enable_telegram': False,
        'auto_pause_after_losses': 2
    }

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def load_results():
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, 'r') as f:
            return json.load(f)
    return {
        'trades': [],
        'equity_curve': [],
        'divergences': [],
        'statistics': {},
        'last_update': None
    }

def save_results(results):
    with open(RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2, default=str)

@app.route('/')
def index():
    """Página principal com dashboard"""
    config = load_config()
    results = load_results()
    return render_template('index.html', config=config, results=results)

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """API para configuração"""
    if request.method == 'POST':
        config = request.json
        save_config(config)
        return jsonify({'status': 'success', 'message': 'Configuração salva'})
    return jsonify(load_config())

@app.route('/api/run-backtest', methods=['POST'])
def run_backtest():
    """Executa backtest com configuração atual"""
    config = load_config()
    
    try:
        # Atualiza configuração com dados do request
        if 'timeframe' in request.json:
            config.update(request.json)
            save_config(config)
        
        # Importa dados e executa backtest
        from coingecko_data import CoinGeckoData
        cg = CoinGeckoData()
        days = config['days']
        
        # Mapeia timeframe para dias
        timeframe_days = {
            '1m': 1,
            '5m': 7,
            '15m': days
        }
        
        actual_days = timeframe_days.get(config['timeframe'], days)
        df = cg.get_ohlc_days("solana", actual_days)
        
        # Executa forward test
        global forward_tester
        forward_tester = ForwardTester(
            position_size=config['position_size'],
            fees=config['fees'],
            stop_loss=config['stop_loss_pct'],
            take_profit=config['take_profit_pct'],
            volume_min=config['volume_min'],
            trading_hours=config['trading_hours']
        )
        
        results = forward_tester.run(df, days_to_test=days)
        
        # Analisa divergências
        divergences = divergence_analyzer.analyze(df, results['trades_df'] if 'trades_df' in results else None)
        
        # Prepara resultados
        output = {
            'trades': results.get('trades_df', pd.DataFrame()).to_dict('records') if 'trades_df' in results else [],
            'equity_curve': results.get('equity_curve', []),
            'divergences': divergences,
            'statistics': {
                'total_trades': results.get('trades', 0),
                'win_rate': results.get('win_rate', 0),
                'profit_factor': results.get('profit_factor', 0),
                'expectancy': results.get('expectancy', 0),
                'max_drawdown': results.get('max_drawdown_pct', 0),
                'total_return': results.get('total_return_pct', 0),
                'divergence_count': len(divergences),
                'divergence_rate': (len(divergences) / results.get('trades', 1) * 100) if results.get('trades', 0) > 0 else 0
            },
            'last_update': datetime.now().isoformat(),
            'config': config
        }
        
        save_results(output)
        
        # Envia notificação Telegram se habilitado
        if config.get('enable_telegram') and config.get('telegram_token'):
            telegram_notifier.set_credentials(
                config['telegram_token'],
                config['telegram_chat_id']
            )
            telegram_notifier.send_backtest_report(output)
        
        return jsonify(output)
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/results')
def api_results():
    """Retorna resultados salvos"""
    return jsonify(load_results())

@app.route('/api/start-forward-test', methods=['POST'])
def start_forward_test():
    """Inicia forward testing em tempo real (simulado)"""
    config = load_config()
    
    def run_test():
        # Simula forward testing com dados recentes
        from coingecko_data import CoinGeckoData
        cg = CoinGeckoData()
        df = cg.get_ohlc_days("solana", 1)  # Últimas 24h
        
        tester = ForwardTester(
            position_size=config['position_size'],
            fees=config['fees'],
            stop_loss=config['stop_loss_pct'],
            take_profit=config['take_profit_pct'],
            volume_min=config['volume_min'],
            trading_hours=config['trading_hours'],
            enable_telegram=config.get('enable_telegram', False),
            telegram_token=config.get('telegram_token', ''),
            telegram_chat_id=config.get('telegram_chat_id', '')
        )
        
        results = tester.run(df, simulate_real_time=True)
        save_results(results)
    
    # Executa em thread separada
    thread = threading.Thread(target=run_test)
    thread.start()
    
    return jsonify({'status': 'started', 'message': 'Forward testing iniciado em background'})

@app.route('/api/divergence-analysis')
def divergence_analysis():
    """Retorna análise detalhada de divergências"""
    results = load_results()
    divergences = results.get('divergences', [])
    
    if not divergences:
        return jsonify({'error': 'Nenhuma divergência registrada'})
    
    # Análise estatística
    indicator_counts = {}
    for div in divergences:
        indicator = div.get('indicator', 'unknown')
        indicator_counts[indicator] = indicator_counts.get(indicator, 0) + 1
    
    # Taxa de erro por indicador
    error_rates = {}
    for indicator, count in indicator_counts.items():
        # Simula cálculo de taxa de erro (em produção, usar dados reais)
        error_rates[indicator] = {
            'count': count,
            'error_rate': round(min(40 + count * 2, 85), 1),  # Simulação
            'impact': 'high' if count > 5 else 'medium' if count > 2 else 'low'
        }
    
    return jsonify({
        'total_divergences': len(divergences),
        'by_indicator': error_rates,
        'most_problematic': max(error_rates.items(), key=lambda x: x[1]['count'])[0] if error_rates else 'none',
        'recommendation': 'Ajustar sensibilidade do MACD' if error_rates.get('MACD', {}).get('count', 0) > 5 else 'Estratégia estável'
    })

if __name__ == '__main__':
    # Cria diretórios necessários
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    print("="*80)
    print("🚀 SISTEMA DE FORWARD TESTING - SOL/USDT")
    print("="*80)
    print("\n✅ Servidor iniciado: http://localhost:5000")
    print("   • Interface web com dashboard completo")
    print("   • Análise de divergência entre indicadores")
    print("   • Notificações Telegram configuráveis")
    print("   • Gráficos interativos com Chart.js")
    print("\n💡 Dica: Abra o navegador e acesse http://localhost:5000")
    print("="*80)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
