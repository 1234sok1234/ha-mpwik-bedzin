# MPWiK Będzin iBOK (Home Assistant)

Nieoficjalna, customowa integracja do Home Assistanta, która loguje się do [iBOK MPWiK Będzin](https://ibok.mpwik.bedzin.pl/) i pilnuje rozrachunków za wodę.

Powstała jako rozwiązanie tymczasowe — dopóki MPWiK nie uruchomi systemu powiadomień o nowych fakturach. A że od ponad roku nic w tym temacie się nie wydarzyło, to chyba nie ma już co liczyć na SMS-y czy maile i lepiej oddać temat w ręce Home Assistanta. 💧

> **Uwaga:** Jest to nieoficjalny projekt korzystający z portalu iBOK (brak oficjalnego API). Zmiany po stronie MPWiK mogą wymagać aktualizacji integracji.

## Funkcje
- **Amount due** (`PLN`) — łączna kwota do zapłaty (+ lista nieopłaconych faktur w atrybutach).
- **Next due date** — najbliższy termin płatności nieopłaconej faktury.
- **Unpaid invoices** — liczba faktur do zapłaty.
- Konfigurowalny interwał odświeżania w UI (domyślnie co 24h).

## Instalacja (Marketplace)
1. Otwórz `Settings > Marketplace` w Home Assistant.
2. Dodaj to repozytorium jako **Custom repository** (kategoria: Integration).
3. Pobierz integrację i zrestartuj Home Assistant.
4. Dodaj konto w `Settings > Devices & services > Add integration`.
