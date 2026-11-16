# Grenzen van v0.6.0 — transparante release-notities

- **Nog geen productiecertificering.** HA-installatie, batterij-/achtergrondgedrag Android en echte externe marktfeeds zijn niet end-to-end getest.
- **Yahoo Finance** is onofficieel, rate-limit / veranderlijke structuur mogelijk. Alle data blijft transparant gedateerd; geen verzonnen koersen.
- **State Street-holdings**: officiële Excel-URL wordt dagelijks geprobeerd; parser herkent kolommen op naam en valideert 1000+ posities en 75–115% gewicht. Bij onverwachte bestandstructuur toont de app de laatst bevestigde snapshot, of leeg.
- **Onderliggende aandelen**: lokale prijzen uit de fondssamenstelling zijn dagprijzen; actuele koerswijzigingen voor alle ~6000 aandelen vereisen een bijkomende conforme databron. De optionele top-10-aandelenknop gebruikt onofficiële Yahoo-symbolen die mogelijk niet bij de primaire notering horen; beschouw die als experimenteel.
- **MeDirect-PDF**: nog niet betrouwbaar te importeren zonder een geanonimiseerd echt voorbeeldtransactiebewijs; handmatige invoer/CSV werkt.
- **Android APK**: er is broncode in een eerder pakket, maar geen gebouwde, op toestel geteste release-APK in deze repository. Synchronisatie werkt via de browser + beveiligde API, afhankelijk van bereikbaarheid van de HA-server.
- **Meldingen en agenda**: koersalerts worden nu bij openen/verversen van het dashboard bekeken; geen 24/7 push-notificaties naar Android, en de evenementenkalender bevat handmatig ingevoerde items.
- **Geen gegarandeerde dataverversing**: beurzen zijn 's avonds/weekend gesloten, gratis bronnen kunnen vertraging of downtime hebben.

- Historische rendementsvoorstellen zijn uitsluitend op echte opgehaalde EUR-slotkoersen gebaseerd. De gratis koersfeed is extern, onofficieel en niet end-to-end op de Home Assistant-installatie gecontroleerd.
