#メール用のRaspberry Piからコピーで持ってきたもの　スペースやタブの関係がおかしくなっている可能性あり
#メールを送る際にはインストールするものがあり、使う場合には事前設定が必要
#送信元としてMBK-LABのGoogleアカウントを使っているので、遠隔ログインするための設定も必要

#必要モジュールのimport
import RPi.GPIO as GPIO
import time
import smtplib
import smbus
import sys
from email.mime.text import MIMEText
from email.utils import formatdate

#GPIO setup------------------------------------------------------------------
GPIO.setmode(GPIO.BCM)
GPIO.setup(23,GPIO.OUT)     #23番ピンを出力ピン
GPIO.setup(24,GPIO.IN)      #24番ピンを入力ピン

#mail set（アドレス等のメールを必要な情報）---------------------------------------------------------------------
FROM_ADDRESS = '差出しアドレス'
MY_PASSWORD = 'アプリパスワード'        #Googleアカウントを2段階認証にしている関係で、ここは専用のアプリパスワードを使用している
TO_ADDRESS = '宛先アドレス'
BCC = '差出しアドレス'
SUBJECT = 'Error'
BODY = 'machine has stopped'

#message function（メールを作成する関数）-------------------------------------------------------------
def create_message(from_addr, to_addr, bcc_addrs, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_addr
    msg['Bcc'] = bcc_addrs
    msg['Date'] = formatdate()
    return msg

#send function（メール送信関数）---------------------------------------------------------------
def send(from_addr, to_addrs, msg): 
    smtpobj = smtplib.SMTP('smtp.gmail.com', 587)
    smtpobj.ehlo()
    smtpobj.starttls()
    smtpobj.ehlo()
    smtpobj.login(FROM_ADDRESS, MY_PASSWORD)
    smtpobj.sendmail(from_addr, to_addrs, msg.as_string())
    smtpobj.close()

#lux function（光センサからの光量を読み込む関数）----------------------------------------------------------------
def get_lux():
    bus = smbus.SMBus(1)
    addr = 0x23
    lux = bus.read_i2c_block_data(addr,0x10)
    return (lux[0]*256+lux[1])/1.2

#variable（変数の準備）--------------------------------------------------------------------
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


