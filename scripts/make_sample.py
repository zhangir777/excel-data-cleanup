"""Generate samples/messy_sales.csv: made-up orders with the mess real exports have.

py scripts/make_sample.py
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)
OUT = Path(__file__).parent.parent / "samples" / "messy_sales.csv"

CLIENTS = ["aliya nurlanova", "DANIYAR SEITKALI", "  marat  akhmetov", "Gulnara Abenova",
           "erlan ospanov ", "Madina kassymova", "TIMUR ZHAKUPOV", "Aigerim Sadykova",
           "sanzhar bekov", "Dana Iskakova", "Arman Tulegenov", "zarina omarova"]  # fmt: skip
MANAGERS = ["Asel", "asel ", "BAUYRZHAN", "Bauyrzhan", "Kamila", "kamila"]
PRODUCTS = ["Haircut", "Coloring ", "Manicure", "  Styling", "Consultation"]


def messy_phone() -> str:
    d = f"77{random.randint(0, 9)}{random.randint(1000000, 9999999)}"
    spaced = f"8 {d[0:3]} {d[3:6]} {d[6:8]} {d[8:]}"
    dashed = f"+7 ({d[0:3]}) {d[3:6]}-{d[6:8]}-{d[8:]}"
    return random.choice([spaced, dashed, f"8{d}", d, f"+7{d}"])


def messy_date(d: date) -> str:
    return random.choice([d.strftime("%d.%m.%Y"), d.isoformat(), d.strftime("%d/%m/%Y"),
                          d.strftime("%d.%m.%y"), d.strftime("%d %b %Y")])  # fmt: skip


def messy_amount(x: float) -> str:
    whole = f"{int(x):,}"
    return random.choice([f"{whole.replace(',', ' ')} ₸", f"{x:.2f}".replace(".", ","),
                          f"{whole}.00", str(int(x)), f"{whole.replace(',', ' ')},00"])  # fmt: skip


def main() -> None:
    rows, start = [], date(2026, 7, 1)
    phones = {c: messy_phone() for c in CLIENTS}
    for _ in range(180):
        client = random.choice(CLIENTS)
        email = client.strip().split()[0].lower() + "@example.com"
        rows.append({
            "Date ": messy_date(start + timedelta(days=random.randint(0, 120))),
            "Client name": client,
            "Phone": phones[client] if random.random() > 0.05 else "123",
            "E-mail": email if random.random() > 0.1 else email.replace("@", " at "),
            "Manager": random.choice(MANAGERS),
            "Product": random.choice(PRODUCTS),
            "Amount, KZT": messy_amount(random.choice([5000, 6000, 7000, 8000, 20000, 15500.5])),
        })  # fmt: skip
    rows += random.sample(rows, 15)  # double exports
    rows += [{k: "" for k in rows[0]} for _ in range(5)]  # empty lines
    rows += [{**rows[0], "Date ": "soon"}, {**rows[1], "Amount, KZT": "free"}]  # broken rows
    random.shuffle(rows)
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} rows -> {OUT}")


if __name__ == "__main__":
    main()
