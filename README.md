# SPYI Desk voor Home Assistant — v0.6.1 bèta

SPYI Desk draait op Home Assistant OS (amd64) via Ingress en bewaart persoonlijke gegevens lokaal.

**Geen fictieve koersen of posities.** De eerste keer toont de app lege marktgegevens totdat een echte bron een geldige, gedateerde respons levert.

## Databronnen
- Xetra `SPYI.DE`: onofficiële Yahoo Finance chartinterface. Streefinterval 15 minuten; geen gegarandeerde uptime, gratis bron, vertraging of licentie. Tijdstip van de werkelijke handelskoers wordt altijd getoond.
- Fondsposities: dagelijks officieel SPDR/State Street Excelbestand op `https://www.ssga.com/library-content/products/fund-data/etfs/emea/holdings-daily-emea-en-spyi-gy.xlsx`.
- Koershistorie: via Yahoo, maximaal 5 jaar (dezelfde bron). Individuele lokale prijzen in het holdingsbestand zijn **geen live beurskoersen**.

Bij een storing worden laatst geverifieerde waarden met datum behouden. Zonder eerdere gegevens verschijnt geen koers.

## Home Assistant-installatie
Via Apps → App installeren → ⋮ → Repositories → `https://github.com/fj86-gif/SPYI-Desk-HA` → SPYI Desk → Installeren → Starten → Open Web UI.

Maak vooraf een Home Assistant-back-up. De database en synchronisatiestatus staan in `/data` en de app gebruikt een cold backup om SQLite correct te bewaren.

## Privacy en veilige synchronisatie
Via Home Assistant Ingress is geen afzonderlijk login nodig. De aparte mobiele poort 8765 is standaard **niet gepubliceerd**; laat die uit totdat Tailscale Serve correct geconfigureerd is. Geen portforwarding of Funnel. Persoonlijke transacties mogen niet naar GitHub.

## Nog niet productiegetest
De volledige live werking op jouw HA-computer en bij externe dataproviders is nog niet bevestigd. Een gratis koersbron kan weigeren. Er is nog geen volledige Android-APK-build, betrouwbare pushmeldingen, gevalideerde MeDirect-PDF-parser of officiële automatische externe evenementenkalender. ETF-overlap vereist een tweede holdingsbestand.

Alle scenario-rendementen zijn berekende hypothesen, geen voorspellingen. De app mag geen financieel advies geven.

## Nieuw: rendementvoorstel uit echte historie
De inlegsimulator toont geannualiseerde SPYI.DE-koersrendementen in EUR over 1, 3 en 5 jaar indien voldoende **geverifieerde** dagelijkse historische koersen geladen zijn. Kies het gewenste percentage handmatig. Vijf jaar wordt als historische referentie aangeduid; eerdere rendementen zijn geen voorspellingen. Als de koersbron faalt of gegevens ouder zijn dan 14 dagen, geeft de app geen toepasbaar voorstel.
