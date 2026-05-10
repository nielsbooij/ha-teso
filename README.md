![logo](custom_components/teso/images/icon.png)

# TESO Veerboot - Home Assistant Integratie

Volgt het aantal resterende overtochten op je TESO-passen en e-tickets via het Mijn TESO portaal.

## Functies

- **Resterende overtochten** per pas of e-ticket
- **Gekoppeld kenteken** per pas
- **Laatste overtocht** datum en tijd
- Automatisch verversen elke 5 minuten
- Apparaatstructuur per TESO-pas / Ticket

## Installatie

### Handmatig

1. Kopieer de map `custom_components/teso/` naar je Home Assistant `custom_components/` map.
2. Herstart Home Assistant.
3. Ga naar **Instellingen → Apparaten & Diensten → Integratie toevoegen**.
4. Zoek op **TESO** en volg de stappen.

### Via HACS

1. Voeg `https://github.com/nielsbooij/ha-teso` toe als aangepaste repository in HACS.
2. Installeer de **TESO Veerboot** integratie.
3. Herstart Home Assistant.
4. Ga naar **Instellingen → Apparaten & Diensten → Integratie toevoegen**.
5. Zoek op **TESO** en volg de stappen.

## Sensoren

Per pas worden de volgende sensoren aangemaakt:

| Sensor | Beschrijving |
|--------|-------------|
| Resterende overtochten | Aantal resterende overtochten per product |
| Gekoppeld kenteken | Het aan de pas gekoppelde kenteken |
| Laatste overtocht | Datum en tijd van de laatste overtocht |

Per e-ticket word de volgende sensor aangemaakt

| Sensor | Beschrijving |
|--------|-------------|
| Resterende overtochten | Aantal resterende overtochten per product |

## Gebruik in automatiseringen

Stuur een melding als je nog maar 2 overtochten over hebt:

```yaml
automation:
  - alias: "TESO bijna op"
    trigger:
      - platform: numeric_state
        entity_id: sensor.teso_pas_2514921229_resterende_overtochten
        below: 3
    action:
      - service: notify.mobile_app
        data:
          message: "Let op: je hebt nog maar {{ states('sensor.teso_pas_2514921229_resterende_overtochten') }} TESO overtochten!"
```


## Custom teso card
in de www map vind je een custom card die per pas / e-ticked de status weergeeft. 
bij de e-ticket wordt ook de QR-code getoond wanneer er op het salde geklikt word. 

- plaats de teso-card.js in /www/ 
- voeg in dasboards bij bronnen de verwijzing /local/teso-card.js toe. 
- voeg de kaart toe door een custom card te vullen met ;

```yaml
type: custom:teso-card
```

