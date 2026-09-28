import os
import json
import urllib.request

def convert_currency(amount: float, from_currency: str = "USD", to_currency: str = "JPY") -> str:
    """Convert a financial amount between travel currencies (e.g. USD, JPY, EUR, GBP, CAD) using live exchange rates.

    Args:
        amount: The monetary value to convert (e.g. 160.0).
        from_currency: The 3-letter source currency code (e.g. 'USD', 'EUR', 'GBP'). Default is 'USD'.
        to_currency: The 3-letter target currency code (e.g. 'JPY', 'EUR', 'CAD'). Default is 'JPY'.

    Returns:
        A formatted summary string with the converted amount, target currency, and applied exchange rate.
    """
    try:
        from_curr = from_currency.upper().strip()
        to_curr = to_currency.upper().strip()
        
        # Read API key if provided in environment variable
        api_key = os.environ.get("EXCHANGE_RATE_API_KEY")
        if api_key:
            url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{from_curr}"
        else:
            # Fallback to free public endpoint (open.er-api.com)
            url = f"https://open.er-api.com/v6/latest/{from_curr}"

        req = urllib.request.Request(url, headers={"User-Agent": "GlobeTrotterAgent/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())

        if data.get("result") != "success":
            return f"Unable to fetch exchange rates for '{from_curr}'."

        rates = data.get("rates", {})
        if to_curr not in rates:
            return f"Target currency '{to_curr}' not found in exchange rate response."

        rate = rates[to_curr]
        converted_value = round(amount * rate, 2)

        return (
            f"{amount} {from_curr} = {converted_value} {to_curr} "
            f"(Exchange rate: 1 {from_curr} = {rate:.4f} {to_curr})"
        )
    except Exception as e:
        return f"Error converting currency: {str(e)}"
