/**
 * WEB NFC SPOOL READER & SIMULATOR 🏷️
 * Uses browser NDEFReader API (Web NFC) or Fallback Interactive Simulator
 */

class NFCSpoolSystem {
  constructor() {
    this.isSupported = 'NDEFReader' in window;
    this.reader = null;
    this.activeFilamentId = null;
  }

  async startNFCScan(onTagDetected) {
    if (!this.isSupported) {
      console.warn("Web NFC API not supported on this browser/device. Opening Desktop NFC Simulator...");
      this.openNfcSimulatorModal(onTagDetected);
      return;
    }

    try {
      this.reader = new NDEFReader();
      await this.reader.scan();
      showToast("NFC Scanner Active! Hold NFC tag near your phone 📱", "info");

      this.reader.addEventListener("reading", ({ message, serialNumber }) => {
        console.log(`NFC Tag Serial Number: ${serialNumber}`);
        let decodedPayload = "";

        for (const record of message.records) {
          const textDecoder = new TextDecoder(record.encoding);
          decodedPayload += textDecoder.decode(record.data);
        }

        onTagDetected({
          tag_uid: serialNumber || "NFC-" + Math.random().toString(36).substr(2, 6).toUpperCase(),
          payload: decodedPayload
        });
      });

    } catch (error) {
      console.error("NFC Scanning Error:", error);
      showToast("Could not access NFC hardware. Launching NFC Simulator.", "warning");
      this.openNfcSimulatorModal(onTagDetected);
    }
  }

  async writeNFCTag(tagUid, filamentData) {
    if (!this.isSupported) {
      showToast(`[Simulated NFC Write] Tag '${tagUid}' written with spool data!`, "success");
      return true;
    }

    try {
      const writer = new NDEFReader();
      await writer.write({
        records: [
          { recordType: "text", data: JSON.stringify(filamentData) }
        ]
      });
      showToast("Successfully wrote filament data to NFC tag!", "success");
      return true;
    } catch (err) {
      console.error("NFC Write Error:", err);
      showToast("NFC Write failed: " + err.message, "danger");
      return false;
    }
  }

  openNfcSimulatorModal(onTagDetected) {
    const modal = document.getElementById('nfc-modal');
    if (modal) {
      modal.classList.add('active');
    }
    // Bind simulator scan trigger button
    const scanBtn = document.getElementById('nfc-sim-scan-btn');
    if (scanBtn) {
      scanBtn.onclick = () => {
        const tagInput = document.getElementById('nfc-sim-tag-input').value || "NFC-MINION-001";
        const weightInput = parseFloat(document.getElementById('nfc-sim-weight-input').value) || 0.75;
        
        onTagDetected({
          tag_uid: tagInput,
          current_weight_kg: weightInput
        });
        
        if (modal) modal.classList.remove('active');
      };
    }
  }
}

const nfcSystem = new NFCSpoolSystem();
