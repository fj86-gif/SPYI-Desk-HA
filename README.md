# SPYI Desk – Home Assistant OS (beta)

Een lokale, experimentele SPYI-portefeuilleviewer als Home Assistant-app.

> ⚠️ Dit is geen productieklare app. Automatische gratis koersfeeds, volledige SPYI-aandelenimport, MeDirect PDF-import, Android APK en hardwarematige integratie zijn niet end-to-end getest.

## GitHub-publicatie

Publiceer de **inhoud** van deze map (niet de ZIP zelf) in de root van een nieuwe openbare repository, bijvoorbeeld `SPYI-Desk-HA`. Home Assistant zoekt `repository.yaml` in de root en `spyi_desk/config.yaml` in de app-map.

## Installatie vanaf Android

Home Assistant → Instellingen → Apps → App installeren → ⋮ → Repositories → voer de **werkelijk gepubliceerde** repository-URL in. Na toevoegen verschijnt **SPYI Desk** in de appwinkel.

## Teststatus

Lokale HTTP-smoketests voor Ingress, sleutelauthenticatie, synchronisatie en SQLite slagen. Geen echte HA-installatie, Android APK-test, periodieke koersfeedtest, of externe security-audit uitgevoerd.

## Privacy

Code en fictieve demonstratiedata kunnen publiek; **nooit** portefeuille-transactiebestanden, logs, tokens, back-ups of andere echte persoonlijke gegevens committen.

Bekijk `spyi_desk/DOCS.md` voor installatie en beperkingen.