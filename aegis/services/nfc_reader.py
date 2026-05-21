# AEGIS - NowBlackout ENSIBS 2025
# Last modified: 2026-01-26
# Link the NFC reader hardware to AEGIS to read UID from NFC tags

import time
import nfc

class NFCReader:
    """
    Service NFC : lecture UID uniquement
    - Pas de variables globales
    - Ressource matérielle encapsulée
    - Timeout configurable
    """

    def __init__(self, device: str = "usb", timeout: int = 30):
        self.device = device
        self.timeout = timeout
        self._clf = None
        self._uid = None

    def _on_connect(self, tag):
        # UID propre et stable
        self._uid = tag.identifier.hex().upper()
        return True  # stop après lecture

    def read(self) -> str | None:
        start = time.time()

        try:
            self._clf = nfc.ContactlessFrontend(self.device)
        except IOError:
            raise RuntimeError("Lecteur NFC non détecté")

        while time.time() - start < self.timeout:
            self._uid = None

            self._clf.connect(
                rdwr={"on-connect": self._on_connect},
                terminate=lambda: self._uid is not None
            )

            if self._uid:
                self._clf.close()
                return self._uid

        self._clf.close()
        return None
