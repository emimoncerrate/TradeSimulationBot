# Trade Modal Update Summary

## Changes Made

Updated the trade entry modal in `ui/trade_widget.py` to match the new interactive design specification.

### Key Changes:

1. **Modal Callback ID**: Changed from `trade_modal` to `stock_trade_modal_interactive`

2. **Modal Title & Submit**: 
   - Title: "Place Trade"
   - Submit button: "Execute Trade"

3. **Updated Input Fields**:

   - **Stock Symbol** (`trade_symbol_block`):
     - Default value: "TSLA"
     - Action ID: `symbol_input`
   
   - **Current Price Display** (`current_price_display`):
     - Shows real-time stock price when available
     - Fallback: $150.00
   
   - **Trade Action** (`trade_side_block`):
     - Radio buttons for Buy/Sell
     - Action ID: `trade_side_radio`
     - Default: Buy
   
   - **Quantity** (`qty_shares_block`):
     - Number input (integers only)
     - Action ID: `shares_input`
     - **Dispatch actions**: Triggers on character entry and enter press
     - Hint: "Changes here trigger an automatic GMV calculation."
   
   - **GMV - Gross Market Value** (`gmv_block`):
     - Number input (decimals allowed)
     - Action ID: `gmv_input`
     - **Dispatch actions**: Triggers on character entry and enter press
     - Hint: "Changes here trigger an automatic Shares calculation."
     - Auto-calculated from quantity × price
   
   - **Order Type** (`order_type_block`):
     - Dropdown select
     - Action ID: `order_type_select`
     - Options: Market, Limit, Stop, Stop Limit
   
   - **Limit Price** (`limit_price_block`):
     - Number input (decimals allowed)
     - Action ID: `limit_price_input`
     - **Optional field**
     - Hint: "Only required for Limit or Stop Limit order types."

### Interactive Features:

- **Real-time GMV/Shares Calculation**: 
  - Changing shares automatically updates GMV
  - Changing GMV automatically updates shares
  - Uses `dispatch_action_config` with `on_character_entered` trigger

- **Dynamic Price Display**: 
  - Shows current market price when available
  - Updates based on market data context

### Files Modified:

- `ui/trade_widget.py` - Updated `_build_trade_input_section()` method (lines 438-687)
- `ui/trade_widget.py` - Updated modal creation in `create_trade_modal()` (lines 179-202)

### Next Steps:

To handle the interactive dispatch actions, you'll need to register action handlers in `listeners/actions.py` for:
- `shares_input` - Handle quantity changes and update GMV
- `gmv_input` - Handle GMV changes and update shares

Example handler structure:
```python
@app.action("shares_input")
def handle_shares_input(ack, body, client):
    ack()
    # Calculate GMV and update modal
    
@app.action("gmv_input")
def handle_gmv_input(ack, body, client):
    ack()
    # Calculate shares and update modal
```

## Testing:

No linter errors detected. The modal structure follows Slack Block Kit specifications.
