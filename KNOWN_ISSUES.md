# Release v0.6.0 — nog niet productieklaar

**Gecontroleerd in lokale tests:** app-API, tokenautorisatie, gedeelde transactiestatus, aanmaken en bewaren van de marktcache, bewaren van echte gedateerde koersen bij provider-uitval, afkeuren van een ongeldig holdingsbestand.

**Nog te verifiëren:** installatie en Docker-start op jouw Home Assistant OS, werkelijke response van het Yahoo-chartendpoint, downloaden en volledig parsen van de actuele State Street XLSX, herstel van app-back-ups op HA, mobiele synchronisatie via private HTTPS, front-end op echte telefoons.

**Nog niet gebouwd of afhankelijk van ontbrekende externe input:** release Android APK en Android pushmeldingen; MeDirect PDF-import zonder geanonimiseerd voorbeeldbewijs; 24/7 koersalerts; externe bedrijfskalender; gegarandeerde 15-minutenkoersen voor alle duizenden holdings.

**Datakwaliteit:** dagelijkse lokale prijzen in State Street-Excel zijn geen 15-minutenkoersen. De experimentele top-10 individuele tickers kunnen onjuist verwijzen naar buitenlandse handelsplaatsen. Gebruikers moeten beursnotering en valuta verifiëren.

**Privédata:** ingevoerde transacties worden lokaal opgeslagen en niet in GitHub geplaatst. Fictieve begintransacties ontbreken bewust; vul je echte aankopen zelf in. Bij een update wordt een oude demo-koers/historie gewist maar je echte transacties bewaard.

Alle rendementsprognoses en Monte Carlo-scenario's zijn wiskundige simulaties, geen koersdata of financieel advies.
