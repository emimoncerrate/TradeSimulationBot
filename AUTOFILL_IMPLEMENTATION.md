# Trade Modal Autofill Implementation

## Overview

Implemented real-time autofill functionality for the trade modal that automatically calculates and updates fields based on user input.

## Features Implemented

### 1. **Shares → GMV Auto-calculation**
When a user enters the number of shares, the GMV (Gross Market Value) is automatically calculated and displayed.

**Formula**: `GMV = Shares × Current Price`

**Handler**: `handle_shares_input` in `listeners/actions.py`
- Listens to: `shares_input` action
- Triggers on: Character entry and Enter press
- Calculates: GMV based on shares and current price
- Updates: `gmv_block` field in modal

### 2. **GMV → Shares Auto-calculation**
When a user enters a GMV amount, the number of shares is automatically calculated.

**Formula**: `Shares = GMV ÷ Current Price`

**Handler**: `handle_gmv_input` in `listeners/actions.py`
- Listens to: `gmv_input` action
- Triggers on: Character entry and Enter press
- Calculates: Shares based on GMV and current price
- Updates: `qty_shares_block` field in modal

### 3. **Symbol → Price Auto-fetch**
When a user enters a stock symbol and presses Enter, the current market price is fetched and displayed.

**Handler**: `handle_symbol_input` in `listeners/actions.py`
- Listens to: `symbol_input` action
- Triggers on: Enter press
- Fetches: Real-time market data for the symbol
- Updates: `current_price_display` block with current price

## Technical Implementation

### Dispatch Actions Configuration

All interactive inputs use Slack's `dispatch_action_config` to trigger actions in real-time:

```python
"dispatch_action_config": {
    "trigger_actions_on": [
        "on_enter_pressed",      # Symbol input
        "on_character_entered"   # Shares and GMV inputs
    ]
}
```

### Modal Update Flow

1. **User Input** → Dispatch action triggered
2. **Action Handler** → Receives input value
3. **Calculation** → Performs calculation using current modal state
4. **Modal Update** → Uses `client.views_update()` to refresh modal
5. **User Sees** → Updated field value instantly

### Files Modified

#### `ui/trade_widget.py` (Lines 440-687)
- Added dispatch config to `symbol_input`
- Configured `shares_input` with character-based dispatch
- Configured `gmv_input` with character-based dispatch

#### `listeners/actions.py` (Lines 1087-1273)
- Added `handle_shares_input()` - Auto-calculate GMV
- Added `handle_gmv_input()` - Auto-calculate shares
- Added `handle_symbol_input()` - Fetch market price
- Added `@app.view("stock_trade_modal_interactive")` - Handle new callback_id

## Usage Example

### Scenario 1: User Enters Shares
```
1. User types: 100 shares
2. Current price: $150.00
3. Auto-calculated GMV: $15,000.00
4. GMV field updates automatically
```

### Scenario 2: User Enters GMV
```
1. User types: $25,000.00 GMV
2. Current price: $150.00
3. Auto-calculated shares: 166
4. Shares field updates automatically
```

### Scenario 3: User Changes Symbol
```
1. User types: AAPL
2. Presses Enter
3. Fetches current AAPL price
4. Price display updates: $175.50
5. If shares were entered, GMV recalculates
```

## Error Handling

The implementation includes robust error handling:

- **Invalid Number Input**: Catches `ValueError` and `TypeError`
- **Division by Zero**: Catches `ZeroDivisionError` when price is 0
- **Market Data Fetch Failure**: Logs warning, doesn't crash modal
- **Missing Fields**: Gracefully handles missing price or values

## Price Extraction

The handlers intelligently extract the current price from the modal:

```python
# Extract price from display block
price_match = re.search(r'\$([0-9,.]+)', text)
if price_match:
    current_price = float(price_match.group(1).replace(',', ''))
```

## Benefits

1. **✅ Improved UX**: Users don't need to manually calculate GMV or shares
2. **✅ Faster Trade Entry**: Reduces cognitive load during trade execution
3. **✅ Error Reduction**: Automatic calculations eliminate manual calculation errors
4. **✅ Real-time Feedback**: Instant visual feedback as users type
5. **✅ Market Data Integration**: Automatically fetches current prices

## Testing Checklist

- [x] Shares → GMV calculation works
- [x] GMV → Shares calculation works
- [x] Symbol → Price fetch works
- [x] Handles invalid inputs gracefully
- [x] Handles missing price gracefully
- [x] No linter errors
- [x] Follows Slack Block Kit specifications

## Next Steps (Optional Enhancements)

1. **Add loading states** - Show spinner while fetching price
2. **Add validation messages** - Display inline validation errors
3. **Add price change indicator** - Show if price went up/down
4. **Add calculation preview** - Show formula being used
5. **Add decimal precision controls** - Allow users to set decimal places

## Modal Callback IDs

The modal now supports both callback IDs:
- `trade_modal` (legacy)
- `stock_trade_modal_interactive` (new)

Both are handled by the same submission handler for backward compatibility.

## Logging

All autofill actions are logged for debugging and monitoring:

```python
logger.info(f"Updated GMV to {gmv} based on {shares} shares at ${current_price}")
logger.info(f"Updated shares to {shares} based on GMV ${gmv} at ${current_price}")
logger.info(f"Updated price for {symbol}: ${market_quote.current_price:.2f}")
```

## Performance Considerations

- **Throttling**: Dispatch actions are handled by Slack's infrastructure
- **Network Calls**: Only symbol lookup makes external API calls
- **Calculation Speed**: GMV/shares calculations are instant (no I/O)
- **Modal Updates**: Uses Slack's optimized `views_update` API

---

**Implementation Date**: October 14, 2025
**Status**: ✅ Complete and Tested
**No Breaking Changes**: Fully backward compatible

