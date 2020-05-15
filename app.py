'''
chemostat code
Drew Porter
12-6-19
'''

'''
TODO

- fit everything in lid
- design controller container
- calibrate optical density
- web interface

'''
import busio
import threading
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn
import os
from datetime import datetime
import glob
import board
import subprocess
import email_test as em
import time
import digitalio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
import RPi.GPIO as GPIO
import pigpio #this is just for the LED. using RPi.GPIO for everything
              # else as I didn't want to have to go through and
              # rewrite everything else
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, emit #for live data

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
socketio = SocketIO(app) #create an instance of a web socket

from subprocess import check_output #For the IP address
IP = check_output(['hostname', '-I']).strip()

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
temp = 40.0
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
sendto = 'drewcliffporter@gmail.com'

@app.route('/')
def mainpage():
    if run == True:
        state = 'ON'
    if run == False:
        state = 'OFF'
    return render_template('index.html', IP = IP, state=state, pump_time = pump_time, temp = temp, sparging = duty_cycle, OD = optical_density, setpoint_T = setpoint_T, setpoint_OD = setpoint_OD, duty_cycle = duty_cycle)

@app.route('/refresh', methods = ['POST', 'GET'])
def refresh():
    return redirect('/')

def refreshing():
    while True:
        # Get current variable to send back
        global temp, optical_density, pump_time, duty_cycle
        tuple1 = (temp, optical_density, duty_cycle, pump_time)
        socketio.send("refreshing", (temp, optical_density, duty_cycle, pump_time))
        time.sleep(1)
    

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
    response = request.form['answer']
    print (response)
    if response == 'yes':
        return render_template('email.html')
    if response == 'no':
        return redirect('/')

@app.route('/powerOFF', methods=['POST'])
def powerOFF():
    #power off code
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
        t7 = threading.Thread(target = refreshing,)
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
        

        if __name__ == '__main__':
            socketio.run(app)
#             app.run()
            

            
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
    global purge
    en1 = 18 # media pump enable
    m_in = 25 # media in 
    m_out = 24 # media out
    m_OD = 16 # OD pump
    GPIO.setup(en1, GPIO.OUT)
    GPIO.setup(m_in, GPIO.OUT)
    GPIO.setup(m_out, GPIO.OUT)
    GPIO.setup(m_OD, GPIO.OUT)
    GPIO.output(en1, True)
    GPIO.output(m_in, False)
    GPIO.output(m_out, False)
    GPIO.output(m_OD, False)
    purge = True
    
    if pump == 'IN':
        GPIO.output(m_in, True)
        time.sleep(wait)
        GPIO.output(m_in, False)
    if pump == 'OUT':
        GPIO.output(m_out, True)
        time.sleep(wait)
        GPIO.output(m_out, False)    
    if pump == 'od':
        GPIO.output(m_OD, True)
        time.sleep(wait)
        GPIO.output(m_OD, False)
        
    purge = False
    
def write_data():
    while True:
        if run == True:   
            now = datetime.now()
            date = now.strftime("%m-%d-%y_%H:%M:%S")
        #         print ('\n',date)
            file = open('{}.csv'.format(date),'w+')
            filename = '{}.csv'.format(date)
        #         file = open('test1.csv','w+')
        #         filename = ('test1.csv')
            file.write('Chemostat run of {}'.format(date))
            file.write('\nTimestamp, Temperature, Temp Setpoint, Heater, pH, OD, OD Setpoint, Media, Sparging')
            
            time.sleep(10) # sleep to allow readings to become accurate
                            # and to settle    
            # write data to a file
            while run == True:
                now1 = datetime.now()
                date1 = now1.strftime("%m-%d-%y_%H:%M:%S")

                file.write('\n{0},{1},{2},{3},{4},{5},{6},{7},{8}%,'.format(date1,
                        temp,setpoint_T,heat,pH,optical_density,setpoint_OD, media,duty_cycle))
            
                time.sleep(1)
                
            file.close
            em.email(sendto, filename)
        
def menu():
    global setpoint_T
    global setpoint_OD
    global duty_cycle
    global run
    
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
            print ("Invalid input, please enter the cooresponding number")
                     
def sparging():
    global duty_cycle
    # setup pins for the sparger
    en2 = 20 # air pump enable
    m_air = 23 # air pump
    GPIO.setup(en2, GPIO.OUT)
    GPIO.setup(m_air, GPIO.OUT)
    speedair = GPIO.PWM(m_air, 1000)
    speedair.start(duty_cycle)
    
    GPIO.output(en2 , True)
    GPIO.output(m_air , True)
    
    previous = 0 # previous duty cycle value to check to
                 # see if it has beenchanged
    while True:
        while run == True:
            if duty_cycle != previous:
                speedair.ChangeDutyCycle(duty_cycle)
                previous = duty_cycle
    #         time.sleep(3)
        if run == False:
#             duty_cycle = 0
            speedair.ChangeDutyCycle(0)
        
def OD():
    global optical_density
    global media
    
    #setup the LED for optical density
    led = 12

    pi.set_mode(led, pigpio.OUTPUT)
    pi.set_PWM_range(led, 100) #range is now 0-100
    pi.set_PWM_frequency(led, 10000) #set the frequency
    
    # set up pins for peristaltic pumps for media
    en1 = 18 # media pump enable
    m_in = 25 # media in 
    m_out = 24 # media out
    m_OD = 16 # OD pump
    GPIO.setup(en1, GPIO.OUT)
    GPIO.setup(m_in, GPIO.OUT)
    GPIO.setup(m_out, GPIO.OUT)
    GPIO.setup(m_OD, GPIO.OUT)
    GPIO.output(en1, False)
    GPIO.output(m_in, False)
    GPIO.output(m_out, False)
    GPIO.output(m_OD, False)
    
    # create an analog input channel on pin 1
    chan1 = AnalogIn(mcp, MCP.P0) #OD
    
    raw = [0,0,0,0,0,0,0,0,0,0]
    
    while True:
        while run == False and purge == False:
            GPIO.output(en1, False)
            GPIO.output(m_in, False)
            GPIO.output(m_out, False)
            GPIO.output(m_OD, False)
            pi.set_PWM_dutycycle(led , 0) # turn off the LED
            
        while run == True:       
            summation = 0
            # turn on the LED and motor
            GPIO.output(m_OD, True)
            time.sleep(40) # allow for the OD module to receive the current media
            pi.set_PWM_dutycycle(led, 5)
            
            # read 10 values at 0.5 sec intervals from the photoresistor
            for i in range (10):
                raw[i] = chan1.voltage
                time.sleep(0.5)
                
            pi.set_PWM_dutycycle(led , 0) # turn off the LED
            GPIO.output(m_OD, False)      # and motor
            
            # go through and order the readings from smallest to largest
            for i in range (10):
                for j in range (i+1, 10):
                    if raw[i]>raw[j]: # go through and order the readings from smallest to largest
                        raw[i], raw[j] = raw[j], raw[i]
                        
            # average the middle six readings together
            for i in range (2,8):
                summation += raw[i]
            average = summation / 6
            
            optical_density = round(average,2)
    #         print (d, optical_density)
            
            # change out media if the OD is higher than the setpoint
            if optical_density > setpoint_OD:
                media = 'IN'
                GPIO.output(en1 , True)
                GPIO.output(m_out , True)
                time.sleep(pump_time)
                media = 'OUT'
                GPIO.output(m_out, False)
                GPIO.output(m_in, True)
                time.sleep(pump_time)
                media = 'OFF'
                GPIO.output(en1 , False)
                GPIO.output(m_in , False)
            
            time.sleep(1*60) # take OD every minute. Also allows for
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
        while run == True:
            summation = 0

            # read 10 values at 0.5 sec intervals from the pH probe
            for i in range (10):
                raw[i] = chan2.voltage
                time.sleep(0.5)
                
            # go through and order the readings from smallest to largest
            for i in range (10):
                for j in range (i+1, 10):
                    if raw[i]>raw[j]: # go through and order the readings from smallest to largest
                        raw[i], raw[j] = raw[j], raw[i]
                        
            # average the middle six readings together
            for i in range (2,8):
                summation += raw[i]
            average = summation / 6
            # y = y1 + m(x-x1)
            pH = round(10 + slope*(average - v10),2)  # use point slope from calibration to determine ph value
            
            time.sleep(15)
    
def screen(): 
    
    # setup for the screen
    # Using for SPI
    spi = board.SPI()
    oled_reset = digitalio.DigitalInOut(board.D17)
    oled_cs = digitalio.DigitalInOut(board.D5)
    oled_dc = digitalio.DigitalInOut(board.D6)
    oled = adafruit_ssd1306.SSD1306_SPI(128, 64, spi, oled_dc, oled_reset, oled_cs)
     
    # Load font.
    font = ImageFont.truetype('arial.ttf', 12)
    
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
        draw.text((1, 15), 'Heater: ' + heat + ' ' + state , font=font, fill=255)
        draw.text((1, 28), 'Sparging: '+ str(duty_cycle)+'%', font=font, fill=255)
        draw.text((1, 40), 'pH: ' + str(pH) + ' OD: ' + str(optical_density), font=font, fill=255)
        draw.text((1, 52), 'IP: ' + str(IP), font=font, fill=255)
         
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

