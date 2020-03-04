'''
chemostat code
Drew Porter
12-6-19
'''

'''
TODO
- web interface

'''
import busio
import threading
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn
import os
from datetime import datetime
import glob
from flask import Flask
import board
import time
import digitalio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# setup for DS18B20 temperature probe
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
 
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

#Setup for the MCP3008 for the OD and pH functions
# create the spi bus 
spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
# create the cs (chip select)
cs = digitalio.DigitalInOut(board.D13)
# create the mcp object
mcp = MCP.MCP3008(spi, cs)

# initialize global variables for threading
temp = 40.0
setpoint_T = 37.0
pH = 7.00
optical_density = 0.00
setpoint_OD = 2
duty_cycle = 0
heat = 'OFF'
media = 'OFF'
run = True

def main():
    try:
        print ('Initializing\n')
        
        t1 = threading.Thread(target = get_temp,)
        t2 = threading.Thread(target = ph,)
        t3 = threading.Thread(target = OD,)
        t4 = threading.Thread(target = screen,)
        t5 = threading.Thread(target = heater,)
        t6 = threading.Thread(target = sparging,)
        t7 = threading.Thread(target = menu,)
        
        t1.daemon = True
        t2.daemon = True
        t3.daemon = True
        t4.daemon = True
        t5.daemon = True
        t6.daemon = True
        t7.daemon = True  
        
        t1.start()
        t2.start()
        t3.start()
        t4.start()
        t5.start()
        t6.start()
        t7.start()
        
        now = datetime.now()
        date = now.strftime("%m-%d-%y_%H:%M:%S")
        print ('\n',date)
#         file = open('{}.csv'.format(date),'w+')
        file = open('test.csv','w+')
        file.write('Chemostat run of {}'.format(date))
        file.write('\nTimestamp, Temperature, Temp Setpoint, Heater, pH, OD, OD Setpoint, Media, Sparging')
        
        time.sleep(2) # sleep to allow readings to settle
        
        while run == True:
            now1 = datetime.now()
            date1 = now1.strftime("%m-%d-%y_%H:%M:%S")

            file.write('\n{0},{1},{2},{3},{4},{5},{6},{7},{8}%,'.format(date1,
                    temp,setpoint_T,heat,pH,optical_density,setpoint_OD, media,duty_cycle))
        
            time.sleep(1)
            
    except KeyboardInterrupt:
        GPIO.cleanup()
        file.close
        print ('Quit')
        
    GPIO.cleanup()
    print ("Done")
    file.close()
    
def menu():
    global setpoint_T
    global setpoint_OD
    global duty_cycle
    global run
    
    while True:
        selection = int(input('Select the setpoint you would like to change.\n1: Temperature\n2: Sparging\n3: Optical Density\n4: Quit\n'))
        
        if selection == 1:
            print ('Current Setpoint:',setpoint_T,'C')
            setpoint_T = float(input('Enter the new temperature setpoint.\n'))
        
        if selection == 2:
            print ('Current percentage: ', duty_cycle,'%')
            duty_cycle = int(input('Desired sparging percentage (0-100).\n'))
            
        if selection == 3:
            print ('Current Setpoint: ', setpoint_OD)
            setpoint_OD = float(input('Enter the new optical density setpoint.\n'))
        
        if selection == 4:
            verify = str(input('Are you sure you want to quit? Y/N\n'))
            
            if (verify == 'Y' or verify == 'y'):
                run = False
            else:
                run = True
            
def sparging():
    global duty_cycle
    # setup pins for the sparger
    en2 = 12 # air pump enable
    m_air = 23 # air pump
    GPIO.setup(en2, GPIO.OUT)
    GPIO.setup(m_air, GPIO.OUT)
    speedair = GPIO.PWM(en2, 1000)
    speedair.start(duty_cycle)
    
    GPIO.output(en2 , True)
    GPIO.output(m_air , True)
    
    previous = 0 # previous duty cycle value to check to
                 # see if it has beenchanged
    while True:
        
        if duty_cycle != previous:
            speedair.ChangeDutyCycle(duty_cycle)
            previous = duty_cycle
#         time.sleep(3)
        
def OD():
    global optical_density
    global media
    
    #setup the LED for optical density
    led = 20
    GPIO.setup(led, GPIO.OUT)
    
    # set up pins for peristaltic pumps
    en1 = 18 # media pump enable
    m_in = 25 # media in 
    m_out = 24 # media out
    GPIO.setup(en1, GPIO.OUT)
    GPIO.setup(m_in, GPIO.OUT)
    GPIO.setup(m_out, GPIO.OUT)
    GPIO.output(en1, False)
    GPIO.output(m_in, False)
    GPIO.output(m_out, False)
    
    # create an analog input channel on pin 1
    chan1 = AnalogIn(mcp, MCP.P0) #OD
    
    raw = [0,0,0,0,0,0,0,0,0,0]
    
#     while True:
    for d in range (1,11):
        
        summation = 0
        # turn on the LED
        GPIO.output(led , True)
        
        # read 10 values at 0.5 sec intervals from the photoresistor
        for i in range (10):
            raw[i] = chan1.voltage
            time.sleep(0.5)
            
        GPIO.output(led , False) # turn off the LED
        
        # go through and order the readings from smallest to largest
        for i in range (10):
            for j in range (i+1, 10):
                if raw[i]>raw[j]: # go through and order the readings from smallest to largest
                    #temp = raw[i]
                    #raw[i] = raw[j]
                    #raw[i] = temp
                    raw[i], raw[j] = raw[j], raw[i]
                    
        # average the middle six readings together
        for i in range (2,8):
            summation += raw[i]
        average = summation / 6
        
        optical_density = round(average,2)
        print (d, optical_density)
        # change out media if the OD is higher than the setpoint
        if optical_density > setpoint_OD:
            media = 'IN'
            GPIO.output(en1 , True)
            GPIO.output(m_out , True)
            time.sleep(10)
            media = 'OUT'
            GPIO.output(m_out, False)
            GPIO.output(m_in, True)
            time.sleep(10)
            media = 'OFF'
            GPIO.output(en1 , False)
            GPIO.output(m_in , False)
        
        time.sleep(.25*60) # take OD every minute. Also allows for
                         # new media to mix well and give accurate
                         # readings

def ph():
    global pH
    # create an analog input channel on pin 2
    chan2 = AnalogIn(mcp, MCP.P1) # pH
    
    # values from calibration
    v4 = 1.9870127412832845 # voltage for pH 4, format (x1,y1) = (voltage, pH)
    v10 = 1.3067801937895778 # voltage for pH 10, format (x2,y2) = (voltage, pH)
    slope = (10-4)/(v10-v4) # (y2-y1/x2-x1)
    
    raw = [0,0,0,0,0,0,0,0,0,0] # initialize an array for the raw values
        
    while True:
        summation = 0

        # read 10 values at 0.5 sec intervals from the pH probe
        for i in range (10):
            raw[i] = chan2.voltage
            time.sleep(0.5)
            
        # go through and order the readings from smallest to largest
        for i in range (10):
            for j in range (i+1, 10):
                if raw[i]>raw[j]: # go through and order the readings from smallest to largest
                    #temp = raw[i]
                    #raw[i] = raw[j]
                    #raw[i] = temp
                    raw[i], raw[j] = raw[j], raw[i]
                    
        # average the middle six readings together
        for i in range (2,8):
            summation += raw[i]
        average = summation / 6
        # y = y1 + m(x-x1)
        pH = round(10 + slope*(average - v10),2)  # use point slope from calibration to determine ph value
        
        time.sleep(15)
    
def screen(): 
    global temp
    global pH
    global optical_density
    global heat
    # setup for the screen
    # Using for SPI
    spi = board.SPI()
    oled_reset = digitalio.DigitalInOut(board.D17)
    oled_cs = digitalio.DigitalInOut(board.D5)
    oled_dc = digitalio.DigitalInOut(board.D6)
    oled = adafruit_ssd1306.SSD1306_SPI(128, 64, spi, oled_dc, oled_reset, oled_cs)
     
    # Load font.
    font = ImageFont.truetype('arial.ttf', 12)
    while True:
        # Create blank image for drawing.
        # Make sure to create image with mode '1' for 1-bit color.
        image = Image.new('1', (oled.width, oled.height))
        # Get drawing object to draw on image.
        draw = ImageDraw.Draw(image)
        # Draw Some Text
        draw.text((1, 1), 'Temp: '+ str(temp)+'C '+heat, font=font, fill=255)
        draw.text((1, 15), 'Sparging: '+ str(duty_cycle)+'%', font=font, fill=255)
        draw.text((1, 28), 'OD: ' + str(optical_density), font=font, fill=255)
        draw.text((1, 42), 'pH: ' + str(pH), font=font, fill=255)
         
        # Display image
        oled.image(image)
        oled.show()
        time.sleep(2)

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

# for some reason threading wont work with the read_temp function
# this function allows temperature to be read in a thread
def get_temp():
    global temp
    
    while True:
        temp = round(read_temp(),2)
        time.sleep(2)

def heater():
    global heat
    global temp
    global setpoint_T
    
    #setup the relay
    relay = 14
    GPIO.setup(relay, GPIO.OUT)
    GPIO.output(relay, True)
    
    while True:
        if temp > setpoint_T:
            GPIO.output(relay, True) # set relay to off
            heat = 'OFF'
        if temp < setpoint_T:
            GPIO.output(relay, False) # set relay to on
            heat = 'ON'
        time.sleep(2)
        
main()

