class TesoCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._selectedDevice = null;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  setConfig(config) {
    this._config = config;
  }

  getCardSize() {
    return 4;
  }

  _getTesoDevices() {
    const hass = this._hass;
    if (!hass || !hass.states) return [];

    const devices = {};

    Object.keys(hass.states).forEach((entityId) => {
      const stateObj = hass.states[entityId];
      if (!stateObj) return;

      const attrs = stateObj.attributes || {};

      // Groepeer op pasnummer attribuut
      if (attrs.pasnummer !== undefined) {
        const pasNummer = String(attrs.pasnummer);
        const deviceName = `TESO-pas ${pasNummer}`;

        if (!devices[pasNummer]) {
          devices[pasNummer] = {
            id: pasNummer,
            name: deviceName,
            entities: {},
          };
        }

        if (entityId.includes("gekoppeld_kenteken")) {
          devices[pasNummer].entities.kenteken = entityId;
        } else if (entityId.includes("laatste_overtocht")) {
          devices[pasNummer].entities.laatste_overtocht = entityId;
        } else if (entityId.includes("resterende_overtochten")) {
          devices[pasNummer].entities.saldo = entityId;
        }
      }
    });

    const result = Object.values(devices).sort((a, b) => a.id.localeCompare(b.id));
    console.log("[TESO-card] gevonden apparaten:", result);
    return result;
  }

  _getProductIcon(productName) {
    if (!productName) return "mdi:ticket";
    const lower = productName.toLowerCase();
    if (lower.includes("voetganger")) return "mdi:walk";
    if (lower.includes("fiets") || lower.includes("bromfiets")) return "mdi:bicycle";
    if (lower.includes("lang voertuig") || lower.includes("vrachtwagen") || lower.includes("caravan")) return "mdi:truck";
    if (lower.includes("voertuig") || lower.includes("auto") || lower.includes("busje") || lower.includes("camper")) return "mdi:car";
    return "mdi:ticket";
  }

  _extractProductName(entityId) {
    if (!entityId || !this._hass) return null;
    const stateObj = this._hass.states[entityId];
    if (!stateObj) return null;

    // Gebruik het product attribuut direct
    if (stateObj.attributes.product) return stateObj.attributes.product;

    // Fallback: vriendelijke naam
    const friendlyName = stateObj.attributes.friendly_name || "";
    const match = friendlyName.match(/resterende overtochten\s*[-–]\s*(.+)/i);
    if (match) return match[1].trim();

    return null;
  }

  _formatDate(dateStr) {
    if (!dateStr || dateStr === "unknown" || dateStr === "unavailable") return "–";
    try {
      const date = new Date(dateStr);
      if (isNaN(date)) return dateStr;
      return date.toLocaleString("nl-NL", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
    }
  }

  _render() {
    const hass = this._hass;
    if (!hass) return;

    const devices = this._getTesoDevices();
    if (devices.length === 0) {
      this.shadowRoot.innerHTML = `<ha-card><div style="padding:16px">Geen TESO-passen gevonden.</div></ha-card>`;
      return;
    }

    // Selecteer standaard het eerste apparaat
    if (!this._selectedDevice || !devices.find((d) => d.id === this._selectedDevice)) {
      this._selectedDevice = devices[0].id;
    }

    const device = devices.find((d) => d.id === this._selectedDevice);
    const { entities } = device;

    const salState = entities.saldo ? hass.states[entities.saldo] : null;
    const kentekenState = entities.kenteken ? hass.states[entities.kenteken] : null;
    const overtachtState = entities.laatste_overtocht ? hass.states[entities.laatste_overtocht] : null;

    const saldo = salState ? salState.state : "–";
    const kenteken = kentekenState ? kentekenState.state : null;
    const heeftKenteken = kenteken && kenteken !== "unknown" && kenteken !== "unavailable" && kenteken !== "";
    const laatste = overtachtState ? this._formatDate(overtachtState.state) : "–";

    const productName = this._extractProductName(entities.saldo);
    const productIcon = this._getProductIcon(productName);

    const dropdownOptions = devices
      .map(
        (d) =>
          `<option value="${d.id}" ${d.id === this._selectedDevice ? "selected" : ""}>${d.name}</option>`
      )
      .join("");

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          --teso-yellow: #f5c400;
          --teso-dark: #1e1e1e;
          --radius: 12px;
        }

        ha-card {
          border-radius: var(--radius);
          overflow: hidden;
          font-family: var(--paper-font-body1_-_font-family, sans-serif);
        }

        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 14px 16px 10px;
          border-bottom: 1px solid var(--divider-color, rgba(255,255,255,0.08));
        }

        .header-left {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .teso-logo {
          font-size: 18px;
          font-weight: 800;
          letter-spacing: 3px;
          color: var(--primary-text-color);
        }

        .teso-crown {
          color: var(--teso-yellow);
          font-size: 14px;
        }

        select {
          background: var(--card-background-color, #1c1c1c);
          color: var(--primary-text-color);
          border: 1px solid var(--divider-color, rgba(255,255,255,0.15));
          border-radius: 8px;
          padding: 6px 10px;
          font-size: 13px;
          cursor: pointer;
          outline: none;
          max-width: 180px;
        }

        select:focus {
          border-color: var(--teso-yellow);
        }

        .body {
          padding: 12px 16px 16px;
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .row {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 10px 8px;
          border-radius: 8px;
          transition: background 0.15s;
        }

        .row:hover {
          background: var(--secondary-background-color, rgba(255,255,255,0.04));
        }

        .row-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 36px;
          height: 36px;
          border-radius: 8px;
          background: var(--secondary-background-color, rgba(255,255,255,0.06));
          flex-shrink: 0;
        }

        .row-icon ha-icon {
          --mdc-icon-size: 20px;
          color: var(--teso-yellow);
        }

        .row-content {
          display: flex;
          flex-direction: column;
          gap: 1px;
          flex: 1;
          min-width: 0;
        }

        .row-label {
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 0.8px;
          color: var(--secondary-text-color);
          font-weight: 500;
        }

        .row-value {
          font-size: 15px;
          color: var(--primary-text-color);
          font-weight: 500;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .saldo-value {
          font-size: 22px;
          font-weight: 700;
          color: var(--teso-yellow);
        }

        .divider {
          height: 1px;
          background: var(--divider-color, rgba(255,255,255,0.06));
          margin: 2px 8px;
        }
      </style>

      <ha-card>
        <div class="header">
          <div class="header-left">
            <span class="teso-crown">♛</span>
            <span class="teso-logo">TESO</span>
          </div>
          ${
            devices.length > 1
              ? `<select id="pas-select">${dropdownOptions}</select>`
              : `<span style="font-size:13px;color:var(--secondary-text-color)">${device.name}</span>`
          }
        </div>

        <div class="body">
          ${
            productName
              ? `
            <div class="row">
              <div class="row-icon"><ha-icon icon="mdi:card-account-details-outline"></ha-icon></div>
              <div class="row-content">
                <span class="row-label">Product</span>
                <span class="row-value">${productName}</span>
              </div>
            </div>
            <div class="divider"></div>
          `
              : ""
          }

          <div class="row">
            <div class="row-icon"><ha-icon icon="${productIcon}"></ha-icon></div>
            <div class="row-content">
              <span class="row-label">Saldo</span>
              <span class="row-value saldo-value">${saldo} overtochten</span>
            </div>
          </div>

          ${
            heeftKenteken
              ? `
            <div class="divider"></div>
            <div class="row">
              <div class="row-icon"><ha-icon icon="mdi:license"></ha-icon></div>
              <div class="row-content">
                <span class="row-label">Kenteken</span>
                <span class="row-value">${kenteken}</span>
              </div>
            </div>
          `
              : ""
          }

          <div class="divider"></div>

          <div class="row">
            <div class="row-icon"><ha-icon icon="mdi:ferry"></ha-icon></div>
            <div class="row-content">
              <span class="row-label">Laatste overtocht</span>
              <span class="row-value">${laatste}</span>
            </div>
          </div>
        </div>
      </ha-card>
    `;

    // Event listener voor dropdown
    const select = this.shadowRoot.getElementById("pas-select");
    if (select) {
      select.addEventListener("change", (e) => {
        this._selectedDevice = e.target.value;
        this._render();
      });
    }
  }
}

customElements.define("teso-card", TesoCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "teso-card",
  name: "TESO Veerboot",
  description: "Toont TESO-pas informatie inclusief saldo, kenteken en laatste overtocht.",
  preview: false,
});

