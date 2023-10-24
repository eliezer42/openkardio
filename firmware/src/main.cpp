#include <Arduino.h>
#include <StateMachine.h>
#include <Ticker.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <ADS1X15.h>
#include "OKConfig.h"
#include "lpfilter.h"

BLECharacteristic OKDataCharacteristic(OK_DATA_UUID, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
BLECharacteristic OKCtrlCharacteristic(OK_CTRL_UUID, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE);
uint8_t error_code = 0x00;
void send_flag(uint8_t flag){
  uint8_t temp[1];
  temp[0] = flag;
  OKDataCharacteristic.setValue(temp,1);
  OKDataCharacteristic.notify();
}
//// Variables declaration
// Timer reference variable
hw_timer_t *sampling_clock = NULL;
// ISR variables
volatile bool request = false;
volatile long tic, toc = 0L;
volatile long prebuffer_counter = 0;
long sample_times[5000] = {0};
long max_time = 0;
long min_time = 0x7FFFFFFF;
int frame_counter = 0;

// Filter reference
lpfilterType *pFilter = lpfilter_create();
bool bFilterActive = false;
int16_t filter(int16_t sample){
  if(bFilterActive){
    float input = float(sample);
    lpfilter_writeInput(pFilter, input);
    float output = lpfilter_readOutput(pFilter);
    return int16_t(output);
  }
  return sample;
}
// Ekg processing variables
int byte_count = 0;
sample ekg_sample;
uint8_t sample_buffer[BUFFER_LENGTH];
int16_t signal_offset = 0;
int16_t raw_sample = 0;

// Device info
info device_info = {
  100,
  SAMPLES_PER_FRAME,
  EKG_SAMPLE_RATE,
  FRONTEND_LEADS,
  ADC_RESOLUTION,
  FIRMWARE_MAJOR_VERSION,
  FIRMWARE_MINOR_VERSION,
  FRONTEND_GAIN*ADC_GAIN,
};
bool dev_connected = false;
bool exam_running = false;
bool adc_connected = false;

//ADS declaration and setup definition
ADS1115 ADS(0x48);
void adc_setup(void){
  adc_connected = ADS.begin();
  ADS.setWireClock(400000U);
  ADS.setGain(1);     // 4.096 volt max range
  ADS.setDataRate(7); // 1.16 ms per conversion
}

// Ticker declarations
Ticker led_blinker;
Ticker batt_monitor;

void blink(int pattern) {
  static int counter = 0;
  digitalWrite(STAT_LED_PIN, (pattern>>counter++)&0x01);
  if(counter>15) counter = 0;
}

// FSM definitions and flags
StateMachine machine = StateMachine();
void state_idle_cb(void){
  if(machine.executeOnce){
    digitalWrite(STAT_LED_PIN, LOW);
    Serial.println("State: IDLE");
  }
}
void state_conn_cb(void){
  if(machine.executeOnce){
    led_blinker.attach_ms(125, blink, 0x000A);  // 2 pulses every 2 segundos
    OKCtrlCharacteristic.setValue((uint8_t*)&device_info,sizeof(info));
    Serial.println("State: CONN");
  }
}
void on_conn_exit(void){
  led_blinker.detach();
  digitalWrite(STAT_LED_PIN, LOW);
}
void state_send_cb(){
  int16_t newSample = 0;
  if(machine.executeOnce){
    byte_count = 0;
    prebuffer_counter = 0;
    memset(sample_times,0,sizeof(sample_times));
    frame_counter = 0;
    max_time = 0;
    min_time = 0x7FFFFFFF;
    signal_offset = ADS.readADC(0)>>1;
    timerAlarmEnable(sampling_clock);
    digitalWrite(STAT_LED_PIN, HIGH);
    if(!adc_connected){
      error_code = NO_ADC;
      OKDataCharacteristic.setValue(&error_code,1);
      OKDataCharacteristic.notify();
    }
    Serial.println("State: SEND");
  }
  if(request){
    
    raw_sample = ADS.readADC(1);
    newSample = raw_sample-signal_offset;
    
    ekg_sample.raw = filter(newSample);

    sample_buffer[byte_count++] = ekg_sample.bytes[0];
    sample_buffer[byte_count++] = ekg_sample.bytes[1];
    request = false;

    if(byte_count/2 == SAMPLES_PER_FRAME){
      if (prebuffer_counter > lpfilter_length){
        tic = micros();
        OKDataCharacteristic.setValue(sample_buffer,byte_count);
        OKDataCharacteristic.notify();
        toc = micros();

        frame_counter++;

        sample_times[frame_counter-1] = toc - tic;
        max_time = max(max_time, sample_times[frame_counter-1]);
        min_time = min(min_time, sample_times[frame_counter-1]);
      }
      // for(int i = 0; i < byte_count; i++){
      //   Serial.print(((uint16_t)sample_buffer[i] | (uint16_t)sample_buffer[++i]<<8)/ADC_STEPS_PER_V);
      //   Serial.print("-");
      // }
      // Serial.println();
      byte_count = 0;
    }
  }   
}

void on_send_exit(void){
  long sum = 0;
  double average = 0;

  timerAlarmDisable(sampling_clock);
  digitalWrite(STAT_LED_PIN, LOW);
  
  if (frame_counter <= 5000 && frame_counter > 0){
    for (int i = 0; i < frame_counter; i++) {
        sum += sample_times[i];
    }
    average = (double)sum / frame_counter;
    double squaredDifferencesSum = 0.0;

    for (int i = 0; i < frame_counter; i++) {
        double difference = sample_times[i] - average;
        squaredDifferencesSum += difference * difference;
    }

    double variance = squaredDifferencesSum / (frame_counter);
    double sampleStdDeviation = sqrt(variance);

    Serial.println("-----");
    Serial.print("AVG: ");
    Serial.println(average);
    Serial.print("MAX: ");
    Serial.println(max_time);
    Serial.print("MIN: ");
    Serial.println(min_time);
    Serial.print("STD: ");
    Serial.println(sampleStdDeviation);
  }
  else {
    Serial.println("There was a problem.");
  }
  Serial.println("-----");
}

State* IDLE = machine.addState(&state_idle_cb);
State* CONN = machine.addState(&state_conn_cb);
State* SEND = machine.addState(&state_send_cb);

void IRAM_ATTR onSamplingClock(){
    prebuffer_counter++;
    request = true;
}

void timer_setup(void){
  sampling_clock = timerBegin(0, 8, true);
  timerAttachInterrupt(sampling_clock, &onSamplingClock, true);
  timerAlarmWrite(sampling_clock, (uint64_t)10000000/EKG_SAMPLE_RATE, true);
}

void measure_batt(void){
  float voltage_level;
  voltage_level = analogReadMilliVolts(35)*2.0/1000.0; // factor 2 for compensating the voltage divider the pin 35 is attached to
  device_info.battery_level = 10 * min(10,int(floor(9.49 * (voltage_level - MIN_BATTERY_VOLTAGE) / (MAX_BATTERY_VOLTAGE - MIN_BATTERY_VOLTAGE))));
  if(machine.isInState(CONN)) OKCtrlCharacteristic.setValue((uint8_t*)&device_info,sizeof(info));
}

bool idle_to_conn(){
  return dev_connected;
}

bool conn_to_idle(){
  if(!dev_connected){
    on_conn_exit();
    return true;
  }
  return false;
}

bool conn_to_send(){
  if(exam_running){
    on_conn_exit();
    return true;
  }
  return false;
}

bool send_to_idle(){
  if(!dev_connected){
    exam_running = false;
    return true;
  }
  return false;
}

bool send_to_conn(){
  if(!exam_running){
    on_send_exit();
    return true;
  }
  return false;
}

void sm_setup(void){
  IDLE->addTransition(&idle_to_conn,CONN);
  CONN->addTransition(&conn_to_idle,IDLE);
  CONN->addTransition(&conn_to_send,SEND);
  SEND->addTransition(&send_to_idle,IDLE);
  SEND->addTransition(&send_to_conn,CONN);
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
    Serial.print("CMD:  ");
    Serial.println(pData[COMMAND],HEX);
    switch(pData[COMMAND]){
      case 0x00:
      exam_running = true; 
      break;
      case 0x10:
      bFilterActive = false;
      break;
      case 0x11:
      bFilterActive = true;
      break;
      case 0xFF:
      if(machine.isInState(SEND)) exam_running = false;
      break;
      default:
      break;
    }
  }
};

void ble_setup(void){
    // Create the BLE Device
  BLEDevice::init(BLE_SERVER_NAME);
  BLEDevice::setMTU(BLE_L2CAP_MTU);
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
  Serial.println("Waiting a client connection..");
}

void setup() {
  Serial.begin(115200);
  pinMode(STAT_LED_PIN, OUTPUT);
  pinMode(PUSH_BTN_PIN, INPUT_PULLUP);
  pinMode(5,OUTPUT);
  digitalWrite(5,HIGH);
  lpfilter_init(pFilter);
  timer_setup();
  adc_setup();
  sm_setup();
  ble_setup();
  batt_monitor.attach(6, measure_batt);
}

void loop() {
  machine.run();
}