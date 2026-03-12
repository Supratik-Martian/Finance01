from dataclasses import dataclass
from datetime import datetime, time
from .strategies import Signal, TradeSignal

@dataclass
class RiskConfig:
    max_capital_per_trade_pct: float = 0.05   # 5% of capital per trade
    max_loss_per_trade_pct: float = 0.01       # 1% risk per trade
    max_daily_loss_pct: float = 0.03           # 3% max daily loss → stop
    max_open_positions: int = 3
    max_correlation: float = 0.7               # avoid correlated bets
    min_risk_reward: float = 1.5
    trailing_stop_atr_mult: float = 2.0
    max_trades_per_day: int = 10
    no_trade_after: time = time(14, 30)        # no new trades after 2:30
    force_exit_by: time = time(15, 10)         # exit all by 3:10

class RiskManager:
    def __init__(self, capital: float, config: RiskConfig = None):
        self.capital = capital
        self.initial_capital = capital
        self.config = config or RiskConfig()
        self.daily_pnl = 0.0
        self.trades_today = 0
        self.open_positions = {}
        self.trade_log = []
    
    def can_trade(self) -> tuple[bool, str]:
        """Check if we're allowed to take a new trade"""
        now = datetime.now().time()
        
        # Daily loss limit
        if self.daily_pnl <= -(self.initial_capital * self.config.max_daily_loss_pct):
            return False, f"Daily loss limit hit: ₹{self.daily_pnl:.2f}"
        
        # Max trades
        if self.trades_today >= self.config.max_trades_per_day:
            return False, f"Max trades ({self.config.max_trades_per_day}) reached"
        
        # Time restriction
        if now >= self.config.no_trade_after:
            return False, f"No new trades after {self.config.no_trade_after}"
        
        # Max positions
        if len(self.open_positions) >= self.config.max_open_positions:
            return False, f"Max open positions ({self.config.max_open_positions}) reached"
        
        return True, "OK"
    
    def calculate_position_size(self, signal: TradeSignal) -> int:
        """Kelly-criterion inspired position sizing"""
        risk_per_share = abs(signal.entry_price - signal.stop_loss)
        if risk_per_share == 0:
            return 0
        
        # Max loss allowed for this trade
        max_loss = self.capital * self.config.max_loss_per_trade_pct
        
        # Max capital for this trade
        max_capital = self.capital * self.config.max_capital_per_trade_pct
        
        # Position size based on risk
        qty_by_risk = int(max_loss / risk_per_share)
        
        # Position size based on capital
        qty_by_capital = int(max_capital / signal.entry_price)
        
        # Take the smaller
        qty = min(qty_by_risk, qty_by_capital)
        
        # Adjust by confidence
        qty = int(qty * signal.confidence)
        
        return max(qty, 0)
    
    def validate_signal(self, signal: TradeSignal) -> tuple[bool, str]:
        """Validate risk/reward and other criteria"""
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.target - signal.entry_price)
        
        if risk == 0:
            return False, "Zero risk (SL = entry)"
        
        rr_ratio = reward / risk
        if rr_ratio < self.config.min_risk_reward:
            return False, f"R:R too low: {rr_ratio:.2f} < {self.config.min_risk_reward}"
        
        if signal.confidence < 0.5:
            return False, f"Confidence too low: {signal.confidence:.2f}"
        
        # Check if already in same stock
        if signal.symbol in self.open_positions:
            return False, f"Already in position: {signal.symbol}"
        
        return True, "OK"
    
    def update_trailing_stop(self, symbol, current_price, atr):
        """Dynamic trailing stop loss"""
        if symbol not in self.open_positions:
            return
        
        pos = self.open_positions[symbol]
        trailing_distance = atr * self.config.trailing_stop_atr_mult
        
        if pos['side'] == 'BUY':
            new_sl = current_price - trailing_distance
            if new_sl > pos['stop_loss']:
                pos['stop_loss'] = new_sl
                print(f"  Trailing SL updated for {symbol}: ₹{new_sl:.2f}")
        else:
            new_sl = current_price + trailing_distance
            if new_sl < pos['stop_loss']:
                pos['stop_loss'] = new_sl
                print(f"  Trailing SL updated for {symbol}: ₹{new_sl:.2f}")
    
    def record_trade(self, signal, qty, entry_price, exit_price=None):
        self.trades_today += 1
        trade = {
            'timestamp': datetime.now(),
            'symbol': signal.symbol,
            'side': signal.signal.name,
            'qty': qty,
            'entry': entry_price,
            'exit': exit_price,
            'reason': signal.reason,
        }
        if exit_price:
            pnl = (exit_price - entry_price) * qty
            if signal.signal == Signal.SELL:
                pnl = -pnl
            trade['pnl'] = pnl
        self.trade_log.append(trade)

    def close_position_record(self, symbol, exit_price):
        if symbol not in self.open_positions:
            return
            
        pos = self.open_positions[symbol]
        qty = pos['qty']
        entry_price = pos['entry']
        
        gross_pnl = (exit_price - entry_price) * qty
        if pos['side'] == 'SELL':
            gross_pnl = -gross_pnl
            
        # Calculate standard Intraday costs (Zerodha style)
        turnover = (entry_price + exit_price) * qty
        brokerage = 40.0  # ₹40 round trip max
        stt_etc = turnover * 0.0003  # ~0.03% for STT + Exchange + GST
        total_costs = brokerage + stt_etc
        
        net_pnl = gross_pnl - total_costs
            
        self.daily_pnl += net_pnl
        self.capital += net_pnl
        
        # update trade log
        for trade in self.trade_log:
            if trade['symbol'] == symbol and trade['exit'] is None:
                trade['exit'] = exit_price
                trade['pnl'] = net_pnl
                trade['gross_pnl'] = gross_pnl
                trade['costs'] = total_costs
                break
                
    def should_force_exit(self) -> bool:
        return datetime.now().time() >= self.config.force_exit_by
