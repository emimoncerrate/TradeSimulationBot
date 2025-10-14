# Modal Input Block Fix

## Issue
The Slack API was returning an error when opening modals:
```
Error: The request to the Slack API failed. (url: https://www.slack.com/api/views.open)
The server responded with: {'ok': False, 'error': 'invalid_arguments', 'response_metadata': {'messages': ['[ERROR] must define `submit` to use an `input` block in modals [json-pointer:/view/blocks/2/input]']}}
```

## Root Cause
When a Slack modal contains `input` blocks, the Slack API requires a `submit` callback to be defined in the modal structure. Some of our modals were conditionally adding submit buttons, but the input blocks were always present.

## Files Fixed

### 1. listeners/enhanced_trade_command.py
**Problem**: The enhanced trade modal had input blocks but only added a submit button when market data was available.

**Fix**: Always include a submit button when the modal is created:
```python
# Before (conditional submit)
if context.current_quote:
    modal["submit"] = {
        "type": "plain_text",
        "text": "Trade"
    }

# After (always include submit)
modal["submit"] = {
    "type": "plain_text",
    "text": "Get Quote" if not context.current_quote else "Trade"
}
```

### 2. ui/trade_widget.py
**Problem**: The trade widget had input blocks but conditionally showed submit buttons based on form state.

**Fix**: Always include a submit button, but change the text based on state:
```python
# Before (conditional submit)
if self._should_show_submit_button(context):
    modal["submit"] = {
        "type": "plain_text",
        "text": modal_config['submit_text']
    }

# After (always include submit)
modal["submit"] = {
    "type": "plain_text",
    "text": modal_config['submit_text'] if self._should_show_submit_button(context) else "Continue"
}
```

## Verification
- Created a test to verify modals with input blocks have submit callbacks
- Test confirmed the fix works correctly
- Both modals now properly include submit buttons when input blocks are present

## Impact
- ✅ Fixes the Slack API error when opening trade modals
- ✅ Maintains existing functionality
- ✅ Improves user experience by always providing a way to submit forms
- ✅ Complies with Slack's modal requirements

## Notes
- The confirmation modal (`trade_confirmation_modal`) already had proper submit buttons
- Dashboard modals don't use input blocks, so they weren't affected
- Demo modal already had proper submit buttons