class TesoCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._selectedDevice = null;
    this._initialized = false;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._initialized) {
      this._initCard();
    } else {
      this._updateValues();
    }
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

    for (const entityId in hass.states) {
      let pasNummer = null;
      let type = null;

      const kentekenMatch = entityId.match(/^sensor\.gekoppeld_kenteken_(\d+)$/);
      const overtachtMatch = entityId.match(/^sensor\.laatste_overtocht_(\d+)$/);
      const saldoMatch = entityId.match(/^sensor\.resterende_overtochten_/);

      if (kentekenMatch) {
        pasNummer = kentekenMatch[1];
        type = "kenteken";
      } else if (overtachtMatch) {
        pasNummer = overtachtMatch[1];
        type = "laatste_overtocht";
      } else if (saldoMatch) {
        const state = hass.states[entityId];
        if (state && state.attributes && state.attributes.pasnummer) {
          pasNummer = String(state.attributes.pasnummer);
          type = "saldo";
        }
      }

      if (!pasNummer || !type) continue;

      if (!devices[pasNummer]) {
        devices[pasNummer] = { id: pasNummer, name: `TESO-pas ${pasNummer}`, entities: {} };
      }
      devices[pasNummer].entities[type] = entityId;
    }

    return Object.values(devices).sort((a, b) => a.id.localeCompare(b.id));
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
    if (stateObj.attributes.product) return stateObj.attributes.product;
    const friendlyName = stateObj.attributes.friendly_name || "";
    const match = friendlyName.match(/resterende overtochten\s*[-]\s*(.+)/i);
    if (match) return match[1].trim();
    return null;
  }

  _formatDate(dateStr) {
    if (!dateStr || dateStr === "unknown" || dateStr === "unavailable") return "-";
    try {
      const date = new Date(dateStr);
      if (isNaN(date)) return dateStr;
      return date.toLocaleString("nl-NL", {
        day: "2-digit", month: "2-digit", year: "numeric",
        hour: "2-digit", minute: "2-digit",
      });
    } catch { return dateStr; }
  }

  _initCard() {
    const devices = this._getTesoDevices();
    if (devices.length === 0) {
      this.shadowRoot.innerHTML = `<ha-card><div style="padding:16px">Geen TESO-passen gevonden.</div></ha-card>`;
      return;
    }

    if (!this._selectedDevice || !devices.find((d) => d.id === this._selectedDevice)) {
      this._selectedDevice = devices[0].id;
    }

    const dropdownOptions = devices
      .map((d) => `<option value="${d.id}" ${d.id === this._selectedDevice ? "selected" : ""}>${d.name}</option>`)
      .join("");

    this.shadowRoot.innerHTML = `
      <style>
        :host { --teso-yellow: #f5c400; --radius: 12px; }
        ha-card { border-radius: var(--radius); overflow: hidden; font-family: var(--paper-font-body1_-_font-family, sans-serif); }
        .header { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px 10px; border-bottom: 1px solid var(--divider-color, rgba(255,255,255,0.08)); }
        .header-left { display: flex; align-items: center; gap: 10px; }
        .teso-logo { font-size: 18px; font-weight: 800; letter-spacing: 3px; color: var(--primary-text-color); }
        .teso-crown { color: var(--teso-yellow); font-size: 14px; }
        select { background: var(--card-background-color, #1c1c1c); color: var(--primary-text-color); border: 1px solid var(--divider-color, rgba(255,255,255,0.15)); border-radius: 8px; padding: 6px 10px; font-size: 13px; cursor: pointer; outline: none; max-width: 180px; }
        select:focus { border-color: var(--teso-yellow); }
        .body { padding: 12px 16px 16px; display: flex; flex-direction: column; gap: 4px; }
        .row { display: flex; align-items: center; gap: 12px; padding: 10px 8px; border-radius: 8px; transition: background 0.15s; }
        .row:hover { background: var(--secondary-background-color, rgba(255,255,255,0.04)); }
        .row-icon { display: flex; align-items: center; justify-content: center; width: 36px; height: 36px; border-radius: 8px; background: var(--secondary-background-color, rgba(255,255,255,0.06)); flex-shrink: 0; }
        .row-icon ha-icon { --mdc-icon-size: 20px; color: var(--teso-yellow); }
        .row-content { display: flex; flex-direction: column; gap: 1px; flex: 1; min-width: 0; }
        .row-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; color: var(--secondary-text-color); font-weight: 500; }
        .row-value { font-size: 15px; color: var(--primary-text-color); font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .saldo-value { font-size: 22px; font-weight: 700; color: var(--teso-yellow); }
        .divider { height: 1px; background: var(--divider-color, rgba(255,255,255,0.06)); margin: 2px 8px; }
        .row-kenteken { display: none; }
      </style>

      <ha-card>
        <div class="header">
          <div class="header-left">
            <span class="teso-crown">&#9819;</span>
            <span class="teso-logo">TESO</span>
          </div>
          ${devices.length > 1
            ? `<select id="pas-select">${dropdownOptions}</select>`
            : `<span style="font-size:13px;color:var(--secondary-text-color)">${devices[0].name}</span>`
          }
        </div>

        <div class="body">
          <div class="row row-product">
            <div class="row-icon"><ha-icon icon="mdi:card-account-details-outline"></ha-icon></div>
            <div class="row-content">
              <span class="row-label">Product</span>
              <span class="row-value" id="val-product"></span>
            </div>
          </div>
          <div class="divider divider-product"></div>

          <div class="row">
            <div class="row-icon"><ha-icon id="icon-saldo" icon="mdi:car"></ha-icon></div>
            <div class="row-content">
              <span class="row-label">Saldo</span>
              <span class="row-value saldo-value" id="val-saldo"></span>
            </div>
          </div>

          <div class="divider divider-kenteken" style="display:none"></div>
          <div class="row row-kenteken">
            <div class="row-icon"><ha-icon icon="mdi:license"></ha-icon></div>
            <div class="row-content">
              <span class="row-label">Kenteken</span>
              <span class="row-value" id="val-kenteken"></span>
            </div>
          </div>

          <div class="divider"></div>

          <div class="row">
            <div class="row-icon"><ha-icon icon="mdi:ferry"></ha-icon></div>
            <div class="row-content">
              <span class="row-label">Laatste overtocht</span>
              <span class="row-value" id="val-laatste"></span>
            </div>
          </div>
        </div>
      </ha-card>
    `;

    const select = this.shadowRoot.getElementById("pas-select");
    if (select) {
      select.addEventListener("change", (e) => {
        this._selectedDevice = e.target.value;
        this._updateValues();
      });
    }

    this._initialized = true;
    this._updateValues();
  }

  _updateValues() {
    const hass = this._hass;
    const devices = this._getTesoDevices();
    if (devices.length === 0 || !this._initialized) return;

    const device = devices.find((d) => d.id === this._selectedDevice) || devices[0];
    const { entities } = device;

    const salState = entities.saldo ? hass.states[entities.saldo] : null;
    const kentekenState = entities.kenteken ? hass.states[entities.kenteken] : null;
    const overtachtState = entities.laatste_overtocht ? hass.states[entities.laatste_overtocht] : null;

    const saldo = salState ? salState.state : "-";
    const kenteken = kentekenState ? kentekenState.state : null;
    const heeftKenteken = kenteken && kenteken !== "unknown" && kenteken !== "unavailable" && kenteken !== "";
    const laatste = overtachtState ? this._formatDate(overtachtState.state) : "-";
    const productName = this._extractProductName(entities.saldo);
    const productIcon = this._getProductIcon(productName);

    const root = this.shadowRoot;

    const valProduct = root.getElementById("val-product");
    const rowProduct = root.querySelector(".row-product");
    const dividerProduct = root.querySelector(".divider-product");
    if (valProduct) valProduct.textContent = productName || "";
    if (rowProduct) rowProduct.style.display = productName ? "flex" : "none";
    if (dividerProduct) dividerProduct.style.display = productName ? "block" : "none";

    const valSaldo = root.getElementById("val-saldo");
    if (valSaldo) valSaldo.textContent = `${saldo} overtochten`;

    const iconSaldo = root.getElementById("icon-saldo");
    if (iconSaldo) iconSaldo.setAttribute("icon", productIcon);

    const valKenteken = root.getElementById("val-kenteken");
    const rowKenteken = root.querySelector(".row-kenteken");
    const dividerKenteken = root.querySelector(".divider-kenteken");
    if (valKenteken) valKenteken.textContent = kenteken || "";
    if (rowKenteken) rowKenteken.style.display = heeftKenteken ? "flex" : "none";
    if (dividerKenteken) dividerKenteken.style.display = heeftKenteken ? "block" : "none";

    const valLaatste = root.getElementById("val-laatste");
    if (valLaatste) valLaatste.textContent = laatste;
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
