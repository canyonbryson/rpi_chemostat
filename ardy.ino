#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <OneWire.h> 
#include <DallasTemperature.h>
#define OLED_MOSI  11                   //D1
#define OLED_CLK   12                   //D0
#define OLED_DC    9
#define OLED_CS    8
#define OLED_RESET 10
#define ONE_WIRE_BUS 2
  
const int screen_power = 4;                // Use one of the digital pins as a power pin for the screen           
const int Thermometer = 2;              //Thermometer plugged into digital slot #2
int relay = 5;                          // define the relay pin
float temp = 0.0;                       // initialize temp to zero 
float invalidFlo = -127.00;
float setpoint = 37.0;                  // Desired temperature setpoint
float differential = 0.5;               // difference between the setpoint and the desired temp for the relay to kick on
String heat = "Heater: OFF"; 

Adafruit_SSD1306 display(OLED_MOSI, OLED_CLK, OLED_DC, OLED_RESET, OLED_CS);
OneWire oneWire(ONE_WIRE_BUS); 
DallasTemperature sensors(&oneWire);


void setup() {
  Serial.begin(9600); 
  sensors.begin(); 
  display.begin(SSD1306_SWITCHCAPVCC);
  display.display();
  delay(1000);
  display.clearDisplay();
  display.setTextColor(WHITE);
  pinMode(relay,OUTPUT);
  pinMode(screen_power, OUTPUT);
  digitalWrite (screen_power, HIGH);     // turn power to the screen on
  digitalWrite (relay, HIGH);           // set the relay to off
  sensing();
}


void loop() {
  
  sensors.requestTemperatures();
  temp = sensors.getTempCByIndex(0); 
  
  while (temp == invalidFlo){
    temp = sensors.getTempCByIndex(0);
  }     
  if(temp == invalidFlo){
    Serial.println("-127 ERROR");
  }
  if(temp >= setpoint){
    digitalWrite(relay, HIGH);        // turn relay off NOTE: high is off
    heat = "Heater: OFF";
}
  if(temp <= setpoint - differential){
    digitalWrite(relay, LOW);        // turn relay on
    heat = "Heater: ON";
}
  printToDisplay(heat, "Temp: (C) ", temp, false, 0);
  
  Serial.print(temp);
  Serial.print(" ");
  Serial.println(heat);
    
  delay(2000);
}
void sensing(){
  for(int i=5;i!=0;i--){ 
    sensors.requestTemperatures();    // Get temperature from sensor
    temp = sensors.getTempCByIndex(0);// Sort by index, since we only have one sensor it is index 0
    Serial.print("Temp, ");           // Print temperature to Serial Monitor
    Serial.print(temp);

    printToDisplay("Sensing ", "Temp: (C)", temp, true, i); // Call printToDisplay function
     
    Serial.print(" i = ");           // Print to Serial Monitor
    Serial.println(i);
    delay(950);
  }
  Serial.println("Sensing Completed");
}

void printToDisplay(String firstLine, String secondLine, float temp, bool sensing, int delayTime){
  display.clearDisplay();             // Clear the display
  display.setCursor(0,0);             // Start in top left corner
  display.setTextSize(1);             // Set text size
  display.print(firstLine);           // Print the first line string
  if(sensing){                        // Print countdown
    display.print(delayTime);      
  }
  display.setCursor(0,8);            // Move cursor to second line
  display.print(secondLine);          // Print the second line string
  display.setTextSize(2);             // Change text size
  display.setCursor(0,18);            // Move the cursor to the third line
  display.print(temp);                // Print the temperature
  display.display();                  // Send changes to display
}

// Screen Notes:
// https://github.com/jandelgado/arduino/wiki/SSD1306-based-OLED-connected-to-Arduino
// https://github.com/jandelgado/arduino/blob/master/ssd1306_sample_adafruit/ssd1306_sample_adafruit.ino

// Temperature Sensor Notes:
// https://create.arduino.cc/projecthub/TheGadgetBoy/ds18b20-digital-temperature-sensor-and-arduino-9cc806

// Heater Relay Notes:
// https://randomnerdtutorials.com/guide-for-relay-module-with-arduino/
// https://www.ebay.com/itm/2PCS-1-Channel-DC-5V-Relay-Switch-Board-Module-for-Arduino-Raspberry-Pi-ARM-AVR/322465448278?hash=item4b14704156:g:dzgAAOSwSlBY2bTH
