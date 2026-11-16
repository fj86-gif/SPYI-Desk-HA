# SPYI Desk · experimentele Home Assistant-app

**Status: beta / niet productieklaar.** Installeer alleen om te testen na een Home Assistant-back-up.

## Installatie vanuit smartphone (wanneer repository online staat)

1. Open Home Assistant → Instellingen → Apps → App installeren → ⋮ → Repositories.
2. Voeg de URL toe van de **publiek beschikbare** GitHub-repository met dit bestand en `repository.yaml` in de root.
3. Installeer **SPYI Desk** en start de app.
4. Open de app in de HA-zijbalk. Gegevens staan op `/data` en vallen onder de back-ups van de app.

## Wat werkt en wat niet

- Webinterface via Home Assistant Ingress, interne API, transacties, simulaties, eenvoudige server-side sync zijn lokaal getest.
- **Geen bewezen actuele/live beurskoersen:** onofficiële Yahoo-koersbron kan weigeren, vertragen of veranderen; tijdstempels zijn leidend.
- **Niet alle SPYI-onderliggende aandelen zijn automatisch bijgewerkt.** Import van CSV/Excel kan wel, automatische holdings-download ontbreekt.
- **Geen gevalideerde MeDirect PDF-import.** CSV/handmatige import is alternatief.
- Android APK is nog **niet gebouwd** of op echte Android-toestellen getest. Android-meldingen ontbreken.
- Deze HA-versie is nog **niet op echte Home Assistant OS-hardware** getest; alleen lokaal geteste HTTP-functies.
- Het dashboard start met een lege transactieportefeuille en expliciet gemarkeerde fictieve demonstratiekoersen.

## Beveiliging

- **De Android API-poort 8765 staat standaard uit.** Open ze niet rechtstreeks naar internet en bij voorkeur ook niet onversleuteld in je LAN. Configureer eerst een privé HTTPS-verbinding via Tailscale.
- De webinterface via Ingress gebruikt je Home Assistant-aanmelding. De Android API vereist een afzonderlijke lange koppelsleutel.
- Deel nooit je koppelsleutel of een databestand met portefeuille-informatie op GitHub.
- Deze versie is niet onafhankelijk op beveiliging geaudit. Laat geen publieke hostpoort of Tailscale Funnel toe.

## Updates

Dit is een proefpakket voor verdere ontwikkeling, geen officiële release. Maak vóór updates een back-up.
