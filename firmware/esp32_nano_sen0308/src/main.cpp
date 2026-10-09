// Arduino Nano ESP32 — lecture DFRobot SEN0308 (sonde capacitive etanche)
// Sortie serie CSV : millis_ms,mv,index_pct,vwc_pct   (115200 bauds)
// Commandes serie : a = capture AIR (30 s), w = capture EAU (30 s), c = afficher constantes, h = aide
// Variante LoRaWAN (-D WITH_LORAWAN) : uplink port 3 = [mV(2) | index_x10(2) | vwc_x10(2)]

#include <Arduino.h>
#include "config.h"
#ifdef WITH_LORAWAN
#include <hal/hal.h>
#include <SPI.h>
#endif

static float lastMv = NAN, lastIndex = NAN, lastVwc = NAN;

// Mediane de SEN_SAMPLES lectures calibrees (analogReadMilliVolts corrige l'ADC ESP32)
float readSensorMv() {
    uint32_t buf[SEN_SAMPLES];
    for (int i = 0; i < SEN_SAMPLES; i++) {
        buf[i] = analogReadMilliVolts(PIN_SEN0308);
        delayMicroseconds(200);
    }
    for (int i = 1; i < SEN_SAMPLES; i++) {        // tri par insertion
        uint32_t v = buf[i]; int j = i - 1;
        while (j >= 0 && buf[j] > v) { buf[j + 1] = buf[j]; j--; }
        buf[j + 1] = v;
    }
    return (buf[SEN_SAMPLES / 2 - 1] + buf[SEN_SAMPLES / 2]) / 2.0f;
}

float indexPct(float mv) {
    float idx = 100.0f * (AIR_MV - mv) / (AIR_MV - WATER_MV);
    return constrain(idx, 0.0f, 100.0f);
}

float vwcPct(float mv) {
#if USE_VWC
    return max(0.0f, VWC_A * mv + VWC_B);
#else
    (void)mv;
    return NAN;
#endif
}

// Moyenne sur 30 s pour la calibration air / eau (niveau 1)
void captureReference(const char* label) {
    Serial.printf("# Capture %s : ne pas bouger la sonde pendant 30 s...\n", label);
    double sum = 0, sum2 = 0; int n = 0;
    uint32_t t0 = millis();
    while (millis() - t0 < 30000UL) {
        float mv = readSensorMv();
        sum += mv; sum2 += (double)mv * mv; n++;
        delay(250);
    }
    double mean = sum / n;
    double sd = sqrt(max(0.0, sum2 / n - mean * mean));
    Serial.printf("# %s_MV = %.0f mV  (ecart-type %.1f mV, n=%d) -> a reporter dans config.h\n",
                  label, mean, sd, n);
}

void handleSerial() {
    while (Serial.available()) {
        char c = Serial.read();
        if (c == 'a' || c == 'A') captureReference("AIR");
        else if (c == 'w' || c == 'W') captureReference("WATER");
        else if (c == 'c' || c == 'C')
            Serial.printf("# AIR_MV=%.0f WATER_MV=%.0f USE_VWC=%d VWC_A=%g VWC_B=%g\n",
                          AIR_MV, WATER_MV, USE_VWC, (double)VWC_A, (double)VWC_B);
        else if (c == 'h' || c == 'H')
            Serial.println("# a=capture air  w=capture eau  c=constantes  h=aide");
    }
}

#ifdef WITH_LORAWAN
static osjob_t sendjob;
const lmic_pinmap lmic_pins = {
    .nss = PIN_LMIC_NSS, .rxtx = LMIC_UNUSED_PIN, .rst = PIN_LMIC_RST,
    .dio = {PIN_LMIC_DIO0, PIN_LMIC_DIO1, PIN_LMIC_DIO2},
};
void os_getArtEui(u1_t* buf) { memcpy_P(buf, APPEUI, 8); }
void os_getDevEui(u1_t* buf) { memcpy_P(buf, DEVEUI, 8); }
void os_getDevKey(u1_t* buf) { memcpy_P(buf, APPKEY, 16); }

void sendMeasure(osjob_t*) {
    if (!(LMIC.opmode & OP_TXRXPEND)) {
        uint16_t mv = (uint16_t)lastMv;
        uint16_t idx = (uint16_t)(lastIndex * 10);
        uint16_t vwc = isnan(lastVwc) ? 0xFFFF : (uint16_t)(lastVwc * 10);
        uint8_t p[6] = { (uint8_t)(mv >> 8), (uint8_t)mv, (uint8_t)(idx >> 8), (uint8_t)idx,
                         (uint8_t)(vwc >> 8), (uint8_t)vwc };
        LMIC_setTxData2(3, p, sizeof(p), 0);
    }
    os_setTimedCallback(&sendjob, os_getTime() + sec2osticks(TX_INTERVAL_S), sendMeasure);
}

void onEvent(ev_t ev) {
    if (ev == EV_JOINED) {
        Serial.println("# [LORA] Join OK");
        LMIC_setLinkCheckMode(0);
        sendMeasure(&sendjob);
    }
}
#endif

void setup() {
    Serial.begin(115200);
    delay(1500);
    analogReadResolution(12);
    analogSetPinAttenuation(PIN_SEN0308, ADC_11db);   // pleine echelle ~3,1 V
    Serial.println("# SEN0308 Nano ESP32 — h pour l'aide");
    Serial.println("millis_ms,mv,index_pct,vwc_pct");
#ifdef WITH_LORAWAN
    os_init();
    LMIC_reset();
    LMIC_startJoining();
#endif
}

void loop() {
    static uint32_t lastPrint = 0;
#ifdef WITH_LORAWAN
    os_runloop_once();
#endif
    handleSerial();
    if (millis() - lastPrint >= MEASURE_PERIOD_MS) {
        lastPrint = millis();
        lastMv = readSensorMv();
        lastIndex = indexPct(lastMv);
        lastVwc = vwcPct(lastMv);
        Serial.printf("%lu,%.0f,%.1f,", lastPrint, lastMv, lastIndex);
        if (isnan(lastVwc)) Serial.println(); else Serial.printf("%.1f\n", lastVwc);
    }
}
