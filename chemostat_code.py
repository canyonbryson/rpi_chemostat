'''
chemostat code
Drew Porter
12-6-19
'''
import busio
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn
import os
import glob
import board
import time
import digitalio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# setup for the screen
# Using for SPI
spi = board.SPI()
oled_reset = digitalio.DigitalInOut(board.D17)
oled_cs = digitalio.DigitalInOut(board.D5)
oled_dc = digitalio.DigitalInOut(board.D6)
oled = adafruit_ssd1306.SSD1306_SPI(128, 64, spi, oled_dc, oled_reset, oled_cs)

# Setup for temperature sensor
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
 
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

#Setup for the MCP3008
# create the spi bus 
spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)

# create the cs (chip select)
cs = digitalio.DigitalInOut(board.D13)

# create the mcp object
mcp = MCP.MCP3008(spi, cs)

# create an analog input channel on pins 1&2
chan1 = AnalogIn(mcp, MCP.P0) #OD
chan2 = AnalogIn(mcp, MCP.P1) # pH

#setup the relay
relay = 14
GPIO.setup(relay, GPIO.OUT)

#setup the LED
led = 20
GPIO.setup(led, GPIO.OUT)
def main():
    try:
        while True:
            setpoint_T = 37.0
            setpoint_OD = 0.6
            
            temp=read_temp()
            #print (temp)
            pH = ph()
            #print(pH)
            optical_density = round (OD(),3)
            #print (optical_density)
            pumps = 'ON'
            heat = heater(temp, setpoint_T)
            #print (heat)
            screen(temp, pH, heat, pumps, optical_density)
            #time.sleep(1)
            
    except KeyboardInterrupt:
        GPIO.cleanup()
        print ('Quit')
        
    GPIO.cleanup()
    
def OD():
    
    raw = [0,0,0,0,0,0,0,0,0,0]
    summation = 0
    # turn on the LED
    GPIO.output(led , True)
    
    # read 10 values at 0.2 sec intervals from the photoresistor
    for i in range (10):
        raw[i] = chan2.voltage
        time.sleep(0.2)
        
    GPIO.output(led , False) # turn off the LEd
    
    # go through and order the readings from smallest to largest
    for i in range (10):
        for j in range (i+1, 10):
            if raw[i]>raw[j]: # go through and order the readings from smallest to largest
                #temp = raw[i]
                #raw[i] = raw[j]
               # raw[i] = temp
                raw[i], raw[j] = raw[j], raw[i]
                
    # average the middle six readings together
    for i in range (2,8):
        summation += raw[i]
    average = summation / 6
    
    OD = average
    
    return OD

def ph():

    # values from calibration
    v4 = 1.9870127412832845 # voltage for pH 4, format (x1,y1) = (voltage, pH)
    v10 = 1.3067801937895778 # voltage for pH 10, format (x2,y2) = (voltage, pH)
    slope = (10-4)/(v10-v4) # (y2-y1/x2-x1)
    raw = [0,0,0,0,0,0,0,0,0,0] # initialize an array for the raw values
    summation = 0

    # read 10 values at 0.2 sec intervals from the pH probe
    for i in range (10):
        raw[i] = chan2.voltage
        time.sleep(0.2)
        
    # go through and order the readings from smallest to largest
    for i in range (10):
        for j in range (i+1, 10):
            if raw[i]>raw[j]: # go through and order the readings from smallest to largest
                temp = raw[i]
                raw[i] = raw[j]
                raw[i] = temp
                
    # average the middle six readings together
    for i in range (2,8):
        summation += raw[i]
    average = summation / 6
    # y = y1 + m(x-x1)
    pH = 10 + slope*(average - v10)  # use point slope from calibration to determine ph value
    time.sleep(5)
    
    return round(pH, 3)
    
def screen(temp, ph, heater, pumps, OD): 
     
    # Change these
    # to the right size for your display!
    WIDTH = 128
    HEIGHT = 64     # Change to 64 if needed
    BORDER = 5
     
    # Clear display.
    #oled.fill(0)
    #oled.show()
     
    # Create blank image for drawing.
    # Make sure to create image with mode '1' for 1-bit color.
    image = Image.new('1', (oled.width, oled.height))
     
    # Get drawing object to draw on image.
    draw = ImageDraw.Draw(image)
    
    # Load font.
    font = ImageFont.truetype('arial.ttf', 12)
 
    # Draw Some Text
    draw.text((1, 1), 'Temp: '+ str(round(temp,2)), font=font, fill=255)
    draw.text((1, 15), 'Heat: '+ heater + ' Pump: ' + pumps, font=font, fill=255)
    draw.text((1, 28), 'OD: ' + str(OD), font=font, fill=255)
    draw.text((1, 42), 'pH: ' + str(ph), font=font, fill=255)
     
    # Display image
    oled.image(image)
    oled.show()

def read_temp_raw():
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines
 
def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        #temp_f = temp_c * 9.0 / 5.0 + 32.0
        return temp_c

def heater(temp, setpoint):
    if temp > setpoint:
        GPIO.output(relay, True) # set relay to off
        return 'OFF'
    if temp < setpoint:
        GPIO.output(relay, False) # set relay to on
        return 'ON'
        
main()

