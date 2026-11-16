# SPYI Desk — Productiereadiness (16 november 2026)

**Status:** v0.7.0 BETA / Home Assistant testinstallatie. **Niet v1.0 en niet volledig productieklaar.**

## Nu in broncode aanwezig
- Home Assistant OS x86-64 app met Ingress (HA-login, geen publieke interface).
- Automatische pogingen om SPYI.DE in EUR op te halen (gratis onofficiële Yahoo Finance; geen SLA).
- Persistente SQLite-cache voor geverifieerde ETF-koersen, beschikbare koershistorie en SPDR/State Street-posities.
- Behoud van laatste geldige beursgegevens wanneer een bron uitvalt; bron-/tijdweergave.
- Automatische SPDR Excel-import, uitgebreide kolomherkenning, datum/gewichtcontrole, handmatige retry en foutdiagnose.
- Portefeuillebeheer, CSV-import/export, simulator en historische CAGR.
- Klant- en server-side validatie van transacties: geldige datum, aantallen, prijzen, kosten, geen dubbele ID of onmogelijke verkoop.
- Herwerkte XIRR voor open en afgesloten posities; zonder fictieve aankoopprijs.
- Revision-based mobiele sync API met sleutel, atomaire opslag, laatste tien oude privéversies en bescherming tegen ongeldige input.
- Android-broncode en GitHub Actions *unsigned* compile workflow; géén ondertekende APK.

## Testbewijs
- Python/JS regressietests en mock-gebaseerde backendtests zijn toegevoegd aan GitHub Actions.
- Tests op lokaal ontwikkelmodel voor market cache, Excel parser, auth, conflict, XIRR en transactiebeperkingen geslaagd.
- Echte SPYI-koers en grafiek zichtbaar op gebruikers-HA in vorige versie (screenshots). Dit bevestigt niet alle updates.
- Synthetische SPDR-werkmap met ~6.100 aandelen slaagt. **Geen geslaagde import van het actuele bestand op gebruikers-HA bevestigd**.
- Lokale browserautomatisering werd door de testomgeving geblokkeerd.
- Android-build, release signing, koppeling met HA en echte toesteltest **niet bevestigd**.

## Verplichte acceptatietests vóór stabiele v1.0
1. [Echte State Street holdings op HA](https://github.com/fj86-gif/SPYI-Desk-HA/issues/2)
2. [Ondertekende en geteste Android APK inclusief private sync](https://github.com/fj86-gif/SPYI-Desk-HA/issues/3)
3. [MeDirect PDF-parser met anonieme echte voorbeelden](https://github.com/fj86-gif/SPYI-Desk-HA/issues/4)
4. [Achtergrondalerts en automatische rapporten](https://github.com/fj86-gif/SPYI-Desk-HA/issues/5)
5. [Financiële reconciliatie, HA-back-up/herstel en security QA](https://github.com/fj86-gif/SPYI-Desk-HA/issues/6)
6. [Dekking/licenties van duizenden mondiale aandelenkoersen](https://github.com/fj86-gif/SPYI-Desk-HA/issues/7)

## Veilig testen op Home Assistant
1. Maak vooraf een Home Assistant-back-up. Bestaande installaties niet verwijderen.
2. Update via **Instellingen → Apps → SPYI Desk** naar v0.7.0.
3. Onder **Alle aandelen**: **Automatisch ophalen**. Controleer bron, peildatum, positie-aantal, totaalgewicht en fouttekst.
4. Voeg één testtransactie toe en controleer na een herstart dat gegevens bewaard bleven; exporteer ook je transacties.
5. Stel géén publiek toegankelijke portforwarding in voor 8765. Gebruik alleen een privé HTTPS-tunnel/Tailscale met token.
6. Als koersen verouderd zijn of bron ontbreekt: app toont laatste bevestigde waarde, niet een verzonnen livekoers.

> Persoonlijke data, tokens en ondertekeningssleutels mogen nooit in GitHub worden geplaatst. De openbare repository bevat uitsluitend code en synthetische testdata.
