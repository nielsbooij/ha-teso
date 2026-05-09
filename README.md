# TESO Veerboot - Home Assistant Integratie

Volgt het aantal resterende overtochten op je TESO-passen en e-tickets via het Mijn TESO portaal.

## Installatie

### Handmatig

1. Kopieer de map `custom_components/teso/` naar je Home Assistant `custom_components/` map.
2. Herstart Home Assistant.
3. Ga naar **Instellingen → Apparaten & Diensten → Integratie toevoegen**.
4. Zoek op **TESO** en volg de stappen.

### Via HACS (aanbevolen)

1. Voeg deze repository toe als aangepaste repository in HACS.
2. Installeer de **TESO Veerboot** integratie.
3. Herstart Home Assistant.
4. Ga naar **Instellingen → Apparaten & Diensten → Integratie toevoegen**.
5. Zoek op **TESO** en volg de stappen.

## Configuratie

Je hebt je Mijn TESO inloggegevens nodig:
- **Gebruikersnaam**: je e-mailadres waarmee je inlogt op [www.teso.nl](https://www.teso.nl/my-teso/)
- **Wachtwoord**: je wachtwoord

## Sensoren

Per product op je pas wordt een sensor aangemaakt, bijvoorbeeld:

| Sensor | Waarde | Eenheid |
|--------|--------|---------|
| `sensor.teso_60skf2_15x_voertuig_tm_6_50m_tx` | 15 | overtochten |

### Attributen per sensor

- `pasnummer` — het nummer van je TESO-pas
- `product` — naam van het product
- `kenteken` — gekoppeld kenteken (indien van toepassing)
- `voertuig` — omschrijving van het voertuig

## Verversing

De data wordt elk uur automatisch bijgewerkt. Je kunt ook handmatig verversen via **Instellingen → Apparaten & Diensten → TESO → Bijwerken**.

## Gebruik in automatiseringen

Voorbeeld: stuur een melding als je nog maar 2 overtochten over hebt:

```yaml
automation:
  - alias: "TESO bijna op"
    trigger:
      - platform: numeric_state
        entity_id: sensor.teso_60skf2_15x_voertuig_tm_6_50m_tx
        below: 3
    action:
      - service: notify.mobile_app
        data:
          message: "Let op: je hebt nog maar {{ states('sensor.teso_60skf2_15x_voertuig_tm_6_50m_tx') }} TESO overtochten!"
```
