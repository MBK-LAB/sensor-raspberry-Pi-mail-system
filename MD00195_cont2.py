# 選別機のエラーを赤ランプ認識をさせて、感知するシステム
# 感知方法としては、画像から赤色マスクを行い、赤だけを抽出 し、輪郭を描写させる。
# そののち、輪郭面積もしくは外接矩形面積で赤色を選別し、赤ランプのみを認識させる
# 赤ランプの輪郭面積、外接矩形中心がなし➔ありに変化した時に、機械が止まったと連絡させる
# 
#import 物体追跡用
import time
import picamera
import cv2
import numpy as np
import io

#import pylab as plt

#import　メール送信用
import smtplib
import smbus
import sys
from email.mime.text import MIMEText
from email.utils import formatdate


#mail set（アドレス等のメールを必要な情報）
FROM_ADDRESS = 'mbk1953.lab@gmail.com'
MY_PASSWORD = 'rwaqospznmasngin'
TO_ADDRESS = 'tu-i-so.agaritakatta@ezweb.ne.jp'
BCC = 'mbk1953.lab@gmail.com'
SUBJECT = '選別機停止'
BODY = '選別機が停止しました'

er=0
old_er = 0
size = (800,800)
#最初期窓サイズ（動画サイズと同じだと楽）
x = 0
y = 0
w = 800
h = 800
track_window = (x, y, w, h)

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


# 撮影した動画から色マスクで輪郭を検出する
# min_areaより小さい面積の輪郭は排除
# 残った輪郭に対して外接矩形を作り、戻り値とする
def create_gaisetu(frame, track_window):
    x, y, w, h  = track_window
    #検出窓での区切り
    roi = frame[y:y+h, x:x+w]
    #窓内をBGR➔HSVに変換
    hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    #検出する色（赤）の設定（HSV表記にて最小最大を設定する）(初期値　150,64,0　　　179,255,255）
    hsv_min = np.array([159,130,130])
    hsv_max = np.array([179,254,254])
    #設定した条件にてマスクを作る
    mask = cv2.inRange(hsv_roi,hsv_min, hsv_max)
    #輪郭を検出する
    _, contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    #面積による輪郭の選定(認識する最小サイズの設定)
    min_area = 20
    large_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
    #外接矩形の作成及び4点情報（左下の頂点の座標(x, y)、横の長さw、縦の長さh) の取得
    for cnt in contours:
        area = cv2.contourArea(cnt)
    rect = []
    for contour in large_contours:
        rect = cv2.boundingRect(contour)
        x, y, w, h = rect
    #外接矩形の描写
    drow_contour = cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 0), 2)
    cv2.imshow("mask", mask)
    #外接矩形の四点座標（rect）、描写(drow_contour)を戻り値とする
    return(rect, drow_contour)


# CamShiftを行う為の下準備
# 外接矩形内のヒストグラムの算出、正規化、及び精度設定行う    
def histogram(frame, rect):
    #引数として受け取った外接矩形の4点情報から検出窓の作成
    x, y, w, h = rect
    #x, y, w, h = rect[0], rect[1], rect[2], rect[3]
    track_window = (x,y,w,h)
    #検出窓で画像を区切る
    roi = frame[y:y+h, x:x+w]
    #窓内をHSVに変換
    hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    #色によるマスクを行う(初期値　150,64,0　　　179,255,255）
    hsv_min = np.array([159,130,130])
    hsv_max = np.array([179,254,254])
    mask = cv2.inRange(hsv_roi, hsv_min, hsv_max)
    #窓内のヒストグラムの算出
    roi_hist = cv2.calcHist([hsv_roi], [0], mask, [180], [0,180])
    #ヒストグラムの正規化
    cv2.normalize(roi_hist, roi_hist, 0, 255, cv2.NORM_MINMAX)
    #アルゴリズムの繰り返し設定　回数と精度を背彫っていする
    term_crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 1)
    #戻り値として、検出窓、正規化したヒストグラム、アルゴリズムの繰り返し設定を戻す
    return track_window, roi_hist, term_crit


# CamShiftで物体を追跡する関数    
def tracking_movie(frame, track_window, roi_hist, term_crit):
    #動画全体をHSV変換
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    #ヒストグラムの逆投影
    dst = cv2.calcBackProject([hsv],[0],roi_hist,[0,180],1)
    #CamShift で物体追跡させる
    ret, track_window = cv2.CamShift(dst, track_window, term_crit)
    #CamShiftで作った検出窓の座標を入手
    pts = cv2.boxPoints(ret)
    pts = np.int0(pts)
    s_2 = track_window[2] * track_window[3]
    #ptsの4座標から中心座標を算出
    center = pts[0]+pts[1]+pts[2]+pts[3]
    center = np.int0(center/4)
    #print("中心", center)
    #print("x座標:",center[0])
    #print("y座標:",center[1])
    
    #求めた中心座標を中心とする円を描写
    img2 = cv2.circle(frame, (center[0],center[1]),5, (255, 255, 255), thickness=1)
    #追跡するべき色を囲った四角形の描写(ptsの４座標を頂点とする四角形の描写）
    img2 = cv2.polylines(frame, [pts], True, 255, 2)
    #描写した動画の表示
    #cv2.imshow('IMAGE', img2)
    #追跡窓の中心座標を戻す
    return(center,img2)


#Picameraの準備
with picamera.PiCamera() as camera:
    #解像度、フレームレートの設定
    camera.resolution = (800, 800)
    camera.framerate = 30
    stream = io.BytesIO()

    while True:
        #撮影➔OpenCVで編集可能な状態へ？
        camera.capture(stream, format="jpeg", use_video_port=True)
        frame = np.frombuffer(stream.getvalue(), dtype=np.uint8)
        stream.seek(0)
        #cv2.imshow('1',frame)    #この時点だと画像が表示されない
        frame = cv2.imdecode(frame, 1)
        cv2.imshow('2',frame)     #カメラに写る画像のみ
        
        alpha = 1.0 # コントラスト項目
        beta = 0    # 明るさ項目

        # 明るさ・コントラスト操作
        frame = cv2.convertScaleAbs(frame,alpha = alpha,beta = beta)

        # 画像表示
        capt = 'New Image alpha=%.1f beta=%.1f' % (alpha,beta )
        cv2.imshow(capt, frame)
        
        #外接矩形作成関数の呼び出し
        rect, drow_contour = create_gaisetu(frame, track_window)
        cv2.imshow('gaisetu', drow_contour)    #外接矩形を描写した動画の表示
        # rect == [] つまり外接矩形が作成できなかった時は、全て処理を飛ばして最初に戻す
        if rect == []:
            print(rect)
            rect = (0,0,1,1)
            #メール送信する時の判定変数に数字代入（赤がない時が0に対応）
            er = 0
            old_er = 0
            #continue
            
        #ヒストグラム用の関数の呼び出し    
        track_window, roi_hist, term_crit = histogram(frame, rect)
        
        """#動画からフレーム取り出す
        camera.capture(stream, format="jpeg", use_video_port=True)
        frame = np.frombuffer(stream.getvalue(), dtype=np.uint8)
        stream.seek(0)
        frame = cv2.imdecode(frame, 1)
        #cv2.imshow('3',frame)"""
        
    #本来はCamShiftが検出窓を更新するため、検出窓のサイズを初期化する必要はない
    #何らかの理由でトラッキングがはずれた時に輪郭面積による選別を行いたいため、検出後に窓サイズの初期化、及び輪郭検出から繰り返すようにしている
    #この条件の場合CamShiftである必要がないと思われるが、他パターンの動作比較も含めてCamShiftを使用している
        #物体追跡用の関数の呼び出し
        center, s_2 = tracking_movie(frame,track_window, roi_hist, term_crit)
        cv2.imshow('SHOW MEANSHIFT IMAGE', s_2)
        #検出窓を初期サイズに戻す
        track_window = x, y, w, h
        
        #外接矩形の中心座標が存在する時が赤が存在すると判定
        if center[0] >0 and center[1]>0:
            er = 1
        #er = 1 の時、現在赤が存在している。old_er = 0の時、赤を連続で感知しているわけではない。よって、赤ランプが点いた時と判定する。
        if er == 1 and old_er==0:
            print("エラー")
            to_addr = TO_ADDRESS
            subject = SUBJECT
            body = BODY

            msg = create_message(FROM_ADDRESS, to_addr, BCC, subject, body)
            send(FROM_ADDRESS, to_addr, msg)
            print('email sent')
            #赤ランプを判定したので、old_erを更新する。
            old_er = 1
        
        k = cv2.waitKey(1)
        if k == ord('q'):
            break
    
        

            
            

#全ての表示ウィンドウを削除

#board.exit()
