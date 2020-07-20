"""Simple test for using adafruit_motorkit with a DC motor"""
import time
from adafruit_motorkit import MotorKit

kit = MotorKit()

kit.motor4.throttle = 1.0
time.sleep(5)
kit.motor4.throttle = 0
