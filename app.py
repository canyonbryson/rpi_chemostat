'''
chemostat code
Drew Porter
12-6-19
'''

'''
TO DO
- calibrate optical density
- web interface

'''
import busio # contains classes for rpi communication, such as I2C or spi. hence 'bus' - io
import threading # allows the proccessor to run multiple tasks simultaneously. Called concurrency.
import adafruit_mcp3xxx.mcp3008 as MCP #library for the mcp chip
from adafruit_mcp3xxx.analog_in import AnalogIn #library for the analog pins
import os # for certain commands
from datetime import datetime
import glob # identifies files of a a specific extension or pattern
import board # similar to gpio?
import subprocess # for certain terminal commands
import email_test as em
import time
import csv # for the csv file
import digitalio # for the digital pins
from PIL import Image, ImageDraw, ImageFont # for the screen
import adafruit_ssd1306 # for the screen
import RPi.GPIO as GPIO # for gpio pins
import pigpio #this is just for the LED. using RPi.GPIO for everything
              # else as I didn't want to have to go through and
              # rewrite everything else
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

from adafruit_motorkit import MotorKit
kit = MotorKit()    #Motor Library for the motor hat. Initialize each motor
m_out = kit.motor1
m_in = kit.motor2
m_air = kit.motor3
m_od = kit.motor4

import requests
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

import pygal #for the graph
from pygal.style import DarkStyle, NeonStyle

from subprocess import check_output, call #For the IP address, shutdown
IP = extra = ""
IP = check_output(['hostname', '-I']).strip().decode()
IP, extra = IP.split(" ", 1)
        
pi = pigpio.pi() #connect to loccl pi

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
temp = 20.0
setpoint_T = 37.0
pH = 7.00
optical_density = 0.00
setpoint_OD = .2
duty_cycle = 100 # sparging percentge
heat = 'OFF'
media = 'OFF'
purge = False
pump_time = 10 #seconds for the media in/out pumps to run
run = False
sendto = 'canyonbryson@gmail.com'
temp_list = []
OD_list = []
pH_list = []
timestamp_list = []
setTemp = []
setOD = []
syncMedia = False

@app.route('/')
def mainpage():
    global run
    state = "ON" if run else "OFF"
    return render_template('index.html', purge=purge, IP = IP, state=state, pump_time = pump_time, temp = temp, sparging = duty_cycle, OD = optical_density, setpoint_T = setpoint_T, setpoint_OD = setpoint_OD, duty_cycle = duty_cycle, pH = pH)

@app.route('/index')
def index():
    global run
    state = "ON" if run else "OFF"
    return redirect('/')

@app.route('/syncMedia')
def syncMedia():
    global syncMedia   #gets the status of the toggle switch
    Media = request.args.get('data').strip()
    sync = "On" if Media == "Off" else "Off"
    syncMedia = False if Media == "Off" else True
    return jsonify(result=sync)

@app.route('/graph')
def graph():
    global temp_list, OD_list, pH_list, timestamp_list, setpoint_T, setpoint_OD
    graph1 = pygal.StackedLine(show_y_guides=False, x_title='Time', y_title='Temperature', x_label_rotation=20, fill=True, interpolate='cubic')
    graph1.title = "Temp vs Time"
    graph1.x_labels = timestamp_list
    graph1.add('Temp', temp_list)
    graph1.add('Setpoint', setTemp)
    
    graph2 = pygal.StackedLine(show_y_guides=False, x_title='Time', y_title='Optical Density', x_label_rotation=20, fill=True, zero=setpoint_T, interpolate='cubic', style = DarkStyle)
    graph2.title = "OD vs Time"
    graph2.x_labels = timestamp_list
    graph2.add('OD', OD_list)
    graph2.add('Setpoint', setOD)

    
    graph3 = pygal.StackedLine(show_y_guides=False, x_title='Time', y_title='pH', x_label_rotation=20, fill=True, zero=setpoint_OD, interpolate='cubic', style = NeonStyle)
    graph3.title = "pH vs Time"
    graph3.x_labels = timestamp_list
    graph3.add('pH', pH_list)
    
    graph1=graph1.render_data_uri()
    graph2=graph2.render_data_uri()
    graph3=graph3.render_data_uri()

    
    return render_template('graph.html', graph1=graph1, graph2=graph2, graph3=graph3)

@app.route('/refresh')
def refresh():
    try:
        global temp, optical_density, pump_time, duty_cycle, pH, run
        state = "ON" if run else "OFF"
        return jsonify(temp=temp, OD=optical_density, pH=pH, sparging=duty_cycle, state=state)
    except Exception as e:
        return(str(e))
    

@app.route('/change_temp', methods = ['POST'])
def change_temp():
    global setpoint_T
    value = request.form['SP_T']
    setpoint_T = float(value)
#    print ("The new temp setpoint is: " , setpoint_T)
    return redirect('/')

@app.route('/change_OD', methods = ['POST'])
def change_OD():
    global setpoint_OD
    value = request.form['SP_OD']
    setpoint_OD = float(value)
#    print ("The new OD setpoint is: " , setpoint_OD)
    return redirect('/')

@app.route('/change_sparge', methods = ['POST'])
def change_sparge():
    global duty_cycle
    value = request.form['SP_sparge']
    duty_cycle = int(value)
#    print ("The new sparging percentage is: " , duty_cycle)
    return redirect('/')

@app.route('/media_time', methods = ['POST'])
def media_time():
    global pump_time
    value = request.form['time_media']
    pump_time = int(value)      
    return redirect('/')

@app.route('/primeOD', methods = ['POST'])
def primeOD():
    value = request.form['time_OD']
    wait = int(value)
    prime_pumps(wait ,'od')
    return redirect('/')
           
@app.route('/primeIN', methods = ['POST'])
def primeIN():
    value = request.form['time_IN']
    wait = int(value)
    prime_pumps(wait ,'IN')

    return redirect('/')
           
@app.route('/primeOUT', methods = ['POST'])
def primeOUT():
    value = request.form['time_OUT']
    wait = int(value)
    prime_pumps(wait ,'OUT')       
    return redirect('/')
           
@app.route('/start_run', methods = ['POST'])
def start_run():
    global run
    run = True
    return redirect('/')

@app.route('/finish', methods = ['POST'])
def finish():
    return render_template('verify.html')

@app.route('/end_run', methods = ['POST'])
def end_run():
    global run
    run = False
    return redirect('/')

@app.route('/powerOFF', methods=['POST'])
def powerOFF():
    call("sudo shutdown --poweroff", shell=True)
    #Add a 60 second countdown on the page
    return redirect('/')

@app.route('/email', methods = ['POST'])
def email():
    global sendto
    global run
    sendto = request.form['email']
#     print (emailto)
    run = False
    return redirect('/')
#     return render_template('goodbye.html')
 
def main():
    try:        
        t1 = threading.Thread(target = get_temp,)
        t2 = threading.Thread(target = ph,)
        t3 = threading.Thread(target = OD,)
        t4 = threading.Thread(target = screen,)
        t5 = threading.Thread(target = heater,)
        t6 = threading.Thread(target = sparging,)
        t7 = threading.Thread(target = menu,)
        t8 = threading.Thread(target = write_data)
        
        t1.daemon = True
        t2.daemon = True
        t3.daemon = True
        t4.daemon = True
        t5.daemon = True
        t6.daemon = True
        t7.daemon = True
        t8.daemon = True
        
        t1.start()
        t2.start()
        t3.start()
        t4.start()
        t5.start()
        t6.start()
        t7.start()
        t8.start()
        

#        if __name__ == '__main__':
#            app.run(host=IP, port=5000)
            

            
    except KeyboardInterrupt:
        GPIO.cleanup()
        # turn off the LED for optical density
        pi.write(12,0)
        pi.stop()
        
        print ('Quit')
        
#     GPIO.cleanup()
#     #turn off the led
#     pi.write(12,0)
#     pi.stop()
#     print ("Done")
#     file.close()
#     em.email(sendto, filename)

def prime_pumps(wait, pump):
    global purge, m_in, m_out, m_od
    
    purge = True

    if pump == 'IN':
        m_in.throttle = 1.0
        time.sleep(wait)
        m_in.throttle = 0
    if pump == 'OUT':
        m_out.throttle = 1.0
        time.sleep(wait)
        m_out.throttle = 0    
    if pump == 'od':
        m_od.throttle = 1.0
        time.sleep(wait)
        m_od.throttle = 0
        
    purge = False
    
def write_data():
    while True:
        if run or not run:    
            fieldnames=['timestamp','temp','setpoint_T','OD','setpoint_OD','pH','sparging', 'media']
            now = datetime.now()
            date = now.strftime("%m-%d-%y_%H:%M:%S")
            with open('csv/{}.csv'.format(date),'w') as csv_file:
                csv_writer=csv.DictWriter(csv_file, fieldnames=fieldnames)
                csv_writer.writeheader()

            while True:
                with open('csv/{}.csv'.format(date),'a') as csv_file:
                    csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                    now1 = datetime.now()
                    date1 = now.strftime("%m-%d-%y_%H:%M:%S")
                    global temp, optical_density, duty_cycle, pH, pump_time, setpoint_OD, setpoint_T
                    info = {
                              'timestamp':  date1,
                              'temp': temp,
                              'setpoint_T':setpoint_T,
                              'OD': optical_density,
                              'setpoint_OD': setpoint_OD,
                              'pH':pH,
                              'sparging': duty_cycle,
                              'media':pump_time
                              }
                    csv_writer.writerow(info)
                    setTemp.append(setpoint_T)
                    setOD.append(setpoint_OD)
                    temp_list.append(temp)
                    OD_list.append(optical_density)
                    pH_list.append(pH)
                    timestamp_list.append(date1)
                time.sleep(3)
                
            
def menu():
    global setpoint_T
    global setpoint_OD
    global duty_cycle
    global run
    
 #   print('IP: ' + IP)
#    time.sleep(60*2)  # display IP address for 2 minutes
    
    while True:
#         while run == True:
        selection = int(input('Select the setpoint you would like to change.\n1: Temperature\n2: Sparging\n3: Optical Density\n4: Run\n5: Quit\n'))
        
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
            run = True
        if selection == 5:
            verify = str(input('Are you sure you want to quit? Y/N\n'))
            
            if (verify == 'Y' or verify == 'y'):
                run = False
            else:
                run = True
        else:
            print ("Invalid input, please enter the corresponding number")
                     
def sparging():
    global duty_cycle, m_air
    
    speedair = duty_cycle / 100
    
    m_air.throttle = speedair
    
    previous = 0 # previous duty cycle value to check to
                 # see if it has beenchanged
    while True:
        while run == True:
            if duty_cycle != previous:
                speedair = duty_cycle / 100
                previous = duty_cycle
                m_air.throttle = speedair
    #         time.sleep(3)
        if run == False:
#             duty_cycle = 0
            speedair = 0
        
def OD():
    global optical_density
    global media, syncMedia
    
    #setup the LED for optical density
    led = 12

    pi.set_mode(led, pigpio.OUTPUT)
    pi.set_PWM_range(led, 100) #range is now 0-100
    pi.set_PWM_frequency(led, 10000) #set the frequency
    
    
    # create an analog input channel on pin 1
    chan1 = AnalogIn(mcp, MCP.P0) #OD
    
    raw = [0,0,0,0,0,0,0,0,0,0]
    
    while True:
        while run == False and purge == False:
            m_in.throttle = 0
            m_out.throttle = 0
            m_od.throttle = 0
            pi.set_PWM_dutycycle(led , 0) # turn off the LED
            
        while run == True:       
            summation = 0
            # turn on the LED and motor
            m_od.throttle = 1
            time.sleep(40) # allow for the OD module to receive the current media
            pi.set_PWM_dutycycle(led, 5)
            
            # read 10 values at 0.5 sec intervals from the photoresistor
            for i in range (10):
                raw[i] = chan1.voltage
                time.sleep(0.5)
                
            pi.set_PWM_dutycycle(led , 0) # turn off the LED
            m_od.throttle = 0      # and motor
            
            # go through and order the readings from smallest to largest
            for i in range (10):
                for j in range (i+1, 10):
                    if raw[i]>raw[j]: # go through and order the readings from smallest to largest
                        raw[i], raw[j] = raw[j], raw[i]
                        
            # average the middle six readings together
            for i in range (2,8):
                summation += raw[i]
            average = summation / 6
            
            optical_density = round((average - 01.7) * 10, 3)
    #         print (d, optical_density)
            
            # change out media if the OD is higher than the setpoint
            if optical_density > setpoint_OD and not syncMedia:
                media = 'IN'
                m_out.throttle = 1
                time.sleep(pump_time)
                media = 'OUT'
                m_out.throttle = 0
                m_in.throttle = 1
                time.sleep(pump_time)
                media = 'OFF'
                m_in.throttle = 0
                
            elif optical_density > setpoint_OD and syncMedia:
                media = 'ON'
                m_in.throttle = 1
                m_out.throttle = 1
                time.sleep(pump_time)
                media = 'OFF'
                m_out.throttle = 0
                m_in.throttle = 0


            time.sleep(1*60) # take OD every minute. Also allows for
                             # new media to mix well and give accurate
                             # readings

def ph():
    global pH
    # create an analog input channel on pin 2
    try:
        chan2 = AnalogIn(mcp, MCP.P1) # pH
    except:
        print("not connected to pH sensor")
    # values from calibration
    v4 = 1.9870127412832845 # voltage for pH 4, format (x1,y1) = (voltage, pH)
    v10 = 1.3067801937895778 # voltage for pH 10, format (x2,y2) = (voltage, pH)
    slope = (10-4)/(v10-v4) # (y2-y1/x2-x1)
    
    raw = []
    for i in range(100):
        raw += [0]
     # initialize an array for the raw values
        
    while True:
        while run == True:
            summation = 0

            # read 10 values at 0.5 sec intervals from the pH probe
            for i in range (100):
                raw[i] = chan2.voltage
                time.sleep(0.25)
                
            # go through and order the readings from smallest to largest
            for i in range (100):
                for j in range (i+1, 100):
                    if raw[i]>raw[j]: # go through and order the readings from smallest to largest
                        raw[i], raw[j] = raw[j], raw[i]
                        
            # average the middle six readings together
            for i in range (20,80):
                summation += raw[i]
            average = summation / 60
            # y = y1 + m(x-x1)
            pH = round(10 + slope*(average - v10),2)  # use point slope from calibration to determine ph value
            
            time.sleep(5) # pH every 1/2 minute
    
def screen(): 
    loading = True
    while loading:
        try:
    # setup for the screen
    # Using for SPI
            spi = board.SPI()
            oled_reset = digitalio.DigitalInOut(board.D17)
            oled_cs = digitalio.DigitalInOut(board.D5)
            oled_dc = digitalio.DigitalInOut(board.D6)
            oled = adafruit_ssd1306.SSD1306_SPI(128, 64, spi, oled_dc, oled_reset, oled_cs)
            loading = False
        except:
            loading = True
            
    try: 
    # Load font.
        font = ImageFont.truetype('/home/pi/Chemostat/arial.ttf', 12)
    except:
        font = ImageFont.load_default()
            
    # get the IP address
    IP = str(subprocess.check_output(["hostname", "-I"]).split()[0])
    IP = IP[2:-1]
    
    while True:
        if run == True:
            state = "ON"
        if run == False:
            state = "OFF"
        # Create blank image for drawing.
        
        # Make sure to create image with mode '1' for 1-bit color.
        image = Image.new('1', (oled.width, oled.height))
        # Get drawing object to draw on image.
        draw = ImageDraw.Draw(image)
        # Draw Some Text
        draw.text((1, 1), 'Temp: '+ str(temp)+' / '+ str(setpoint_T) + ' C', font=font, fill=255)
        draw.text((1, 15), 'Heat: ' + heat + ' St: ' + state , font=font, fill=255)
        draw.text((1, 28), 'Sparging: '+ str(duty_cycle)+'%', font=font, fill=255)
        draw.text((1, 41), 'pH: ' + str(pH) + ' OD: ' + str(optical_density), font=font, fill=255)
        draw.text((1, 53), 'IP: ' + str(IP), font=font, fill=255)
         
        # Display image
        oled.image(image)
        oled.show()
        #oled.dispaly()
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
        while temp < 0:
            temp = round(read_temp(),2)   
        time.sleep(2)

def heater():
    
    #setup the relay
    relay = 14
    GPIO.setup(relay, GPIO.OUT)
    GPIO.output(relay, True)
    
    while True:
        while run == False:
            GPIO.output(relay, True)
            heat = 'OFF'
            
        while run == True:
            # turn off the relay once it reaches the setpont
            if temp >= setpoint_T:
                GPIO.output(relay, True) # set relay to off
                heat = 'OFF'
            # turn on the relay once it is at or below the setpoint by
            # 0.5 C
            if temp <= setpoint_T - 0.5: 
                GPIO.output(relay, False) # set relay to on
                heat = 'ON'
            time.sleep(2)
  

            

main()
