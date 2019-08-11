#!/usr/bin/python

#Author:        Albert Ribes
#Filename:      portscanner.py
#Version:       01.00
#Date:          09-06-2016

#TODO
#hyperthreading ports
#args: timeout, ports, ips
#DB ports


"""
This program makes a series of connectivity tests from local machine to clients listed in a file with the following rows:
        #Client AliasDNS OS IP Datos

The program works the following way:
        1.- The clients file is read and each valid line is placed in the `qin` queue
        2.- For each `qin` entry a thread is created
        3.- Each thread makes next connectivity tests for each client:
                a) DNS resolution
                b) ping
                c) port connectivity
        4.- Each thread places the clients test results in the `qout`queue
        5.- Each entry in `qout` is printed on the console
"""

import sys
import thread
import Queue
import time
import datetime
import subprocess
import socket
import os

path=os.path.dirname(os.path.realpath(__file__))

hostname=socket.gethostname()
initial_datetime=datetime.datetime.strftime(datetime.datetime.now(), '%d-%m-%Y_%H:%M:%S')

ports=[ "53","80", "443", "8080"]
qin = Queue.Queue(350)
qout = Queue.Queue(350)

thread_processing = []
def lineProcessing(line, tnum):
        value=line.split()
        thread_processing.append(str(tnum +1) + ' ')
        if value:
                        ip=value[3]
                        host=value[1]
                        os=value[2]
                        thread_processing[tnum]='#' + thread_processing[tnum] + host + ' ' + ip + ' ' + os + ' '
                        #DNSdirect
                        p = subprocess.Popen(["nslookup",host], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                        out, err = p.communicate()
                        status="no"
                        if out.find("** server can't find")!=-1:
                                        status="no"
                        elif ip in out:
                                        status="yes"
                        thread_processing[tnum]=thread_processing[tnum] + status + ' '

                        #DNSreverse
                        p = subprocess.Popen(["nslookup",ip], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                        out, err = p.communicate()
                        out=out.lower()
                        status="no"
                        if out.find("** server can't find")!=-1 or out.find("Non-authoritative answer")!=-1:
                                        status="no"
                        elif host.lower() in out:
                                        status="yes"
                        thread_processing[tnum]=thread_processing[tnum] + status + ' '
                        #IP
                        p = subprocess.Popen([path + "/timeout3","-t","3", "ping", ip], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                        out, err = p.communicate()
                        test_result="no"
                        if out.find("64 bytes from")!=-1:
                                        test_result="OK"
                        elif err.find("ping: unknown host")!=-1:
                                        test_result="unknown_host"
                        else:
                                        test_result="timeout"
                        thread_processing[tnum]=thread_processing[tnum] + '\n   - Ping ' + ip + ': ' + test_result

                        #PORTS
                        for port in ports:
                                        p = subprocess.Popen([path + "/timeout3","-t","3", "telnet", ip, port], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                                        out, err = p.communicate()
                                        if out.find("Escape character is")!=-1:
                                                        test_result="open"
                                        elif err.find("Connection refused")!=-1:
                                                        test_result="refused"
                                        else:
                                                        test_result="timeout"
                                        thread_processing[tnum]=thread_processing[tnum] + '\n   - Port ' + port + ': ' + test_result
                        if qout.full()==False:
                                qout.put(thread_processing[tnum])
                        else:
                                print("\n[ERROR]        Queue `qout` is too small!")
                                sys.exit()

#FILE OPENING AND CREATION
if len(sys.argv) > 1:
        finput=str(sys.argv[1])
else:
        print('Usage: ' + sys.argv[0] + ' [CLIENTS_FILE]')
        sys.exit()
print('\n[INFO] Initial datetime: ' + initial_datetime)
print('[INFO]   Starting connectivity test from host `' + hostname + '` to the list of servers defined by file `' + finput  +'`')
print ("[INFO]  Opening input file `"+ finput + "`..."),
sys.stdout.flush()
try:
        fclients=open(finput, 'r')
        print('[OK]')
except:
        print('\n[ERROR]        can NOT open file ' + finput)
        sys.exit()

#date=datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d_%H%M%S')
#outputfile='./ports_' + date
"""
print('[INFO]   Creating output file...'),
try:
        foutput=open(outputfile, 'w')
        print(' [`' + outputfile  + '`]')
except:
        print('\n[ERROR]        can NOT open file ' + outputfile)
        sys.exit()
"""
#FILE PROCESSING: line to qin
print('[INFO]   Reading input file and filling `qin` queue with valid data lines...'),
sys.stdout.flush()
for line in fclients:
        if not line.startswith("#") and line.strip() != '':
                if qin.full()==False:
                        qin.put(line)
                else:
                        print("\n[ERROR]        Queue `qin` is too small!")
                        sys.exit()
sys.stdout.flush()
print('[`qin` length: ' + str(qin.qsize()) + ']')
thread_num=0

#THREAD CREATION
try:
        print "[INFO]   Reading `qin` queue and creating threads to process each line...",
        sys.stdout.flush()
        while True:
                #print('   #qin: ' + str(qin.qsize()))
                if qin.empty()==False:
                        thread.start_new_thread( lineProcessing, (qin.get(),thread_num,))
                        thread_num+= 1
                        time.sleep(0.05)
                else:
                        break
        print('[opened of threads: ' + str(thread_num) + ']')
        print('[INFO]   Reading `qout` queue...\n')
        print('Execution time: ' + initial_datetime)
        print('***************************************************************************************************************')
        print('#thread hostname IP OS DNSdirect DNSreverse ping '),
        for port in ports:
                print (port + ' '),
        print('\n***************************************************************************************************************')
        while True:
                #print(qout.get())
                #print('<qout_size: ' + str(qout.qsize()) + ' #opened threads: ' + str(thread_num))
                if qout.empty()==False or thread_num>0:
                        print(qout.get())
                        thread_num-=1
                elif qout.empty()==True and thread_num==0:
                        break
                        fclients.close()
                        #foutput.close()
                        sys.exit()
                        break
        final_datetime=datetime.datetime.strftime(datetime.datetime.now(), '%d-%m-%Y_%H:%M:%S')
        print('***************************************************************************************************************')
        print('\n[INFO] Final datetime: ' + final_datetime + '\n')
except KeyboardInterrupt:
        fclients.close()
        #foutput.close()
        sys.exit()
