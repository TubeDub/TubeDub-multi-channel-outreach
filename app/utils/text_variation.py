import random

TEMPLATES = [
    "{greeting}, {name}! {text}",
    "{text} — {city}, с уважением!",
    "Привет, {name}! {text}",
    "{name}, {text} ({city})",
    "{text}\n\nP.S. {greeting} из {city}!",
]

GREETINGS = ["Привет","Здравствуйте","Добрый день","Хай","Привіт"]

def vary(text: str, name: str = "", city: str = "") -> str:
    tmpl = random.choice(TEMPLATES)
    greet = random.choice(GREETINGS)
    # Spintax простой: {а|б} внутри text
    import re
    def repl_spintax(m):
        opts = m.group(1).split("|")
        return random.choice(opts)
    text = re.sub(r"\{([^{}]*\|[^{}]*)\}", repl_spintax, text)
    name = name or "друг"
    city = city or "ваш город"
    return tmpl.format(text=text, name=name, city=city, greeting=greet)
