# Unused, shell_command instead

ticker = data.get("ticker_entity_id")
state = hass.states.get(ticker)
attr = state.attributes

def format_2dp(x):
    # Truncates to 2 decimal places and ensures 0.00 padding
    truncated = x #math.floor(x * 100) / 100
    return f"{truncated:.2f}"

def format_change(p_str):
    # Adds a '+' prefix if the number is non-negative
    if float(p_str) >= 0:
        return f"+{p_str}"
    return p_str

post_t = str(attr.get("postMarketTime", 0))
reg_t = str(attr.get("regularMarketTime", 0))
pre_t = str(attr.get("preMarketTime", 0))

# Logic to determine which market period is most recent
if post_t > reg_t and post_t > pre_t:
    timestamp = post_t
    price = attr.get("postMarketPrice")
    change = attr.get("postMarketChangePercent")
    period = "after-hours"
elif reg_t > pre_t:
    timestamp = reg_t
    price = attr.get("regularMarketPrice")
    change = attr.get("regularMarketChangePercent")
    period = "regular-market"
else:
    timestamp = pre_t
    price = attr.get("preMarketPrice")
    change = attr.get("preMarketChangePercent")
    period = "pre-market"

# Construct the final object
result = {
    "symbol": attr.get("symbol"),
    "timestamp": timestamp,
    "changePercentage": format_change(format_2dp(change)),
    "latestPrice": format_2dp(price),
    "preMarketPrice": attr.get("preMarketPrice"),
    "regularMarketPrice": attr.get("regularMarketPrice"),
    "postMarketPrice": attr.get("postMarketPrice"),
    "period": period
}

hass.services.call("notify", "signal_homeassistant", {"message": f"{result}"})