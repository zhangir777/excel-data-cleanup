"""Clean a messy sales/leads table: headers, names, phones, emails, dates, amounts, duplicates."""

import re
from dataclasses import dataclass, field
from datetime import date, datetime

COLUMNS = ["date", "client", "phone", "email", "manager", "product", "amount"]

# Header variants seen in real exports (EN/RU), compared after lower() and trimming
ALIASES = {
    "date": ["date", "order date", "created", "дата", "дата заказа"],
    "client": ["client", "client name", "customer", "name", "клиент", "имя", "фио"],
    "phone": ["phone", "phone number", "tel", "mobile", "телефон", "тел"],
    "email": ["email", "e-mail", "mail", "почта"],
    "manager": ["manager", "sales rep", "responsible", "менеджер", "ответственный"],
    "product": ["product", "item", "service", "товар", "услуга"],
    "amount": ["amount", "sum", "total", "price", "сумма", "итого"],
}

DATE_FORMATS_DAY_FIRST = ["%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y"]
DATE_FORMATS_MONTH_FIRST = ["%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y", "%m/%d/%Y", "%m-%d-%Y", "%b %d %Y"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$")


def map_header(name: str) -> str | None:
    key = re.sub(r"[,(].*$", "", str(name or "")).strip().lower()  # "Amount, KZT" -> "amount"
    for column, variants in ALIASES.items():
        if key in variants:
            return column
    return None


def normalize_phone(raw) -> str | None:
    """KZ/RU numbers to +7XXXXXXXXXX; other international numbers (+...) kept as +digits."""
    if raw is None:
        return None
    raw = str(raw).strip()
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits[0] in "78":
        return "+7" + digits[1:]
    if len(digits) == 10 and digits[0] in "67":
        return "+7" + digits
    if raw.startswith("+") and 8 <= len(digits) <= 15:
        return "+" + digits
    return None


def clean_name(raw) -> str:
    """'  aLIYA   nurlanovna ' -> 'Aliya Nurlanovna'."""
    words = str(raw or "").split()
    return " ".join("-".join(p[:1].upper() + p[1:].lower() for p in w.split("-")) for w in words)


def clean_email(raw) -> str | None:
    email = str(raw or "").strip().lower()
    return email if EMAIL_RE.match(email) else None


def parse_date(raw, month_first: bool = False) -> date | None:
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    text = re.sub(r"\s+", " ", str(raw or "").replace(",", " ")).strip()
    if not text:
        return None
    text = text.split(" ")[0] if re.match(r"^\d{4}-\d{2}-\d{2}[ T]", text) else text
    for fmt in DATE_FORMATS_MONTH_FIRST if month_first else DATE_FORMATS_DAY_FIRST:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_amount(raw) -> float | None:
    """'1 200,50 ₸', '$1,200.50', '1.200,50', '1200' -> 1200.5. None if no number."""
    if isinstance(raw, int | float):
        return float(raw)
    text = re.sub(r"[^\d,.\-]", "", str(raw or ""))
    if not re.search(r"\d", text):
        return None
    if "," in text and "." in text:
        # the separator that comes last is the decimal one
        thousands = "," if text.rfind(".") > text.rfind(",") else "."
        text = text.replace(thousands, "").replace(",", ".")
    elif "," in text:
        whole, _, tail = text.rpartition(",")
        text = f"{whole.replace(',', '')}.{tail}" if len(tail) in (1, 2) else text.replace(",", "")
    elif text.count(".") > 1:
        text = text.replace(".", "")
    try:
        return round(float(text), 2)
    except ValueError:
        return None


@dataclass
class Result:
    clean: list[dict] = field(default_factory=list)
    removed: list[dict] = field(default_factory=list)  # original row + "reason"
    stats: dict = field(default_factory=dict)


def clean_rows(rows: list[dict], month_first: bool = False) -> Result:
    """rows: dicts with the original headers. Returns clean rows keyed by COLUMNS."""
    result = Result()
    stats = dict(rows_in=len(rows), empty=0, invalid=0, duplicates=0, phones_fixed=0,
                 bad_phones=0, bad_emails=0)  # fmt: skip
    seen = set()
    for raw in rows:
        if not any(str(v or "").strip() for v in raw.values()):
            stats["empty"] += 1
            continue
        row = {c: None for c in COLUMNS}
        for header, value in raw.items():
            column = map_header(header)
            if column:
                row[column] = value
        original_phone = str(row["phone"] or "").strip()
        row["date"] = parse_date(row["date"], month_first)
        row["amount"] = parse_amount(row["amount"])
        row["client"] = clean_name(row["client"])
        row["manager"] = clean_name(row["manager"])
        row["product"] = re.sub(r"\s+", " ", str(row["product"] or "")).strip()
        row["phone"] = normalize_phone(original_phone)
        if original_phone and row["phone"] != original_phone:
            stats["phones_fixed" if row["phone"] else "bad_phones"] += 1
        email = row["email"]
        row["email"] = clean_email(email)
        if str(email or "").strip() and not row["email"]:
            stats["bad_emails"] += 1

        checks = [
            ("no valid date", row["date"]),
            ("no valid amount", row["amount"] is not None),
            ("no client or phone", row["client"] or row["phone"]),
        ]
        problems = [name for name, ok in checks if not ok]
        if problems:
            stats["invalid"] += 1
            result.removed.append({**raw, "reason": ", ".join(problems)})
            continue
        key = (row["date"], row["phone"] or row["client"].lower(), row["product"].lower(),
               row["amount"])  # fmt: skip
        if key in seen:
            stats["duplicates"] += 1
            result.removed.append({**raw, "reason": "duplicate"})
            continue
        seen.add(key)
        result.clean.append(row)
    result.clean.sort(key=lambda r: r["date"])
    stats["clean"] = len(result.clean)
    result.stats = stats
    return result
