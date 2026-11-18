# 💧 MPWiK Będzin (iBOK) — Home Assistant Integration

Lekka integracja dla **Home Assistant** pobierająca dane rozrachunkowe oraz odczyty wodomierzy z portalu **iBOK MPWiK Będzin** (`https://ibok.mpwik.bedzin.pl/`) za pomocą czystych zapytań HTTP (`aiohttp`), bez użycia ciężkiej przeglądarki (Chromium/Playwright).

Po każdym pobraniu danych integracja automatycznie wylogowuje sesję (`?logout=true&kill=true`), zapobiegając blokadom konta oraz pojawianiu się CAPTCHA.

---

## ✨ Funkcje i dostępne sensory

| Sensor | Opis | Jednostka / Atrybuty |
|---|---|---|
| **Amount due** | Łączna kwota do zapłaty | `PLN` · atrybuty: `invoices`, `unpaid_invoices`, `total_charged`, `total_paid` |
| **Next due date** | Najbliższy termin płatności nieopłaconej faktury | Data (`YYYY-MM-DD`) |
| **Unpaid invoices** | Liczba nieopłaconych faktur | Liczba całkowita |
| **Water meter** | Aktualny stan wodomierza (`TOTAL_INCREASING` — gotowy pod Energy Dashboard) | `m³` · atrybut `history` (do 24 ostatnich odczytów) |
| **Water consumption** | Zużycie wody wyliczone z różnicy dwóch ostatnich odczytów | `m³` |

---

## 📦 Instalacja (Marketplace / HACS)

1. W Home Assistant otwórz **Settings > Marketplace** (lub **HACS**).
2. Wybierz menu w prawym górnym rogu (**Custom repositories**) i dodaj adres:
   `https://github.com/1234sok1234/ha-mpwik-bedzin` (kategoria: **Integration**).
3. Zainstaluj integrację i zrestartuj Home Assistant (**Settings > System > Restart**).
4. Przejdź do **Settings > Devices & services > Add integration**, wyszukaj **MPWiK Będzin** i podaj login oraz hasło do iBOK.

*(Opcjonalnie: dodaj sensor `Water meter` w **Settings > Dashboards > Energy** w sekcji **Water consumption**, aby śledzić zużycie na wykresach).*

---

## 📊 Gotowe karty na Dashboard (Markdown)

*(Zamień `12345` w nazwie encji na swój numer klienta z iBOK).*

### 1. Historia faktur

```yaml
type: markdown
title: 💧 MPWiK Będzin — Historia faktur
content: |
  | Faktura | Wystawiona | Termin | Kwota | Do zapłaty |
  |:---|:---|:---|---:|---:|
  {%- for f in state_attr('sensor.mpwik_bedzin_12345_amount_due', 'invoices') or [] %}
  | {{ f.number }} | {{ f.issued }} | {{ f.due_date }} | {{ "%.2f"|format(f.amount_total) }} | **{{ "%.2f"|format(f.amount_due) }}** |
  {%- endfor %}
```

### 2. Historia odczytów wodomierza

```yaml
type: markdown
title: 🚰 Wodomierz — Historia odczytów
content: |
  | Data | Stan (m³) | Zużycie (m³) | Typ |
  |:---|---:|---:|:---|
  {%- for r in state_attr('sensor.mpwik_bedzin_12345_water_meter', 'history') or [] %}
  | {{ r.date }} | **{{ "%.2f"|format(r.reading_m3) }}** | {{ "%.2f"|format(r.consumption_m3) }} | {{ r.type or '-' }} |
  {%- endfor %}
```

---

## 🔔 Przykładowa automatyzacja (Powiadomienie o nowej fakturze)

```yaml
alias: "MPWiK Będzin — Powiadomienie o nowej fakturze"
mode: single
triggers:
  - trigger: state
    entity_id: sensor.mpwik_bedzin_12345_unpaid_invoices
conditions:
  - condition: template
    value_template: >
      {{ trigger.from_state is not none
         and trigger.from_state.state not in ['unknown', 'unavailable']
         and (trigger.to_state.state | int(0)) > (trigger.from_state.state | int(0)) }}
actions:
  - action: notify.notify
    data:
      title: "💧 Nowa faktura MPWiK Będzin"
      message: >
        {% set unpaid = state_attr('sensor.mpwik_bedzin_12345_amount_due', 'unpaid_invoices') or [] %}
        {% set latest = (unpaid | sort(attribute='issued', reverse=true) | first) if unpaid else none %}
        {% if latest %}
          Faktura {{ latest.number }}: masz do zapłaty {{ "%.2f"|format(latest.amount_due) }} zł do {{ latest.due_date }}.
        {% else %}
          Brak nieopłaconych faktur (saldo: {{ states('sensor.mpwik_bedzin_12345_amount_due') }} zł).
        {% endif %}
```
