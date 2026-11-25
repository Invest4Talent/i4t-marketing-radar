# Marketing Radar — overstap naar publicatie vanuit gh-pages

De huidige livewebsite blijft ongewijzigd zolang **RADAR_PAGES_MODE** niet gelijk is aan `branch`.
De overstap vervangt alleen de publicatiemethode. Nieuwsverwerking, Google Search Console en AI-scores blijven werken zoals voorheen.

## Waarom apart token?

GitHub bevestigt dat commits gemaakt met het standaard `GITHUB_TOKEN` **geen GitHub Pages-build starten** wanneer Pages uit een branch publiceert. Gebruik daarom een beperkt, apart token. Geen OpenAI-token hergebruiken.

Documentatie: https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site

## Veilige omschakeling

1. Laat PR voor deze functie mergen. De oude GitHub Actions-publicatie blijft standaard geselecteerd.
2. Maak via https://github.com/settings/personal-access-tokens/new een **fine-grained personal access token** van een account dat schrijfrechten op **Invest4Talent/i4t-marketing-radar** heeft. Selecteer uitsluitend deze repository, geef minimaal **Contents: Read and write**, kies een beperkte vervaldatum en laat de organisatiehouder indien nodig het token goedkeuren. Het token is niet hetzelfde als je OpenAI API-sleutel.
3. Voeg dat token toe bij **Invest4Talent/i4t-marketing-radar → Settings → Secrets and variables → Actions → Repository secrets → New repository secret** met exacte naam `PAGES_PUBLISH_TOKEN`. Plak het token nooit in code, een pull request of een chat.
4. Ga naar de workflow **Go4Jobs Radar - dagelijks bijwerken en publiceren** op de `main`-branch en klik op **Run workflow**. Zet de optie **prepare_branch** op **true**. Dit maakt en vult `gh-pages` zonder de bestaande Pages-publicatie om te schakelen. Controleer dat **Schrijf website naar gh-pages-branch** groen is en dat in **Code → branches** een `gh-pages`-branch bestaat met `index.html`, `radar-data.json` en `.nojekyll`.
5. Ga naar **Settings → Pages → Build and deployment → Source**. Kies **Deploy from a branch**, daarna `gh-pages`, map `/(root)`, en klik op **Save**.
6. Ga naar **Settings → Secrets and variables → Actions → Variables → New repository variable**. Voeg `RADAR_PAGES_MODE` toe met waarde `branch` (geen secret).
7. Start op `main` opnieuw handmatig de workflow, deze keer met **prepare_branch = false**. Controleer dat **Schrijf website naar gh-pages-branch** groen is en dat de standaard GitHub Pages-branchbuild succesvol draait. Controleer ook of de online datum op https://invest4talent.github.io/i4t-marketing-radar/ overeenkomt met `radar-data.json` in de `gh-pages`-branch. Zo test je meer dan alleen de data-update.
8. Controleer de eerstvolgende automatische ochtend- en namiddaguitvoering. GitHub kan geplande workflows vertragen of in uitzonderlijke gevallen overslaan; deze migratie lost dat niet afzonderlijk op.

**Belangrijk:** zet `RADAR_PAGES_MODE` niet op `branch` voordat het token geldig is en de Pages-bron correct is ingesteld. Gebruik geen standaard `GITHUB_TOKEN` als vervanging.

## Terugkeren naar de vorige publicatie

1. Verwijder de variabele `RADAR_PAGES_MODE` of wijzig de waarde naar `actions`.
2. Zet **Settings → Pages → Source** terug naar **GitHub Actions**.
3. Start de dagelijkse workflow opnieuw. Het bestaande `scripts/deploy_pages.py`-pad blijft beschikbaar als tijdelijke terugvaloptie.

## Grenzen

- Het gebruik van een apart token introduceert een beheerafspraak: vóór de vervaldatum verlengen en vervangen bij personeelswissels. Overweeg later een organisatiebeheerde GitHub App met scoped repository access.
- Deze aanpak vermijdt onze huidige custom artifact-API-deployment, maar GitHub Pages moet nog steeds de `gh-pages`-branch verwerken; storingen bij GitHub zijn nooit volledig uit te sluiten.
- De workflow heeft bewust niet automatisch de GitHub Pages-instelling gewijzigd. Dat blijft een eenmalige beheerdersactie.
