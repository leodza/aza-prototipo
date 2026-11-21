#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>
#include <U8g2lib.h>
#include <Adafruit_NeoPixel.h>
#include <Adafruit_AHTX0.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <Preferences.h>
#include <math.h>

// =========================
// PINES E INSTANCIAS
// =========================
#define PIN_CS 39
#define PIN_DC 38
#define PIN_SCK 40
#define PIN_SDA 41
#define PIN_RST 5 
#define PIN_RGB 10
#define PIN_SW 16
#define PIN_AD2 18 
#define TRIG 7
#define ECHO 8
#define PIN_BOMBA 15 

U8G2_SSD1309_128X64_NONAME0_F_4W_HW_SPI oled(U8G2_R0, PIN_CS, PIN_DC);
Adafruit_NeoPixel led(1, PIN_RGB, NEO_GRB + NEO_KHZ800);
Adafruit_AHTX0 aht;
Preferences preferences;

// =========================
// VARIABLES GLOBALES (REGLA DE ORO)
// =========================
static bool deviceConnected = false; 
static bool sistemaActivo = false;
static bool bootSafeMode = true;
static int perfilActivo = 0;

// Variables de Alarma Mejoradas
static bool popupActivo = false;
static bool bloqueoPorVacio = false;
static uint32_t msInicioPopup = 0;
static uint32_t msUltimaAlarmaConfirmada = 0;
static const char* mensajePopup = "";
static String valorPopupDetalle = "";
static const char* popupFooter = "";
static bool popupEsRemoto = false;
enum WaterAlarmState { WATER_OK, WATER_LOW, WATER_EMPTY };
static WaterAlarmState waterAlarmState = WATER_OK;

const float UMBRAL_BAJO = 10.0; 
const float UMBRAL_VACIO = 5.0;    
const uint32_t LAPSUS_ALARMAS = 5000; // 5 segundos entre alarmas
const uint32_t TIMEOUT_STANDBY = 15000; // Standby de 15 segundos

// Constantes Algoritmo
static const int   TR_MIN_HW   = 1;
static const int   TD_MIN_HW   = 10;
static const float VPD_REF_DAY   = 1.2f;
static const float VPD_REF_NIGHT = 0.6f;
static const float E_MAX      = 0.20f;
static const float TERM_CLAMP = 0.30f;
static const float K_TD = 1.0f;
static const float K_TR = 0.3f;
static const float W_VPD = 0.65f;
static const float W_U   = 0.35f;
static const float ALPHA_DOTL = 0.90f;
static const float BETA_UREF = 0.01f;
static const int   TR_SURVIVAL = 30;
static const int   TD_SURVIVAL = 30;

// =========================
// BITMAP Y VARIABLES LOGO
// =========================
const uint8_t logo_bits[1024] PROGMEM = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0xc0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x06, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0c, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x08, 0x30, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x10, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x30, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x20, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x40, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xc0, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03, 0x00, 0x00, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x04, 0x00, 0x00, 0x60, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0c, 0x00, 0x00, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x08, 0x00, 0x00, 0x30, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x10, 0x00, 0x00, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x10, 0x00, 0x00, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x20, 0x00, 0x00, 0x0c, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x60, 0x00, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xc0, 0x00, 0x03, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x00, 0x06, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x80, 0x00, 0x0e, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x1e, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x3e, 0x00, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0x7e, 0x00, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0xfe, 0x00, 0xc0, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x0f, 0x01, 0xfc, 0x00, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x04, 0x07, 0xc1, 0xfc, 0x00, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x04, 0x07, 0xf3, 0xfc, 0x00, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x04, 0x03, 0xf9, 0xf8, 0x00, 0x60, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x04, 0x03, 0xfd, 0xf0, 0xc0, 0x60, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x04, 0x01, 0xff, 0xef, 0xc0, 0x60, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x04, 0x01, 0xff, 0x3f, 0xc0, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x04, 0x01, 0xf7, 0x7f, 0xc0, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00, 0xfb, 0xff, 0xc0, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00, 0xff, 0xff, 0x80, 0xc0, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00, 0x7d, 0xff, 0x00, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x1d, 0xfe, 0x01, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x80, 0x01, 0xfc, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x01, 0x70, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x40, 0x01, 0x00, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x20, 0x00, 0x00, 0x0c, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x18, 0x00, 0x00, 0x18, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0c, 0x00, 0x00, 0x70, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x07, 0x00, 0x01, 0xc0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0xe0, 0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3f, 0xf8, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};
static uint8_t logoMinX = 127, logoMaxX = 0;
static uint16_t onList[8192];
static uint16_t onCount = 0, revealCursor = 0;

// =========================
// ESTRUCTURAS Y ESTADOS
// =========================
enum AppState { APP_OPENING, APP_LOGO_FIJO, APP_MENU_PRINCIPAL, APP_SUBMENU, APP_PANTALLA_ESTADO, APP_PANTALLA_CONEXION, APP_PANTALLA_RIEGO, APP_RIEGO_DETALLE };
AppState appState = APP_OPENING;

const char* subMenuOptions[] = {"ENCENDER", "STATUS", "MODOS RIEGO"};
const char* riegoOptions[] = {"RUCULA", "LECHUGA", "PAPA", "MANUAL", "VOLVER"};

struct Perfil { 
    const char* nombre; 
    int trDia; int tdDia; 
    int trNoche; int tdNoche; 
};

Perfil perfiles[] = {
    {"RUCULA", 100, 210, 100, 100}, 
    {"LECHUGA", 105, 360, 105, 360},
    {"PAPA", 900, 900, 900, 3600},
    {"MANUAL", 100, 210, 100, 100} 
};

static int menuIdx = 0, subMenuIdx = 0, riegoIdx = 0, campoFoco = 4;
static bool editandoParametro = false, oledSleeping = false, visualFeedback = false, ledOverride = false;
static uint32_t lastActivityMs = 0, lastFrameMs = 0, lastDebounceMs = 0, lastLedMs = 0, lastMinuteMs = 0;

static float tempC = 0, humPct = 0;
static int aguaPct = 0, horaInt = 0, minInt = 0;
static bool bombaEstado = false, horaSincronizada = false;
static uint32_t ultimoCambioBombaMs = 0;
String wifiNombreApp = "SIN SEÑAL";

static float u_ref_day[4] = {0.00005f, 0.00005f, 0.00005f, 0.00005f};
static float u_ref_night[4] = {0.00005f, 0.00005f, 0.00005f, 0.00005f};
static float L_prev = 0.0f, dotL = 0.0f;
static bool hasPrevLevel = false;
static int TR_calc = 0, TD_calc = 0;

void saveManualProfile() {
    preferences.putInt("man_tr_d", perfiles[3].trDia);
    preferences.putInt("man_td_d", perfiles[3].tdDia);
    preferences.putInt("man_tr_n", perfiles[3].trNoche);
    preferences.putInt("man_td_n", perfiles[3].tdNoche);
}

void loadManualProfile() {
    perfiles[3].trDia = preferences.getInt("man_tr_d", perfiles[3].trDia);
    perfiles[3].tdDia = preferences.getInt("man_td_d", perfiles[3].tdDia);
    perfiles[3].trNoche = preferences.getInt("man_tr_n", perfiles[3].trNoche);
    perfiles[3].tdNoche = preferences.getInt("man_td_n", perfiles[3].tdNoche);
}

// =========================
// LÓGICA DE ALARMAS MEJORADA
// =========================
void dispararPopup(const char* msg, String detalle, bool esBloqueo) {
    uint32_t now = millis();
    if (!popupActivo && (now - msUltimaAlarmaConfirmada > LAPSUS_ALARMAS)) {
        mensajePopup = msg;
        valorPopupDetalle = detalle;
        popupFooter = esBloqueo ? "BOMBA APAGADA" : "";
        popupEsRemoto = false;
        popupActivo = true;
        bloqueoPorVacio = esBloqueo;
        msInicioPopup = now;
        if (oledSleeping) { oled.setPowerSave(0); oledSleeping = false; }
        lastActivityMs = now; 
    }
}

void dispararPopupRemoto(const char* msg, String detalle) {
    mensajePopup = msg;
    valorPopupDetalle = detalle;
    popupFooter = "";
    popupEsRemoto = true;
    popupActivo = true;
    bloqueoPorVacio = false;
    msInicioPopup = millis();
    if (oledSleeping) {
        oled.setPowerSave(0);
        oledSleeping = false;
    }
}

// =========================
// MOTOR DEL ALGORITMO
// =========================
void ejecutarAlgoritmoAquaBrain() {
    bool dia = (horaInt >= 6 && horaInt < 20) || (horaInt == 20 && minInt == 0);
    if (waterAlarmState == WATER_LOW) {
        TR_calc = TR_SURVIVAL;
        TD_calc = TD_SURVIVAL;
        return;
    }
    if (!horaSincronizada) {
        TR_calc = 20;
        TD_calc = 20;
        return;
    }
    if (!sistemaActivo || perfilActivo == -1) {
        TR_calc = dia ? perfiles[riegoIdx].trDia : perfiles[riegoIdx].trNoche;
        TD_calc = dia ? perfiles[riegoIdx].tdDia : perfiles[riegoIdx].tdNoche;
        return;
    }
    int TR_base = dia ? perfiles[perfilActivo].trDia : perfiles[perfilActivo].trNoche;
    int TD_base = dia ? perfiles[perfilActivo].tdDia : perfiles[perfilActivo].tdNoche;
    float es = 0.6108f * expf((17.27f * tempC) / (tempC + 237.3f));
    float vpd = es * (1.0f - (humPct / 100.0f));
    float vpd_ref = dia ? VPD_REF_DAY : VPD_REF_NIGHT;
    float e_vpd = constrain((vpd - vpd_ref) / vpd_ref, -TERM_CLAMP, TERM_CLAMP);
    float u = max(0.0f, -dotL);
    float uRef = dia ? u_ref_day[perfilActivo] : u_ref_night[perfilActivo];
    if (uRef < 1e-6f) uRef = 1e-6f;
    float e_u = constrain((u - uRef) / uRef, -TERM_CLAMP, TERM_CLAMP);
    float E = constrain(W_VPD * e_vpd + W_U * e_u, -E_MAX, E_MAX);
    TD_calc = max((int)round(TD_base * (1.0f - K_TD * E)), (int)TD_MIN_HW);
    TR_calc = max((int)round(TR_base * (1.0f + K_TR * E)), (int)TR_MIN_HW);
    if (u > 0) {
        float &targetRef = dia ? u_ref_day[perfilActivo] : u_ref_night[perfilActivo];
        targetRef = (1.0f - BETA_UREF) * targetRef + BETA_UREF * u;
    }
}

// =========================
// BLE CALLBACKS
// =========================
#define SERVICE_UUID        "7D41B000-7A57-4E7A-A8C3-9E12C8F4A001"
#define CHAR_UUID_TEMP      "7D41B001-7A57-4E7A-A8C3-9E12C8F4A001"
#define CHAR_UUID_HUM       "7D41B002-7A57-4E7A-A8C3-9E12C8F4A001"
#define CHAR_UUID_LEVEL     "7D41B003-7A57-4E7A-A8C3-9E12C8F4A001"
#define CHAR_UUID_WIFI_OK   "0000AA04-0000-1000-8000-00805F9B34FB"
#define CHAR_UUID_TIME      "0000AA05-0000-1000-8000-00805F9B34FB"
#define CHAR_UUID_RIEGO     "7D41B006-7A57-4E7A-A8C3-9E12C8F4A001"
#define CHAR_UUID_LED       "0000AA10-0000-1000-8000-00805F9B34FB"

BLECharacteristic *pCharTemp, *pCharHum, *pCharLevel, *pCharWifi, *pCharTime, *pCharRiego, *pCharServiceChanged;
String lastReportedRiegoState = "";
uint32_t riegoStateVersion = 1;

void markRiegoStateDirty() {
    riegoStateVersion++;
    lastReportedRiegoState = "";
}

String buildRiegoStatePayload() {
    String activeMode = String(perfiles[perfilActivo].nombre);
    return "STATE," + String(riegoStateVersion) + "," + String(sistemaActivo ? "ON" : "OFF") + "," + activeMode + "," +
           String(perfiles[3].trDia) + "," +
           String(perfiles[3].tdDia) + "," +
           String(perfiles[3].trNoche) + "," +
           String(perfiles[3].tdNoche);
}

void notifyRiegoState(bool force = false) {
    if (!deviceConnected || pCharRiego == nullptr) return;
    String payload = buildRiegoStatePayload();
    if (force || payload != lastReportedRiegoState) {
        pCharRiego->setValue(payload.c_str());
        pCharRiego->notify();
        lastReportedRiegoState = payload;
        Serial.println("[RIEGO][STATE][NOTIFY] " + payload);
    }
}

void applyIrrigationSelection(int idx) {
    if (perfilActivo == idx && riegoIdx == idx) return;
    perfilActivo = idx;
    riegoIdx = idx;
    ultimoCambioBombaMs = millis();
    bombaEstado = false;
    digitalWrite(PIN_BOMBA, LOW);
    markRiegoStateDirty();
}

void setSystemActive(bool enabled) {
    if (enabled) {
        bootSafeMode = false;
    }
    if (sistemaActivo == enabled) return;
    sistemaActivo = enabled;
    if (sistemaActivo) {
        bombaEstado = true;
        ultimoCambioBombaMs = millis();
        digitalWrite(PIN_BOMBA, HIGH);
    } else {
        digitalWrite(PIN_BOMBA, LOW);
        bombaEstado = false;
    }
    markRiegoStateDirty();
}

class MyCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pS) override {
        deviceConnected = true;
        lastReportedRiegoState = "";
        Serial.println("[BLE] Cliente conectado");
        if (pCharServiceChanged != nullptr) {
            uint8_t range[4] = {0x01, 0x00, 0xFF, 0xFF};
            pCharServiceChanged->setValue(range, sizeof(range));
            pCharServiceChanged->indicate();
            Serial.println("[BLE] Service Changed indicado");
        }
        notifyRiegoState(true);
    }
    void onDisconnect(BLEServer* pS) override {
        deviceConnected = false;
        lastReportedRiegoState = "";
        Serial.println("[BLE] Cliente desconectado");
        pS->getAdvertising()->start();
    }
};

class TimeCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pC) override {
        std::string val = pC->getValue();
        if (val.length() >= 5) {
            int h, m;
            if (sscanf(val.c_str(), "%d:%d", &h, &m) == 2) {
                horaInt = h; minInt = m;
                lastMinuteMs = millis();
                horaSincronizada = true;
            }
        }
    }
};

class WifiCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pC) override {
        std::string val = pC->getValue();
        if (!val.empty()) {
            String msg = String(val.c_str());
            if (msg.startsWith("WIFI_OK:")) wifiNombreApp = msg.substring(8);
            else wifiNombreApp = msg; 
            lastActivityMs = millis();
        }
    }
};

class LedCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pC) override {
        std::string val = pC->getValue();
        int r, g, b;
        if (sscanf(val.c_str(), "%d,%d,%d", &r, &g, &b) == 3) {
            led.setPixelColor(0, led.Color(constrain(r,0,255), constrain(g,0,255), constrain(b,0,255))); led.show();
            ledOverride = true;
        }
    }
};

static void handleIrrigationCommand(const String &command) {
    lastActivityMs = millis();
    if (oledSleeping) {
        oled.setPowerSave(0);
        oledSleeping = false;
    }

    if (command == "SYNC") {
        notifyRiegoState(true);
        return;
    }

    if (command == "SYSTEM,ON") {
        setSystemActive(true);
        dispararPopupRemoto("ENCENDIDO", "");
        notifyRiegoState(true);
        return;
    }

    if (command == "SYSTEM,OFF") {
        setSystemActive(false);
        dispararPopupRemoto("APAGADO", "");
        notifyRiegoState(true);
        return;
    }

    if (!command.startsWith("SELECT,")) return;

    int firstComma = command.indexOf(',');
    int secondComma = command.indexOf(',', firstComma + 1);
    String mode = secondComma == -1
        ? command.substring(firstComma + 1)
        : command.substring(firstComma + 1, secondComma);

    if (mode == "RUCULA") {
        applyIrrigationSelection(0);
        dispararPopupRemoto("MODO RUCULA", "SELECCIONADO");
    } else if (mode == "LECHUGA") {
        applyIrrigationSelection(1);
        dispararPopupRemoto("MODO LECHUGA", "SELECCIONADO");
    } else if (mode == "PAPA") {
        applyIrrigationSelection(2);
        dispararPopupRemoto("MODO PAPA", "SELECCIONADO");
    } else if (mode == "MANUAL") {
        int trDia, tdDia, trNoche, tdNoche;
        if (sscanf(command.c_str(), "SELECT,MANUAL,%d,%d,%d,%d", &trDia, &tdDia, &trNoche, &tdNoche) == 4) {
            perfiles[3].trDia = max(1, trDia);
            perfiles[3].tdDia = max(1, tdDia);
            perfiles[3].trNoche = max(1, trNoche);
            perfiles[3].tdNoche = max(1, tdNoche);
            saveManualProfile();
            markRiegoStateDirty();
            applyIrrigationSelection(3);
            dispararPopupRemoto("MODO MANUAL", "CONFIGURADO");
        } else {
            return;
        }
    } else {
        return;
    }

    notifyRiegoState(true);
}

class IrrigationStateCallbacks: public BLECharacteristicCallbacks {
    void onRead(BLECharacteristic *pC) override {
        String payload = buildRiegoStatePayload();
        pC->setValue(payload.c_str());
        lastReportedRiegoState = payload;
        Serial.println("[RIEGO][STATE][READ] " + payload);
    }

    void onWrite(BLECharacteristic *pC) override {
        std::string val = pC->getValue();
        if (val.empty()) return;
        String command = String(val.c_str());
        command.trim();
        Serial.println("[RIEGO][CMD] " + command);
        handleIrrigationCommand(command);
    }
};

// =========================
// SOPORTE Y SENSORES
// =========================
void actualizarReloj() {
    if (!horaSincronizada) return;
    if (millis() - lastMinuteMs >= 60000) {
        lastMinuteMs = millis();
        minInt++;
        if (minInt >= 60) { minInt = 0; horaInt++; if (horaInt >= 24) horaInt = 0; }
    }
}

static inline uint8_t clamp255(uint32_t v) { return (v > 255u) ? 255u : (uint8_t)v; }

static inline bool getLogoPixel(uint16_t x, uint16_t y) {
    return (pgm_read_byte(&logo_bits[y * 16 + (x / 8)]) >> (7 - (x % 8))) & 0x01;
}

void prepareRandomRevealList() {
    onCount = 0; revealCursor = 0; logoMinX = 127; logoMaxX = 0;
    for (uint16_t i = 0; i < 8192; i++) {
        uint16_t x = i % 128;
        if (getLogoPixel(x, i / 128)) {
            onList[onCount++] = i;
            if (x < logoMinX) logoMinX = x;
            if (x > logoMaxX) logoMaxX = x;
        }
    }
    randomSeed(esp_random());
    for (int i = (int)onCount - 1; i > 0; i--) {
        int j = random(0, i + 1); uint16_t t = onList[i]; onList[i] = onList[j]; onList[j] = t;
    }
}

void restartOpeningSequence() {
    prepareRandomRevealList();
    revealCursor = 0;
    lastFrameMs = 0;
    appState = APP_OPENING;
}

void leerSensores() {
    sensors_event_t h, t;
    if (aht.getEvent(&h, &t)) { tempC = t.temperature - 11.5f; humPct = h.relative_humidity; }
    digitalWrite(TRIG, LOW); delayMicroseconds(2); 
    digitalWrite(TRIG, HIGH); delayMicroseconds(10); 
    digitalWrite(TRIG, LOW);
    long dur = pulseIn(ECHO, HIGH, 20000); 
    if (dur > 0) {
        float cm = (dur * 0.0343) / 2;
        int nuevoPct = constrain(map((int)cm, 35, 5, 0, 100), 0, 100); 
        aguaPct = (aguaPct * 0.6) + (nuevoPct * 0.4); 
        static uint32_t lastLevelTime = 0;
        if (millis() - lastLevelTime >= 60000) {
            float L_curr = (float)aguaPct;
            if (!hasPrevLevel) { L_prev = L_curr; hasPrevLevel = true; }
            float dotL_raw = (L_curr - L_prev) / 60.0f;
            dotL = ALPHA_DOTL * dotL + (1.0f - ALPHA_DOTL) * dotL_raw;
            L_prev = L_curr;
            lastLevelTime = millis();
        }
    }

    WaterAlarmState nextAlarmState = WATER_OK;
    if (aguaPct <= UMBRAL_VACIO) {
        nextAlarmState = WATER_EMPTY;
    } else if (aguaPct <= UMBRAL_BAJO) {
        nextAlarmState = WATER_LOW;
    }

    if (nextAlarmState != waterAlarmState) {
        bool clearingAlarm = (waterAlarmState != WATER_OK && nextAlarmState == WATER_OK);
        waterAlarmState = nextAlarmState;
        popupActivo = false;
        msUltimaAlarmaConfirmada = 0;
        if (clearingAlarm) {
            appState = APP_MENU_PRINCIPAL;
            subMenuIdx = 0;
            oled.clearBuffer();
            oled.sendBuffer();
            oled.setPowerSave(1);
            oledSleeping = true;
        }
    }

    if (waterAlarmState == WATER_EMPTY) {
        bloqueoPorVacio = true;
        if (sistemaActivo || bombaEstado) {
            setSystemActive(false);
            notifyRiegoState(true);
        }
        dispararPopup("TANQUE VACIO", String(aguaPct) + "%", true);
    } else if (waterAlarmState == WATER_LOW) {
        bloqueoPorVacio = false;
        dispararPopup("NIVEL AGUA BAJO", "MODO SUPERVIVENCIA ACTIVADO", false);
    } else {
        bloqueoPorVacio = false;
    }

    if (deviceConnected) {
        if (deviceConnected) {
    pCharTemp->setValue(String(tempC, 1).c_str());
    pCharTemp->notify();
    delay(10);

    pCharHum->setValue(String((int)humPct).c_str());
    pCharHum->notify();
    delay(10);

    pCharLevel->setValue(String(aguaPct).c_str());
    pCharLevel->notify();
    delay(10);
}
    }
}

void gestionarBomba() {
    if (!sistemaActivo || perfilActivo == -1) {
        digitalWrite(PIN_BOMBA, LOW);
        bombaEstado = false;
        return;
    }
    uint32_t now = millis();
    ejecutarAlgoritmoAquaBrain();
    uint32_t duracion = (bombaEstado ? (uint32_t)TR_calc : (uint32_t)TD_calc) * 1000;
    if (now - ultimoCambioBombaMs >= duracion) {
        bombaEstado = !bombaEstado;
        digitalWrite(PIN_BOMBA, bombaEstado ? HIGH : LOW);
        ultimoCambioBombaMs = now;
    }
}

// =========================
// RENDERIZADO OLED
// =========================
void drawPopupAlarma() {
    oled.clearBuffer();
    oled.drawFrame(0, 0, 128, 64);
    bool hasDetail = valorPopupDetalle.length() > 0;
    int msgY = hasDetail ? 24 : 34;
    int detailY = hasDetail ? 44 : 0;
    oled.setFont(u8g2_font_6x12_tf);
    int msgX = (128 - oled.getStrWidth(mensajePopup)) / 2;
    oled.drawStr(msgX < 6 ? 6 : msgX, msgY, mensajePopup);
    if (hasDetail) {
        oled.setFont(u8g2_font_7x14B_tf);
        int detailX = (128 - oled.getStrWidth(valorPopupDetalle.c_str())) / 2;
        oled.drawStr(detailX < 6 ? 6 : detailX, detailY, valorPopupDetalle.c_str());
    }
    if (strlen(popupFooter) > 0) {
        oled.setFont(u8g2_font_4x6_tf);
        int footerX = (128 - oled.getStrWidth(popupFooter)) / 2;
        oled.drawStr(footerX < 6 ? 6 : footerX, 58, popupFooter);
    }
    oled.sendBuffer();
}

void drawMenuOption(const char* text, bool highlighted = false) {
    oled.clearBuffer();
    int bx = 6, by = 21, bw = 116, bh = 24;
    if (highlighted || visualFeedback) {
        oled.drawBox(bx, by, bw, bh);
        oled.setDrawColor(0);
    }
    oled.setFont(u8g2_font_7x14_tf);
    String opt = "< ";
    opt += text;
    opt += " >";
    oled.drawStr((128 - oled.getStrWidth(opt.c_str())) / 2, by + 16, opt.c_str());
    oled.setDrawColor(1);
    oled.sendBuffer();
}

void drawPantallaConexion() {
    oled.clearBuffer();
    oled.drawLine(15, 10, 15, 26); oled.drawLine(15, 10, 21, 14);
    oled.drawLine(21, 14, 11, 22); oled.drawLine(11, 14, 21, 22); oled.drawLine(21, 22, 15, 26);
    oled.setFont(u8g2_font_6x12_tf);
    oled.drawStr(32, 16, "BLE");
    oled.setFont(u8g2_font_7x14_tf);
    oled.drawStr(32, 34, deviceConnected ? "CONECTADO" : "DESCONECTADO");
    oled.sendBuffer();
}

void drawFinalLogo() {
    oled.clearBuffer();
    for (uint16_t k = 0; k < onCount; k++) {
        uint16_t idx = onList[k]; oled.drawPixel((idx % 128) - 4, idx / 128);
    }
    oled.setFont(u8g2_font_9x15B_tf);
    oled.drawStr(logoMinX - 4 - 2 - oled.getStrWidth("AQUA"), 40, "AQUA");
    oled.drawStr(logoMaxX - 4 + 3, 40, "BRAIN");
    oled.sendBuffer();
}

void drawPantallaRiego() {
    oled.clearBuffer();
    oled.setFont(u8g2_font_7x14_tf);
    const char* nombre = riegoOptions[riegoIdx];
    int tw = oled.getStrWidth(nombre);
    int xPos = (128 - tw) / 2;
    if (riegoIdx < 4 && perfilActivo == riegoIdx) {
        oled.drawBox(xPos - 6, 23, tw + 12, 20);
        oled.setDrawColor(0);
    } else if (visualFeedback) {
        oled.drawBox(xPos - 6, 23, tw + 12, 20);
        oled.setDrawColor(0);
    }
    oled.drawStr(xPos, 37, nombre);
    oled.setDrawColor(1);
    oled.sendBuffer();
}

void drawRiegoDetalle() {
    oled.clearBuffer();
    bool esManual = (riegoIdx == 3);
    oled.setFont(u8g2_font_6x12_tf); oled.drawStr(0, 10, perfiles[riegoIdx].nombre); oled.drawLine(0, 12, 128, 12);
    ejecutarAlgoritmoAquaBrain();
    oled.setFont(u8g2_font_5x8_tf);

    auto drawValueField = [&](int x, int y, int w, int h, int focus, int value) {
        bool isFocused = esManual && campoFoco == focus;
        if (isFocused) {
            if (editandoParametro) oled.drawBox(x, y, w, h);
            else oled.drawFrame(x, y, w, h);
        }
        oled.setDrawColor(isFocused && editandoParametro ? 0 : 1);
        oled.setCursor(x + 2, y + 8);
        oled.print(value);
        oled.print("s");
        oled.setDrawColor(1);
    };

    oled.drawStr(0, 25, "DIA:");
    drawValueField(28, 17, 32, 11, 0, perfiles[3].trDia);
    drawValueField(28, 29, 32, 11, 1, perfiles[3].tdDia);
    oled.drawStr(65, 25, "NOCHE:");
    drawValueField(93, 17, 34, 11, 2, perfiles[3].trNoche);
    drawValueField(93, 29, 34, 11, 3, perfiles[3].tdNoche);

    if (!esManual) {
        oled.setCursor(30, 25); oled.print(sistemaActivo ? TR_calc : perfiles[riegoIdx].trDia); oled.print("s");
        oled.setCursor(30, 37); oled.print(sistemaActivo ? TD_calc : perfiles[riegoIdx].tdDia); oled.print("s");
        oled.setCursor(95, 25); oled.print(perfiles[riegoIdx].trNoche); oled.print("s");
        oled.setCursor(95, 37); oled.print(perfiles[riegoIdx].tdNoche); oled.print("s");
    }

    if(campoFoco == 4) oled.drawBox(10, 48, 48, 14);
    oled.setDrawColor(campoFoco == 4 ? 0 : 1);
    oled.drawFrame(10, 48, 48, 14); oled.drawStr(20, 58, visualFeedback ? "OK!" : "SELECT");
    oled.setDrawColor(1);
    if(campoFoco == 5) oled.drawBox(70, 48, 48, 14);
    oled.setDrawColor(campoFoco == 5 ? 0 : 1);
    oled.drawFrame(70, 48, 48, 14); oled.drawStr(83, 58, "VOLVER");
    oled.setDrawColor(1); oled.sendBuffer();
}

void drawPantallaEstado() {
    oled.clearBuffer(); oled.setFont(u8g2_font_6x12_tf);
    String esp = "P: "; esp += perfiles[perfilActivo].nombre;
    oled.drawStr(0, 10, esp.c_str()); oled.drawLine(0, 12, 128, 12);
    char buffer[10]; if (horaSincronizada) sprintf(buffer, "%02d:%02d", horaInt, minInt); else strcpy(buffer, "--:--");
    oled.drawStr(95, 10, buffer); 
    oled.setFont(u8g2_font_5x8_tf);
    oled.setCursor(0, 25); oled.print("TEMP: "); oled.print(tempC, 1); oled.print(" C");
    oled.setCursor(0, 36); oled.print("HUM:  "); oled.print((int)humPct); oled.print(" %");
    oled.setCursor(0, 47); oled.print("NIVEL:"); oled.print(aguaPct); oled.print(" %");
    oled.setCursor(75, 25); oled.print("BOMBA:"); oled.setCursor(75, 36); 
    oled.print((sistemaActivo && bombaEstado) ? "[ ON ]" : "[ OFF ]");
    oled.drawFrame(75, 42, 50, 6); int f = map(aguaPct, 0, 100, 0, 46); if(f > 0) oled.drawBox(77, 44, f, 2);
    oled.setFont(u8g2_font_4x6_tf); 
    oled.drawStr(0, 62, sistemaActivo ? "SISTEMA ACTIVO" : "SISTEMA STANDBY");
    oled.sendBuffer();
}

void updateLedFX() {
    if (waterAlarmState != WATER_OK) {
        if ((millis() / 200) % 2 == 0) {
            led.setPixelColor(0, waterAlarmState == WATER_EMPTY ? led.Color(255,0,0) : led.Color(255,180,0));
        } else {
            led.setPixelColor(0, led.Color(0,0,0));
        }
        led.show();
        return;
    }
    if (ledOverride || millis() - lastLedMs < 80) return;
    lastLedMs = millis();
    static uint16_t hue = 0; static float ph = 0.0f;
    hue += 100; ph += 0.01f;
    float w = (sinf(ph) + 1.0f) * 0.5f;
    uint32_t c1 = led.ColorHSV(hue, 255, 200);
    uint32_t c2 = led.ColorHSV(hue + 32768, 255, 200);
    led.setPixelColor(0, led.gamma32(led.Color(
        clamp255(((c1 >> 16) & 0xFF) * w + ((c2 >> 16) & 0xFF) * (1.0f - w)),
        clamp255(((c1 >> 8) & 0xFF) * w + ((c2 >> 8) & 0xFF) * (1.0f - w)),
        clamp255((c1 & 0xFF) * w + (c2 & 0xFF) * (1.0f - w))
    )));
    led.show();
}

// =========================
// MANEJADORES DE ENTRADA
// =========================
void manejadorNavegacion(int jX, bool sw, uint32_t now) {
    if (now - lastDebounceMs > 250) {
        if (jX > 3200) { subMenuIdx = (subMenuIdx + 1) % 3; lastDebounceMs = now; }
        else if (jX < 800) { subMenuIdx = (subMenuIdx - 1 + 3) % 3; lastDebounceMs = now; }
    }
    if (sw && (now - lastDebounceMs > 600)) {
        lastDebounceMs = now;
        visualFeedback = true; delay(150); visualFeedback = false;
        if (subMenuIdx == 0) {
            setSystemActive(!sistemaActivo);
            notifyRiegoState(true);
        }
        else if (subMenuIdx == 1) { appState = APP_PANTALLA_ESTADO; leerSensores(); }
        else if (subMenuIdx == 2) { appState = APP_PANTALLA_RIEGO; riegoIdx = perfilActivo; }
    }
}

void manejadorSubMenu(int jX, bool sw, uint32_t now) {
    manejadorNavegacion(jX, sw, now);
}

void manejadorRiego(int jX, bool sw, uint32_t now) {
    if (now - lastDebounceMs > 250) {
        if (jX > 3200) { riegoIdx = (riegoIdx + 1) % 5; lastDebounceMs = now; }
        else if (jX < 800) { riegoIdx = (riegoIdx - 1 + 5) % 5; lastDebounceMs = now; }
    }
    if (sw && (now - lastDebounceMs > 600)) {
        lastDebounceMs = now;
        if (riegoIdx == 4) {
            appState = APP_SUBMENU;
        } else if (riegoIdx == 3) {
            appState = APP_RIEGO_DETALLE;
            campoFoco = 4;
            editandoParametro = false;
        } else {
            visualFeedback = true; delay(200); visualFeedback = false;
            applyIrrigationSelection(riegoIdx);
            notifyRiegoState(true);
        }
    }
}

void manejadorRiegoDetalle(int jX, bool sw, uint32_t now) {
    if (!editandoParametro) {
        if (now - lastDebounceMs > 250) {
            if (jX > 3200) { campoFoco = (campoFoco + 1) % 6; lastDebounceMs = now; }
            else if (jX < 800) { campoFoco = (campoFoco - 1 + 6) % 6; lastDebounceMs = now; }
        }
        if (sw && (now - lastDebounceMs > 600)) {
            lastDebounceMs = now;
            if (campoFoco == 4) {
                visualFeedback = true; delay(300); visualFeedback = false;
                applyIrrigationSelection(riegoIdx);
                notifyRiegoState(true);
                appState = APP_PANTALLA_RIEGO;
            } else if (campoFoco == 5) {
                appState = APP_PANTALLA_RIEGO;
            } else {
                editandoParametro = true;
            }
        }
    } else {
        if (now - lastDebounceMs > 150) {
            int delta = (jX > 3200) ? 5 : (jX < 800 ? -5 : 0);
            if (delta != 0) {
                lastDebounceMs = now;
                if (campoFoco == 0) perfiles[3].trDia = max(0, perfiles[3].trDia + delta);
                if (campoFoco == 1) perfiles[3].tdDia = max(0, perfiles[3].tdDia + delta);
                if (campoFoco == 2) perfiles[3].trNoche = max(0, perfiles[3].trNoche + delta);
                if (campoFoco == 3) perfiles[3].tdNoche = max(0, perfiles[3].tdNoche + delta);
                saveManualProfile();
                markRiegoStateDirty();
                notifyRiegoState(true);
            }
        }
        if (sw && (now - lastDebounceMs > 600)) { editandoParametro = false; lastDebounceMs = now; }
    }
}

// =========================
// SETUP Y LOOP
// =========================
void setup() {
    Serial.begin(115200);
    preferences.begin("aquabrain", false);
    loadManualProfile();
    bootSafeMode = true;
    sistemaActivo = false;
    bombaEstado = false;
    horaSincronizada = false;
    horaInt = 0;
    minInt = 0;
    ultimoCambioBombaMs = millis();
    lastMinuteMs = millis();
    pinMode(PIN_BOMBA, OUTPUT); digitalWrite(PIN_BOMBA, LOW);
    pinMode(PIN_RST, OUTPUT); digitalWrite(PIN_RST, LOW); delay(20);
    SPI.begin(PIN_SCK, -1, PIN_SDA, PIN_CS); Wire.begin(2, 3);
    delay(600); digitalWrite(PIN_RST, HIGH);
    oled.begin(); oled.setContrast(255); led.begin(); led.setBrightness(150); led.show();
    aht.begin(); pinMode(PIN_SW, INPUT_PULLUP); pinMode(TRIG, OUTPUT); pinMode(ECHO, INPUT);

    BLEDevice::init("AquaBrain-S3");
    BLEServer *pS = BLEDevice::createServer(); pS->setCallbacks(new MyCallbacks());
    BLEService *pGatt = pS->createService(BLEUUID((uint16_t)0x1801));
    pCharServiceChanged = pGatt->createCharacteristic(
        BLEUUID((uint16_t)0x2A05),
        BLECharacteristic::PROPERTY_INDICATE
    );
    pCharServiceChanged->addDescriptor(new BLE2902());
    uint8_t initialRange[4] = {0x01, 0x00, 0xFF, 0xFF};
    pCharServiceChanged->setValue(initialRange, sizeof(initialRange));
    pGatt->start();
    BLEService *pServ = pS->createService(BLEUUID(SERVICE_UUID), 40);
    pCharTemp = pServ->createCharacteristic(CHAR_UUID_TEMP, BLECharacteristic::PROPERTY_NOTIFY);
    pCharTemp->addDescriptor(new BLE2902());
    pCharHum = pServ->createCharacteristic(CHAR_UUID_HUM, BLECharacteristic::PROPERTY_NOTIFY);
    pCharHum->addDescriptor(new BLE2902());
    pCharLevel = pServ->createCharacteristic(CHAR_UUID_LEVEL, BLECharacteristic::PROPERTY_NOTIFY);
    pCharLevel->addDescriptor(new BLE2902());
    pCharWifi = pServ->createCharacteristic(CHAR_UUID_WIFI_OK, BLECharacteristic::PROPERTY_WRITE);
    pCharWifi->setCallbacks(new WifiCallbacks());
    pCharTime = pServ->createCharacteristic(CHAR_UUID_TIME, BLECharacteristic::PROPERTY_WRITE);
    pCharTime->setCallbacks(new TimeCallbacks());
    pCharRiego = pServ->createCharacteristic(
        CHAR_UUID_RIEGO,
        BLECharacteristic::PROPERTY_NOTIFY |
        BLECharacteristic::PROPERTY_READ |
        BLECharacteristic::PROPERTY_WRITE |
        BLECharacteristic::PROPERTY_WRITE_NR
    );
    pCharRiego->addDescriptor(new BLE2902());
    pCharRiego->setCallbacks(new IrrigationStateCallbacks());
    BLECharacteristic *pCharLed = pServ->createCharacteristic(CHAR_UUID_LED, BLECharacteristic::PROPERTY_WRITE);
    pCharLed->setCallbacks(new LedCallbacks());
    pServ->start(); pS->getAdvertising()->start();
    prepareRandomRevealList();
    lastActivityMs = millis();
    notifyRiegoState(true);
}

void loop() {
    uint32_t now = millis();
    int jX = analogRead(PIN_AD2);
    bool sw = (digitalRead(PIN_SW) == LOW);

    if (bootSafeMode) {
        sistemaActivo = false;
        bombaEstado = false;
        digitalWrite(PIN_BOMBA, LOW);
    }

    actualizarReloj();
    gestionarBomba();
    notifyRiegoState();
    updateLedFX(); 

    if (sw || jX > 3200 || jX < 800) {
        lastActivityMs = now;
        if (oledSleeping) {
            oled.setPowerSave(0);
            oledSleeping = false;
            appState = APP_MENU_PRINCIPAL;
            subMenuIdx = 0;
            oled.clearBuffer();
            oled.sendBuffer();
            delay(200);
        }
        if (appState == APP_LOGO_FIJO) { appState = APP_MENU_PRINCIPAL; subMenuIdx = 0; delay(250); }
    }

    // STANDBY ACTIVO 24/7
    static uint32_t lastSensMs = 0;
    if (now - lastSensMs > 3000) { leerSensores(); lastSensMs = now; }

    // PRIORIDAD: RENDERIZAR SI HAY POPUP O SI NO HAY STANDBY
    static uint32_t lastRenderMs = 0;
    if ((popupActivo || !oledSleeping) && (now - lastRenderMs >= 33)) {
        lastRenderMs = now;
        
        if (popupActivo) {
            // DESPERTAR FÍSICO SI HAY POPUP
            if (oledSleeping) { oled.setPowerSave(0); oledSleeping = false; }
            drawPopupAlarma();
            
            // CERRAR POPUP CON SWITCH (INTERACTIVO)
            if (sw && (now - lastDebounceMs > 600)) {
                lastDebounceMs = now;
                popupActivo = false;
                msUltimaAlarmaConfirmada = now; // Inicia lapsus de 5 segundos
                if (popupEsRemoto) {
                    oled.setPowerSave(1);
                    oledSleeping = true;
                } else {
                    appState = APP_PANTALLA_ESTADO;
                }
            }
            // Auto-cierre por tiempo si no es crítico (3 segundos)
            if (!bloqueoPorVacio && (now - msInicioPopup > 3000)) {
                popupActivo = false;
                msUltimaAlarmaConfirmada = now;
                if (popupEsRemoto) {
                    oled.setPowerSave(1);
                    oledSleeping = true;
                }
            }
        } 
        else {
            // RENDERIZADO NORMAL
            switch (appState) {
                case APP_OPENING:
                    if (now - lastFrameMs >= 65) {
                        lastFrameMs = now; uint16_t b = 10; while (b-- && revealCursor < onCount) revealCursor++;
                        oled.clearBuffer();
                        for (uint16_t k = 0; k < revealCursor; k++) { uint16_t idx = onList[k]; oled.drawPixel((idx % 128) - 4, idx / 128); }
                        float p = (float)revealCursor / onCount; oled.setFont(u8g2_font_9x15B_tf);
                        char lb[8]={0}, rb[8]={0}; strncpy(lb, "AQUA", (int)(p*4)); strncpy(rb, "BRAIN", (int)(p*5));
                        oled.drawStr(logoMinX-4-2-oled.getStrWidth(lb), 40, lb); oled.drawStr(logoMaxX-4+3, 40, rb);
                        oled.sendBuffer(); if (revealCursor >= onCount) appState = APP_LOGO_FIJO;
                    }
                    break;
                case APP_MENU_PRINCIPAL: {
                    manejadorNavegacion(jX, sw, now);
                    String subLabel = (subMenuIdx == 0) ? (sistemaActivo ? "APAGAR" : "ENCENDER") : subMenuOptions[subMenuIdx];
                    drawMenuOption(subLabel.c_str(), subMenuIdx == 0 && sistemaActivo);
                    break;
                }
                case APP_SUBMENU: {
                    manejadorSubMenu(jX, sw, now);
                    String subLabel = (subMenuIdx == 0) ? (sistemaActivo ? "APAGAR" : "ENCENDER") : subMenuOptions[subMenuIdx];
                    drawMenuOption(subLabel.c_str(), subMenuIdx == 0 && sistemaActivo);
                    break;
                }
                case APP_PANTALLA_RIEGO: manejadorRiego(jX, sw, now); drawPantallaRiego(); break;
                case APP_RIEGO_DETALLE: manejadorRiegoDetalle(jX, sw, now); drawRiegoDetalle(); break;
                case APP_PANTALLA_ESTADO: if (sw && (now-lastDebounceMs>600)) {lastDebounceMs=now; appState=APP_MENU_PRINCIPAL;} drawPantallaEstado(); break;
                case APP_PANTALLA_CONEXION: if (sw && (now-lastDebounceMs>600)) {lastDebounceMs=now; appState=APP_MENU_PRINCIPAL;} drawPantallaConexion(); break;
                case APP_LOGO_FIJO: drawFinalLogo(); break;
            }
        }
    }
    if (now - lastActivityMs >= TIMEOUT_STANDBY && !oledSleeping) { oled.setPowerSave(1); oledSleeping = true; ledOverride = false; }
}
