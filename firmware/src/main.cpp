#include <Arduino.h>
#include <StateMachine.h>
#include <Ticker.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <ADS1X15.h>

// port definitions
#define ANALOG_PIN 34
#define ADC_RDY_PIN 23
#define AD8232_LOM 4
#define AD8232_LOP 0
#define AD8232_SDN 2
#define LED_PIN 5
#define BUTTON_PIN 18

// CONSTANTS definitions
const uint16_t SAMPLE_RATE = 30;
const uint16_t EXAM_END_FLAG = 0xFFFF;

//// BLE definitions
#define BLE_SERVER_NAME "OKDevice"
#define SERVICE_UUID "5e6c5158-05d8-463b-b21d-eed2204c2002"
#define OK_DATA_UUID "cba1d466-344c-4be3-ab3f-189f80dd7518"
#define OK_CTRL_UUID "55498abf-77df-4dc4-89b2-107dab085034"
BLECharacteristic OKDataCharacteristic(OK_DATA_UUID, BLECharacteristic::PROPERTY_NOTIFY);
BLECharacteristic OKCtrlCharacteristic(OK_CTRL_UUID, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE);

// union definition
union Sample{
  volatile uint16_t raw;
  volatile uint8_t bytes[2];
} ekg_sample;

// varaible declarations
uint8_t sampleBuffer[12] = {0};
int byte_count = 0;
int sample_count = 0;
int sample_limit = 0;
int samples_per_frame = 6;
float f = 0;

// ISR flags
volatile bool adc_ready = false;
volatile bool request = false;
volatile long tic, toc = 0L;

// timer initialization and function definitions
hw_timer_t *timer = NULL;
void IRAM_ATTR onTimer(){
    request = true;
    tic = micros();
}
void timer_setup(void){
  timer = timerBegin(0, 80, true);
  timerAttachInterrupt(timer, &onTimer, true);
  timerAlarmWrite(timer, (uint64_t)1000000/SAMPLE_RATE, true);
}

// ADC initialization and functions definitions
ADS1115 ADS(0x48);
void adc_setup(void){
  Serial.println(ADS.begin());
  ADS.setWireClock(400000U);
  ADS.setGain(1);     // 4.096 volt max range
  ADS.setDataRate(6); // 2.25 ms per conversion
  f = ADS.toVoltage(); // voltage factor
  
  // set the thresholds to Trigger RDY pin
  ADS.setComparatorThresholdLow(0x0000);
  ADS.setComparatorThresholdHigh(0x0200);
  ADS.setComparatorQueConvert(0);             // enable RDY pin !!
  ADS.setComparatorLatch(0);
}
void IRAM_ATTR onAdcRdy() {
    adc_ready = true;
}

// Ticker definition
Ticker blinker;
void blink(int pattern) {
  static int counter = 0;
  digitalWrite(LED_PIN, (pattern>>counter++)&0x01);
  if(counter>15) counter = 0;
}

uint16_t okFilter(uint16_t sample){
  #ifdef FILTER
    static uint16_t output = 0;
    static uint32_t accumulator = 0;
    accumulator = accumulator + sample - output;
    output = accumulator >> 4; // where N = 1, 2, 3, 4, etc.
    return output;
  #else
    return sample;
  #endif
}
// FSM definition
StateMachine machine = StateMachine();
bool dev_connected = false;
bool exam_running = false;

void state_idle_cb(){
  if(machine.executeOnce){
    digitalWrite(LED_PIN, LOW);
    timerAlarmDisable(timer);
    detachInterrupt(ADC_RDY_PIN);
    OKCtrlCharacteristic.setValue((uint8_t*)&SAMPLE_RATE,2);
    Serial.println("State -> IDLE");
  }
}

void state_conn_cb(){
  if(machine.executeOnce){
    blinker.attach_ms(100, blink, 0x5555); // 1 pulses every 200 ms
    timerAlarmDisable(timer);
    detachInterrupt(ADC_RDY_PIN);
    Serial.println("State -> CONN");
  }
}

void state_wait_cb(){
  if(machine.executeOnce){
    sample_count = 0;
    blinker.attach_ms(125, blink, 0x000A);  // 2 pulses every 2 segundos
    timerAlarmEnable(timer);
    attachInterrupt(ADC_RDY_PIN, onAdcRdy, RISING);
    Serial.println("State -> WAIT");
  }
}

void state_send_cb(){
  uint16_t newSample = 0;
  if(machine.executeOnce){
    digitalWrite(LED_PIN, HIGH);
    Serial.println("State -> SEND");
  }
  if(request){
    ADS.requestADC(0);
    request = false;
  }
  if(adc_ready){
    newSample = ADS.getValue();
    ekg_sample.raw = okFilter(newSample);
    sampleBuffer[byte_count++] = ekg_sample.bytes[0];
    sampleBuffer[byte_count++] = ekg_sample.bytes[1];
    sample_count++;
    toc = micros();
    if(byte_count >= samples_per_frame*2){
      OKDataCharacteristic.setValue(sampleBuffer,byte_count);
      OKDataCharacteristic.notify();
      byte_count = 0;
      Serial.println(toc - tic);
      for(int i = 0; i < samples_per_frame; i++){
        Serial.print((uint16_t)sampleBuffer[2*i] | (uint16_t)sampleBuffer[2*i + 1]<<8, HEX);
        Serial.print(" ");
      }
      Serial.println();
    }
    if(sample_count >= sample_limit){

      OKDataCharacteristic.setValue((uint8_t*)&EXAM_END_FLAG,2);
      OKDataCharacteristic.notify();
      exam_running = false;
    }
    adc_ready = false;
  }    
}

State* IDLE = machine.addState(&state_idle_cb);
State* CONN = machine.addState(&state_conn_cb);
State* WAIT = machine.addState(&state_wait_cb);
State* SEND = machine.addState(&state_send_cb);

bool idle_to_conn(){
  return dev_connected;
}

bool conn_to_idle(){
  if(!dev_connected){
    blinker.detach();
    return true;
  }
  return false;
}
bool conn_to_wait(){
  if((bool)(digitalRead(AD8232_LOM) && digitalRead(AD8232_LOP))){
    blinker.detach();
    return true;
  }
  return false;
}

bool wait_to_idle(){
  if(!dev_connected){
    blinker.detach();
    return true;
  }
  return false;
}
bool wait_to_conn(){
  if(!(bool)(digitalRead(AD8232_LOM) && digitalRead(AD8232_LOP))){
    blinker.detach();
    return true;
  }
  return false;
}
bool wait_to_send(){
  if(exam_running){
    blinker.detach();
    return true;
  }
  return false;
}

bool send_to_idle(){
  if(!dev_connected){
    return true;
  }
  return false;
}
bool send_to_conn(){
  if(!(bool)(digitalRead(AD8232_LOM) && digitalRead(AD8232_LOP))){
    return true;
  }
  return false;
}
bool send_to_wait(){
  return !exam_running;
}


void sm_setup(void){
  IDLE->addTransition(&idle_to_conn,CONN);
  CONN->addTransition(&conn_to_idle,IDLE);
  CONN->addTransition(&conn_to_wait,WAIT);
  WAIT->addTransition(&wait_to_idle,IDLE);
  WAIT->addTransition(&wait_to_conn,CONN);
  WAIT->addTransition(&wait_to_send,SEND);
  SEND->addTransition(&send_to_idle,IDLE);
  SEND->addTransition(&send_to_conn,CONN);
  SEND->addTransition(&send_to_wait,WAIT);
}

// BLE Callbacks
class OKServerCallbacks: public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) {
    dev_connected = true;
  }
  void onDisconnect(BLEServer* pServer) {
    dev_connected = false;
    exam_running = false;
    pServer->getAdvertising()->start();
    Serial.println("Waiting a client connection to notify...");
  }
};

class OKCtrlCallbacks: public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *pCharacteristic) {
    uint8_t* pData = pCharacteristic->getData();
    uint16_t duration = *(uint16_t*)pData;
    Serial.println(duration, HEX);
    if(duration > 20) duration = 20;
    sample_limit = duration*SAMPLE_RATE;
    samples_per_frame = 6;
    exam_running = true;
  }
};

void ble_setup(void){
    // Create the BLE Device
  BLEDevice::init(BLE_SERVER_NAME);
  // Create the BLE Server
  BLEServer *pServer = BLEDevice::createServer();
  pServer->setCallbacks(new OKServerCallbacks());
  // Create the BLE Service
  BLEService *pService = pServer->createService(SERVICE_UUID);
  // Create and add Descriptors
  BLEDescriptor *pOKDataDescriptor = new BLE2902();
  OKDataCharacteristic.addDescriptor(pOKDataDescriptor);
  BLEDescriptor *pOKCtrlDescriptor = new BLE2902();
  OKCtrlCharacteristic.addDescriptor(pOKCtrlDescriptor);
  // Add Characteristics
  pService->addCharacteristic(&OKDataCharacteristic);
  pService->addCharacteristic(&OKCtrlCharacteristic);
  // Set Callbacks for characteristics
  OKCtrlCharacteristic.setCallbacks(new OKCtrlCallbacks());
  // Start advertising
  pService->start();
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pServer->getAdvertising()->start();
  OKCtrlCharacteristic.setValue((uint8_t*)&SAMPLE_RATE,2);
  Serial.println("Waiting a client connection to notify...");
}

void setup() {
  Serial.begin(115200);
  pinMode(ADC_RDY_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  pinMode(AD8232_LOM, INPUT_PULLUP);
  pinMode(AD8232_LOP, INPUT_PULLUP);
  timer_setup();
  adc_setup();
  sm_setup();
  ble_setup();
}

void loop() {
  machine.run();
}