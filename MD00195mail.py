import RPi.GPIO as GPIO
import time
import smtplib
import smbus
import sys
from email.mime.text import MIMEText
from email.utils import formatdate

#GPIO setup------------------------------------------------------------------
GPIO.setmode(GPIO.BCM)
GPIO.setup(23,GPIO.OUT)
GPIO.setup(24,GPIO.IN)

#mail set---------------------------------------------------------------------
FROM_ADDRESS = 'mbk1953.lab@gmail.com'
MY_PASSWORD = 'rwaqospznmasngin'
TO_ADDRESS = 'md00195sen@m-b-k.co.jp'
BCC = 'mbk1953.lab@gmail.com'
SUBJECT = 'Error'
BODY = 'machine has stopped'

#message function-------------------------------------------------------------
def create_message(from_addr, to_addr, bcc_addrs, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_addr
    msg['Bcc'] = bcc_addrs
    msg['Date'] = formatdate()
    return msg

#send function---------------------------------------------------------------
def send(from_addr, to_addrs, msg): 
    smtpobj = smtplib.SMTP('smtp.gmail.com', 587)
    smtpobj.ehlo()
    smtpobj.starttls()
    smtpobj.ehlo()
    smtpobj.login(FROM_ADDRESS, MY_PASSWORD)
    smtpobj.sendmail(from_addr, to_addrs, msg.as_string())
    smtpobj.close()

#lux function----------------------------------------------------------------
def get_lux():
    bus = smbus.SMBus(1)
    addr = 0x23
    lux = bus.read_i2c_block_data(addr,0x10)
    return (lux[0]*256+lux[1])/1.2

#variable--------------------------------------------------------------------
val_gpio23 = 0
old_val_gpio24 = 0
val_gpio24 =0
state = 0
old_sate = 0
old_get_lux = 0

#main------------------------------------------------------------------------
try:
    while True:
        val_gpio24 = GPIO.input(24)
        old_state = state
        print(get_lux())

        if val_gpio24 == GPIO.HIGH and old_val_gpio24 == GPIO.LOW:
            state = 1- state
        else:
            pass

        old_val_gpio24 = val_gpio24

        if state == 1: 
            GPIO.output(23, GPIO.HIGH)
        else:
            GPIO.output(23, GPIO.LOW)

        val_gpio23 = GPIO.input(23)

        if get_lux() > 100 and old_get_lux < 100 and val_gpio23 == GPIO.HIGH:
             to_addr = TO_ADDRESS
             subject = SUBJECT
             body = BODY


             msg = create_message(FROM_ADDRESS, to_addr, BCC, subject, body)
             send(FROM_ADDRESS, to_addr, msg)
             print('email sent')
        else:
            pass

        old_get_lux = get_lux()

        time.sleep(1.0)

except KeyboardInterrupt:
    print ('exit')

GPIO.cleanup()


