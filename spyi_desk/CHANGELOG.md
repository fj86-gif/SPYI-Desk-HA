# 0.7.0 (beta) — 16 november 2026

- Validatie van aankoop/verkooptransacties in de browser en synchronisatieserver.
- XIRR voor open en afgesloten posities aangepast, inclusief expliciete nul en ambigue wortels.
- Geen verzonnen invulprijs bij een nieuwe transactie.
- Automatisch behoud van laatste tien versies van persoonlijke sync-gegevens.
- Foutieve/oudere koersen en vreemde valuta verhinderen geen valide cache; worden geweigerd.
- Maximaal beschikbare SPYI.DE-historie opvragen bij Yahoo; bron blijft onofficieel.
- Extra financiële regressietests en GitHub Android-buildproject (unsigned).
- Ongevalideerde MeDirect PDF-import niet langer als werkend gepresenteerd.
- **Release blijft experimenteel.** Zie ../PRODUCTION_READINESS.md.


# 0.6.0
- Home Assistant OS-app met Ingress, beperkte Android-API, quote-cache in SQLite, persistent synchronisatiestate.

## v0.6.1 — historische rendementsvoorstellen
- Simulator berekent CAGR voor 1, 3 en 5 jaar uit de werkelijk opgehaalde EUR-slotkoersen van SPYI.DE.
- Vijfjaars-CAGR is de aanbevolen historische referentie; kiezen is optioneel.
- Historische rendementen met verouderde data (>14 dagen) kunnen niet worden toegepast.
- Geen fictieve percentages of voorgeselecteerde historische waarden zonder verifieerbare koersreeks.
