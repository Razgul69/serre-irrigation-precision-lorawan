// Contrôleur d'électrovanne LoRaWAN avec débitmètre
// Downlink port 1 : [0x01] ouvrir, [0x00] fermer, [0x02 vol_H vol_L] ouvrir avec limite volume (x100 mL)
// Uplink port 2   : [état(1) | volume_cycle_mL(4) | volume_total_L_x10(2) | uptime_min(2)]

#include <Arduino.h>
#include <lmic.h>
#include <hal/hal.h>
#include <SPI.h>
#include "config.h"

volatile uint32_t flowPulses = 0;
uint32_t cycleStartPulses = 0;
uint32_t valveOpenedAt = 0;
uint32_t volumeLimitMl = 0;   // 0 = pas de limite volume
bool valveOpen = false;
uint32_t totalPulses = 0;

static osjob_t sendjob;

const lmic_pinmap lmic_pins = {
    .nss = PIN_LMIC_NSS,
    .rxtx = LMIC_UNUSED_PIN,
    .rst = PIN_LMIC_RST,
    .dio = {PIN_LMIC_DIO0, PIN_LMIC_DIO1, PIN_LMIC_DIO2},
};

void os_getArtEui(u1_t* buf) { memcpy_P(buf, APPEUI, 8); }
void os_getDevEui(u1_t* buf) { memcpy_P(buf, DEVEUI, 8); }
void os_getDevKey(u1_t* buf) { memcpy_P(buf, APPKEY, 16); }

void IRAM_ATTR onFlowPulse() { flowPulses++; }

uint32_t cycleVolumeMl() {
    return (uint32_t)((flowPulses - cycleStartPulses) * 1000.0f / FLOW_PULSES_PER_LITER);
}

void openValve(uint32_t limitMl) {
    cycleStartPulses = flowPulses;
    volumeLimitMl = limitMl;
    valveOpenedAt = millis();
    valveOpen = true;
    digitalWrite(PIN_VALVE, HIGH);
    Serial.printf("[VANNE] OUVERTE (limite %lu mL)\n", limitMl);
}

void closeValve() {
    digitalWrite(PIN_VALVE, LOW);
    if (valveOpen) {
        totalPulses += flowPulses - cycleStartPulses;
        Serial.printf("[VANNE] FERMEE, volume cycle = %lu mL\n", cycleVolumeMl());
    }
    valveOpen = false;
}

void sendStatus(osjob_t* j) {
    if (LMIC.opmode & OP_TXRXPEND) {
        os_setTimedCallback(&sendjob, os_getTime() + sec2osticks(TX_INTERVAL_S), sendStatus);
        return;
    }
    uint32_t volMl = valveOpen ? cycleVolumeMl() : 0;
    uint16_t totalLx10 = (uint16_t)(totalPulses * 10.0f / FLOW_PULSES_PER_LITER);
    uint16_t uptimeMin = (uint16_t)(millis() / 60000UL);
    uint8_t payload[9];
    payload[0] = valveOpen ? 1 : 0;
    payload[1] = volMl >> 24; payload[2] = volMl >> 16; payload[3] = volMl >> 8; payload[4] = volMl;
    payload[5] = totalLx10 >> 8; payload[6] = totalLx10;
    payload[7] = uptimeMin >> 8; payload[8] = uptimeMin;
    LMIC_setTxData2(2, payload, sizeof(payload), 0);
    os_setTimedCallback(&sendjob, os_getTime() + sec2osticks(TX_INTERVAL_S), sendStatus);
}

void onEvent(ev_t ev) {
    switch (ev) {
        case EV_JOINED:
            Serial.println("[LORA] Join OK");
            LMIC_setLinkCheckMode(0);
            sendStatus(&sendjob);
            break;
        case EV_TXCOMPLETE:
            if (LMIC.dataLen > 0) {  // downlink reçu
                uint8_t* d = LMIC.frame + LMIC.dataBeg;
                if (d[0] == 0x00) closeValve();
                else if (d[0] == 0x01) openValve(0);
                else if (d[0] == 0x02 && LMIC.dataLen >= 3)
                    openValve(((uint32_t)(d[1] << 8 | d[2])) * 100UL);  // x100 mL
            }
            break;
        default:
            break;
    }
}

void setup() {
    Serial.begin(115200);
    pinMode(PIN_VALVE, OUTPUT);
    digitalWrite(PIN_VALVE, LOW);
    pinMode(PIN_FLOWMETER, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(PIN_FLOWMETER), onFlowPulse, FALLING);
    os_init();
    LMIC_reset();
    LMIC_startJoining();
    Serial.println("[BOOT] Controleur vanne LoRaWAN pret");
}

void loop() {
    os_runloop_once();
    // Sécurités locales : fonctionnent même si le réseau tombe
    if (valveOpen) {
        if (millis() - valveOpenedAt > MAX_OPEN_DURATION_MS) {
            Serial.println("[SECU] Duree max atteinte");
            closeValve();
        }
        uint32_t limit = volumeLimitMl ? volumeLimitMl : MAX_VOLUME_ML;
        if (cycleVolumeMl() >= limit) {
            Serial.println("[SECU] Volume max atteint");
            closeValve();
        }
    }
}
