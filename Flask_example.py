
"""
Created on Thu Jan 16 09:34:58 2020

@author: drewc
"""

from flask import Flask, render_template, request, redirect

app = Flask(__name__)

setpoint_T = 37.0
setpoint_OD = 0.6
duty_cycle = 50
run = True

@app.route('/')
def main():
#    temp = 37
#    OD = 0.6
#    sparging = 50
    return render_template('index.html', setpoint_T = setpoint_T, setpoint_OD = setpoint_OD, duty_cycle = duty_cycle)

@app.route('/temp', methods = ['POST'])
def change_temp():
    global setpoint_T
    value = request.form['SP_T']
    setpoint_T = float(value)
#    print ("The new temp setpoint is: " , setpoint_T)
    return redirect('/')

@app.route('/OD', methods = ['POST'])
def change_OD():
    global setpoint_OD
    value = request.form['SP_OD']
    setpoint_OD = float(value)
#    print ("The new OD setpoint is: " , setpoint_OD)
    return redirect('/')

@app.route('/sparge', methods = ['POST'])
def change_sparge():
    global duty_cycle
    value = request.form['SP_sparge']
    duty_cycle = int(value)
#    print ("The new sparging percentage is: " , duty_cycle)
    return redirect('/')

@app.route('/finish', methods = ['POST'])
def end():
    return render_template('verify.html')

@app.route('/quit', methods = ['POST'])
def end_prog():
    global run

    response = request.form['answer']
    print (response)

    if response == 'yes':
        run = False
        return render_template('email.html')
    if response == 'no':
        return redirect('/')

@app.route('/email', methods = ['POST'])
def email_file():
    emailto = request.form['email']
    print (emailto)
    return render_template('goodbye.html')

if __name__ == '__main__':
#    app.run(host='192.168.0.114', port=5000)
    app.run()
