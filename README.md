# SPYI Desk voor Home Assistant — v0.6.0 bèta

Een lokaal portefeuille-dashboard met **echte, gedateerde** SPYI-data. Geen fictieve aandelenposities, koersgrafieken of startkoersen.

> **BETA — niet productieklaar verklaard.** De officiële databronnen en de update op je eigen HA-installatie zijn nog niet end-to-end getest. Bij storingen worden laatst geverifieerde waarden met hun oorspronkelijke koersdatum getoond, niet een verzonnen nieuwe prijs.

## Echte databronnen
- SPYI.DE (Xetra, EUR): Yahoo Finance chart-endpoint (onofficieel). De koers wordt elke 15 minuten *geprobeerd*; niet gegarandeerd, bronvoorwaarden en koersvertraging gelden.
- Koershistoriek: dezelfde Yahoo-bron, maximaal vijf jaar.
- Onderliggende aandelen: **State Street SPDR officiële dagelijkse holdings Excel** via de officiële productdownload, dagelijks opgehaald. Lokale prijzen in het Excelbestand zijn niet realtime.
- De persoonlijke portefeuille komt **uitsluitend** uit transacties die je zelf hebt ingevoerd of geïmporteerd.

De server bewaart geldige records op /data/market.sqlite3. Als Yahoo of State Street weigert, blijft de laatst opgeslagen versie intact en toont het dashboard de echte tijdstempel.

## Update vanuit Home Assistant
Instellingen → Apps → SPYI Desk → zet een back-up klaar → bij een nieuwe versie kies **Bijwerken** → Open webinterface. Browsercache kan na de update ververst worden.

## Veiligheid & privacy
Home Assistant Ingress is de aanbevolen toegang. De Android-API op poort 8765 is standaard **niet** op de HA-host gepubliceerd. Publiceer die nooit rechtstreeks op internet. Alleen een juist ingestelde privé-HTTPS-oplossing zoals Tailscale Serve is geschikt; test extern synchroniseren afzonderlijk. Maak een HA-back-up vóór updates, en plaats nooit echte transacties, koppelcodes of back-ups in GitHub.

## Nog niet productieklaar
De echte werking van de externe koers- en holdingsfeed, Android release-APK, achtergrondpushmeldingen, automatische externe bedrijfskalender en MeDirect PDF-import zijn nog niet bevestigd of afgerond. Handmatige transactie-invoer/CSV werkt als alternatief voor PDF. De top-10-aandelenknop is experimenteel omdat symbolen beursafhankelijk zijn.

Bekijk KNOWN_ISSUES.md voor de volledige beperkingen. Testresultaten betreffen lokale regressietests met gecontroleerde externe antwoorden; geen bewijs van live beursupdates op je toestel.
