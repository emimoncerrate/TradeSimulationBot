# Trade Modal Autofill Flow Diagram

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Slack Trade Modal                             │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Symbol Input: [TSLA_______________] (on_enter_pressed)   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Current Price: $150.00    ◄── Auto-updated               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Shares: [100__] (on_character_entered) ──┐               │  │
│  └──────────────────────────────────────────│───────────────┘  │
│                              │               │                   │
│                              │               │ triggers          │
│                              ▼               ▼                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ GMV: [$15,000.00] ◄── Auto-calculated                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              │ user can also edit               │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ GMV: [$25,000.00] (on_character_entered) ──┐             │  │
│  └──────────────────────────────────────────────│───────────┘  │
│                              │                  │                │
│                              │                  │ triggers       │
│                              ▼                  ▼                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Shares: [166____] ◄── Auto-calculated                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow Sequence

### Flow 1: User Enters Symbol

```
User Types Symbol → Enter Key
    ↓
handle_symbol_input()
    ↓
Extract symbol from modal state
    ↓
Call market_data_service.get_quote(symbol)
    ↓
Get current price from API
    ↓
Update current_price_display block
    ↓
Call client.views_update()
    ↓
Modal refreshes with new price
    ↓
User sees updated price
```

### Flow 2: User Enters Shares

```
User Types Shares (e.g., 100)
    ↓
handle_shares_input() [triggers on each character]
    ↓
Extract shares value from modal state
    ↓
Extract current price from display block
    ↓
Calculate: GMV = shares × price
    ↓
GMV = 100 × $150.00 = $15,000.00
    ↓
Update gmv_block with new value
    ↓
Call client.views_update()
    ↓
Modal refreshes with calculated GMV
    ↓
User sees GMV update in real-time
```

### Flow 3: User Enters GMV

```
User Types GMV (e.g., $25,000)
    ↓
handle_gmv_input() [triggers on each character]
    ↓
Extract GMV value from modal state
    ↓
Extract current price from display block
    ↓
Calculate: Shares = GMV ÷ price
    ↓
Shares = $25,000 ÷ $150.00 = 166.67 → 166 (rounded)
    ↓
Update qty_shares_block with new value
    ↓
Call client.views_update()
    ↓
Modal refreshes with calculated shares
    ↓
User sees shares update in real-time
```

## Component Interaction Diagram

```
┌────────────────────┐         ┌──────────────────────┐
│                    │         │                      │
│   Slack Modal      │────────▶│  Action Handlers     │
│   (User Input)     │ Dispatch│  (listeners/        │
│                    │  Action │   actions.py)        │
└────────────────────┘         └──────────┬───────────┘
                                          │
                                          │ Extract Values
                                          │ & Calculate
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
                    ▼                     ▼                     ▼
         ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
         │                  │  │                  │  │                  │
         │ handle_symbol_   │  │ handle_shares_   │  │ handle_gmv_      │
         │     input()      │  │     input()      │  │     input()      │
         │                  │  │                  │  │                  │
         └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
                  │                     │                     │
                  │                     │                     │
                  ▼                     ▼                     ▼
         ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
         │                  │  │                  │  │                  │
         │ Market Data API  │  │ Calculate GMV    │  │ Calculate Shares │
         │ (Finnhub)        │  │ shares × price   │  │ GMV ÷ price      │
         │                  │  │                  │  │                  │
         └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
                  │                     │                     │
                  └─────────────────────┼─────────────────────┘
                                        │
                                        │ Update Modal Blocks
                                        │
                                        ▼
                          ┌──────────────────────────┐
                          │                          │
                          │  client.views_update()   │
                          │  (Slack API)             │
                          │                          │
                          └────────────┬─────────────┘
                                       │
                                       │ Refresh Display
                                       │
                                       ▼
                          ┌──────────────────────────┐
                          │                          │
                          │  User Sees Updated       │
                          │  Modal with New Values   │
                          │                          │
                          └──────────────────────────┘
```

## State Management

### Modal State Structure

```json
{
  "view": {
    "id": "V12345",
    "callback_id": "stock_trade_modal_interactive",
    "state": {
      "values": {
        "trade_symbol_block": {
          "symbol_input": {
            "type": "plain_text_input",
            "value": "TSLA"
          }
        },
        "qty_shares_block": {
          "shares_input": {
            "type": "number_input",
            "value": "100"
          }
        },
        "gmv_block": {
          "gmv_input": {
            "type": "number_input",
            "value": "15000.00"
          }
        }
      }
    },
    "blocks": [
      {
        "block_id": "current_price_display",
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*Current Stock Price:* *$150.00*"
        }
      }
      // ... other blocks
    ]
  }
}
```

## Trigger Configuration

### Symbol Input
```json
{
  "dispatch_action_config": {
    "trigger_actions_on": ["on_enter_pressed"]
  }
}
```
**Why**: Price fetch is expensive (API call), only trigger on Enter

### Shares Input
```json
{
  "dispatch_action_config": {
    "trigger_actions_on": [
      "on_enter_pressed",
      "on_character_entered"
    ]
  }
}
```
**Why**: GMV calculation is cheap (simple math), update in real-time

### GMV Input
```json
{
  "dispatch_action_config": {
    "trigger_actions_on": [
      "on_enter_pressed",
      "on_character_entered"
    ]
  }
}
```
**Why**: Shares calculation is cheap (simple math), update in real-time

## Error Handling Flow

```
User Input
    ↓
Try Parse Value
    ├──▶ Success: Continue to calculation
    │
    └──▶ Failure (ValueError, TypeError)
            ↓
        Log Warning
            ↓
        Don't Update Modal
            ↓
        User Sees Original Value
            ↓
        No Error Message (Silent Fail)
            ↓
        User Can Continue Typing
```

## Performance Optimization

1. **Debouncing**: Slack handles debouncing automatically
2. **Calculation Caching**: Current price extracted once, reused
3. **Minimal API Calls**: Only symbol lookup hits external API
4. **Efficient Updates**: Only modified blocks are updated
5. **Error Recovery**: Failures don't break the modal

---

This autofill system provides a seamless, real-time calculation experience for traders while maintaining robust error handling and performance optimization.
