# -*- coding: utf-8 -*-
"""
Servidor TCP, que debe recibir mensajes de Modulos ESP8266 y de Dispositivos como PC´s, Teléfonos, ...
Un Módulo puede enviar mensajes por tener planficado el envío cada cierto tiempo, ya sea temperatura, interrupción porque 
algún sensor se ha activado, ... o como contestación a un mensaje recibido por el servidor.
Si tiene que enviar un mensaje este proceso comienza por AT+CIPSEND y termina con la contestación del servidor.
Si el servidor por planificación, o porque uno de los dispositivos le quiere enviar un mensaje a un determinado módulo, lo 
hace enviando directamente el mensaje formateado y terminando el mensaje con EOT, el módulo lo recibe con +IPD,nºcar:cars
que lo ejecuta y devuelve el resultado al servidor, el servidor reenvia el resultado al dispositivo.

Por lo que tenemos dos maneras desde el servidor de trabajar con un Modulo : 
1º recibimos un mensaje enviado mediante AT+CIPSEND, esto se recibe con : recv(), entonces se analiza y se toma la decisión
correspondiente, contestando siempre al módulo con el resultado, que será un mensaje terminado en EOT.
2º recibimos un mensaje desde un dispositivo cualquiera con destino a un determinado módulo. Esto se hace con colas,
cada modulo o dispositivo dispone de un thread por el que entran los datos desde dos fuentes por recv() o por cola.
En este caso la cola contiene un mensaje hacia el modulo donde estamos por estar en nuestro thread, este se envia al modulo
como un mensaje normal terminado en EOT, y esperamos el resultado, que se pondra en la cola del que ha pedido la información.

Entonces todo se concentra en un thread, hemos creado tantos threads como conexiones tenemos, todos los threads reciben
mensajes por dos fuentes, desde recv() o por la cola. Por recv() cuando es el propio dispositivo el que envia información al servidor
directamente y por su cola, porque otros dispositivo quiere enviar un mensaje a dicho dispositivo.
Un ejemplo normal sería el siguiente : un dispositivo quiere leer la temperatura de un determinado módulo
1º el dispositivo envia el mensaje de lectura de temperatura de un modulo existente, y se recibe con recv()
2º el servidor recibe el mensaje y despues de su analisis, pone el mensaje en la cola del modulo destino
3º el thread del modulo destino, lo saca de la cola y lo envia al modulo con sendv()
4º el modulo destino, envia el resultado, al servidor que lo recibe con recv()
5º el servidor despues del analisis, pone en la cola del dispositivo que ha enviado el mensaje, el resultado obtenido
6º el thread del dispositivo que queria la temperatura, recibe en su cola el resultado, y lo envia al dispositivo con sendv()

Con lo que un thread cualquiera siempre debe leer desde 2 fuentes conv recv() que es su modulo conectado, y desde su cola.
Para hacer esto debemos hacer recv() con timeout y la cola preguntando con MiCola.qsize() > 0, y esto continuamente en cada
thread arrancado, un thread arrancado, es porque un módulo o cualquier dispositivo se quiere conectar con nosotros que somos el servidor

Un Módulo ESP8266 SOLO conoce al servidor, pero cualquier otro cliente, sabe cuales son los Módulo conectados al sistema
pero solo los Módulo no conoce al resto de clientes que no sean Módulos ESP8266

Al principio cuando un dispositivo sea módulo o no se conecta, no sabemos que es, pero debemos crear su cola, y asignarla
a la dirección IP, que si que lo sabemos.


Se añade Thread de HouseKeeping : controla el uso de threads, libera memoria, etc...

12/05/2016
un evento nos lo comunica un modulo, de acuerdo a la tabla eventos que tiene origen, funcion origen, destino, funcion destino
por ejemplo un interrruptor se pulsa en origen, y dicho modulo origen envia un mensaje con dicho evento al servidor,
que envia un mensaje al modulo destino para que ejecute la funcion destino. El modulo origen y destino pueden ser el mismo
la tabla de eventos, se lee por el servidor y envia los eventos del modulo conectado para que este los ejecute adecuadamente
las alarmas tambien se utilizaran de la misma manera
al conectar un modulo, se enviaran todos los eventos y alarmas a los modulos
10/7/16
Cambio para crear 2 threads por dispositivo conectado, de forma que siempre estan parados excepto cuando reciben un mensaje
Uno de los threads está esperando un mensaje por su socket, y bloqueado, en cuando recibe el el mensaje lo envia a su segundo thread
reenviando el mensaje a su cola, y vuelve a quedarse bloqueado.
El thread que maneja la cola, siempre esta bloqueado, y cuando recibe un mensaje lo trata como se hacia, antes,
tambien envia mensaje a su dispositivo, el primer thread nunca envia mensajes, solo los recibe,
el thread de la cola, recibe un mensaje lo ejecuta y vuelve a bloquearse, en realidad es lo mismo que hacemos ahora, salvo que el thread actual, solo
atiende la cola, en la que esta bloqueado hasta que tiene que actuar y el trhead nuevo que es el del socket, que simplemente lo reenvia
a la cola, como no hay time out todos los thread estan bloqueados.
Podemos crear un nuevo thread que envia mensajes a las diferentes colas para saber si estan vivos los dispositivos.
Creo que sería más rápida la ejecución, con menor consumo de CPU. Aunque tengamos el doble de threads creados.
El proceso globalmente consume menos CPU, y no tiene delay, ya que en cuanto recibe el mensaje lo ejecuta, en la version anterior
al tener un timeout de 0,3sg, tenia que estar continuamente preguntando, por mensajes de socket y por mensaje en su cola. 
Consumiendo CPU continuamente, por todos los threads, cos que ahora, todos estan parados.
"""
"""
ent1 = Myconfig.Entorno()
DirLib=ent1.LibDir()
sys.path.insert(0, DirLib)
"""
import os, sys
if os.name == 'nt':
      try:
            os.chdir("h:/Dropbox")
            sys.path.insert(0, 'h:/Dropbox/Python35/Lib35')
            #sys.path.append('h:/Dropbox/Lib')
      except:
            sys.path.insert(0, 'd:/Dropbox/Python35/Lib35')
else:
      sys.path.insert(0, '/home/joaquin/Dropbox/Python35/Lib35')

import time
import datetime
import MyFunc16
import USBFunc16
import serial
import signal
import socket                    # get socket constructor and constants
from ChimoFunc16 import extrae2, extrae3, semana1, semana2, cambia, fechahora, timestamp, dif_tiempo, fechahoy, ahora, semana1, code_clave2
import random
import threading as HilosEjec
import select #module provides access to the select() and poll() functions available in most operating systems, epoll() available on Linux 2.5+
import sched #The sched module defines a class which implements a general purpose event scheduler
import multiprocessing
import queue
import Myconfig
import IoTFunc16
import logging
from socketIO_client import SocketIO, LoggingNamespace, BaseNamespace

global f1, timer1, threads, DicSentSql
global NumMenGen,  Mibloqueo, Permiso_Envio

SERVER_HOST = 'localhost'
ASCII_EOT = 0x04 #la contestación de un modulo termina con EOT
ASCII_CR = 0x0D #Control Return, = \r
ASCII_LF = 0x0A #Line Feed, esto es EOL=\n, usamos EOL como fin de linea
MODULO = 500
MODULOESP = 506
ANDROID = 501
TABLET=502
PCWINDOWS=513
PCLINUX=512
PCDUINO=510
RASPBERRY=511
IPHONE=505
LOOPBACK=50
MENSAJE_ERROR = 23
MODULOS_CONECTADOS = 500
THREAD_CODIGO = 501
CODIGOS_CLIENTE = 502
PONER_HORA_INTERNA = 80
QUIERES_ALGO = 21
ESTAS_VIVO = 22
EN_ESPERA = 24
REPETITIVO = 25
EVENTO_MODULO = 26
SEP1 = '|'
SEP2 = '#'
SALIR=20
class Thread(HilosEjec.Thread):
      def __init__(self, target, *args):
            HilosEjec.Thread.__init__(self, target=target, args=args)
            self.start()
            self.nombre = ""
      def Nombre(self, nombre):
            self.nombre = nombre
      def Join(self):
            self.join() #si otro thread, ejecuta esta función, queda bloqueado hasta que este thread termine.

class Semaforo(HilosEjec.Semaphore):
      def __init__(self, connections=5):
            #wait = HilosEjec._Semaphore.acquire
            self.__cond = HilosEjec.Condition(HilosEjec.Lock())		
            self.connections=connections
            self.contador = 0
      def Coger(self):
            self.__cond.acquire()		
            self.contador += 1
            #self.acquire() #decrementa el valor del semaforo, si es 0, bloquea hasta que algun thread, haga release
      def Soltar(self):
            self.__cond.release()		
            self.contador -= 1
            #self.release() #incrementa el valor del semaforo, permitiendo que algún thread se desbloquee
      def ValorContador(self):
            return self.contador


def IdentificaCliente(idclient, direc, numth):
      EsteCliente1={}
      cola_cliente = queue.Queue(0)
      EsteCliente1.setdefault("thread", numth)
      EsteCliente1.setdefault("tipo", "") #no se el tipo todavia
      EsteCliente1.setdefault("dirip", direc) #direccion ip
      EsteCliente1.setdefault("mensaje", 0) #mensaje que se ha enviado
      idclient.setdefault(numth, EsteCliente1) #tenemos identificado el cliente por su dirección IP
      del(EsteCliente1)
      return cola_cliente

def ConexionCliente(Puerto, Host, tab1, Puerto_Serie): 
      sockobj1 = socket(AF_INET, SOCK_STREAM)       # make a TCP socket object
      sockobj1.bind((Host, Puerto))               # bind it to server port number
      sockobj1.listen(5)  	
      connection, address = sockobj1.accept() 

def ConstruyeMensaje(tipomens, valoresd, origen = '0', destino = '1', separador = '|', fin_mensaje = ASCII_EOT):
      mens1 = origen + separador +  destino + separador + tipomens + separador
      for codid in sorted(valoresd.keys()):
            valor = valoresd.get(codid)
            mens1=mens1+valor+separador
      mens1 = ("%s%c" %(mens1, fin_mensaje)) #el modulo solo analizará un mensaje si termina en EOT, es la señal para analizar el mensaje, en caso contrario, pasará de él
      return mens1
      #y siempre que el destino, sea igual a su nº de identificación = destino, que será el segundo campo
      #el primer campo debe ser 0 si viene del servidor, que siempre se interpretará, o desde un origen que el modulo acepte que tenga permiso.

#thread de estas vivo, solo se dedica a verificar que los diferentes dispositivos estan vivos.
def EstasVivo(DicClientes, cola_logop, logger):
      TimeOutEsp = 720 #cada 12 min. enviamos un mensaje para verificar que el modulo esta vivo
      while 1:
            time.sleep(TimeOutEsp) #dormimos 12 minutos, y leemos los diferentes cliente del IdenCliente a los que enviamos Estavivo
            HoraAct=time.time()
            for ntrh in DicClientes.keys(): #enviamos mensaje de estas vivo a cada dispositivo conectado
                  HoraUltMens = DicClientes.get(ntrh).get("Hora_Mensaje")
                  MiCola = DicClientes.get(ntrh).get("cola")
                  MiTipo = DicClientes.get(ntrh).get("tipo") 
                  if  MiTipo != PCLINUX: #envia mensaje de estas vivo
                        Mens1="%c%c%d%c%d%c%c" % ('0', SEP1, ntrh, SEP1, ESTAS_VIVO, SEP1, ASCII_EOT)
                        DicClientes.get(ntrh).pop("mensaje")
                        DicClientes.get(ntrh).setdefault("mensaje", ESTAS_VIVO)	
                        DicClientes.get(ntrh).setdefault("env1", 1) #para verificar solo los que existian
                        MiCola.put(Mens1)
            time.sleep(TimeOutEsp/4) #dormimos 3 minutos, y vemos si esta vivo
            for ntrh in DicClientes.keys():   #cada uno de los dispositivos debe haber respondido si estas vivo   
                  MiCola = DicClientes.get(ntrh).get("cola")
                  MiTipo = DicClientes.get(ntrh).get("tipo") 
                  if MiTipo != PCLINUX:
                        if  (DicClientes.get(ntrh).get("mensaje") == ESTAS_VIVO) and DicClientes.get(ntrh).get("env1") == 1:
                              cola_logop.put("No devuelve el Mensaje de Esta Vivo : {}".format(ntrh)) 
                              msg1="No devuelve el Mensaje de Esta Vivo : {}".format(ntrh)
                              logger.info(msg1)
                              MiCola.put("SALIR|SALIR|%c"% (ASCII_EOT)) #para que termine ese thread
                              continue


#solo esta bloqueado esperando mensajes de su dispositivo conectado, y cuando recibe un mensaje lo envia a su cola            
def ConSocket(cola_logop, connection, address, MiThread, DicClientes, threads, logger):
      MiDireccion = address[0] 
      MiCola = DicClientes.get(MiThread).get("cola")
      while 1:
            try:
                  data = bytes.decode(connection.recv(1024)) #el thread queda parado hasta que venga un mensaje
            except:
                  msg1="data:{} ERROR thread : {} Hora : {}".format(data, MiThread, ahora())
                  logger.info(msg1)
                  ErrorModuloCaido = 1
                  break
            MiCola.put(data)
      MiCola.put("SALIR|SALIR|%c"% (ASCII_EOT)) #si hemos ido por except, mandamos mensaje de salir del thread de cola
      
#cuando el tipo de mensaje sea EVENTO, la dirección debe ser 0, el propio servidor.
#dicho mensaje se enviará a la cola_eventos, de forma que se reenviara mediante socket.io a todas la paginas html conectadas!!!
def ConCola(cola_logop, connection, numthread, DicClientes, ThreadAct, connbd, DicFunciones, logger, cola_eventos):
      global NumMenGen, Mibloqueo, Permiso_Envio, DicSentSql
      tab1 = MyFunc16.DicciDatos_My(connbd.get("bd"), connbd.get("usuario"), connbd.get("password"))  #necesitamos conexión con la BD en cada Thread
      upd1 = DicSentSql.get("upd1")
      upd2 = DicSentSql.get("upd2")
      if tab1.conn==None:
            cola_logop.put("No se ha podido conectar con la BD "+str(MiDireccion))		
            connection.close()
            return
      Permiso_Envio = 0
      MiThread = DicClientes.get(numthread).get("thread")
      NumMensaje = 0 # numero de mensaje de esta conexión, son solo válidos, será 0 mientras tipo = ""
      MiCola = DicClientes.get(MiThread).get("cola")
      ModuloPendienteRecepcion = 0
      PendienteOrigen = 0
      Mensaje_Enviado = 0 
      ErrorModuloCaido = 0
      data=None
      MiTipo = DicClientes.get(numthread).get("tipo") # no lo sabemos ahora, debe ser lo primero que debe decirnos.
      while 1:	
            data = MiCola.get()#bytes.decode(MiCola.get())
            if data != '' and data != None: #si el cliente no envia nada en 1 minuto, se desconecta	
                  nc, mensaje = extrae2(data)
                  if nc < 2 or mensaje[0] == 'None':
                        MiEnvio="Mensaje  No Valido|ERROR  : {}".format(data) 
                        logger.info(MiEnvio)
                        #print (MiEnvio)
                        connection.send(str.encode("%s|%c" %(MiEnvio, ASCII_EOT)))	
                        #break
                  elif NumMensaje == 0: #debemos saber que tipo de cliente es 
                        #antes de procesar mensajes debemos saber su tipo y nº de serie
                        #en mensaje tenemos la información
                        HoraConexion=time.time()
                        cola_logop.put("Cliente : "+data+" "+ahora()) 
                        nf2, res1 = MyFunc16.ResSel3(tab1, DicSentSql.get("sel2"), (mensaje[1], mensaje[0])) 
                        if nf2 == 1:
                              DicClientes.get(MiThread).pop("tipo") 
                              MiTipo = res1.get("grupos_cod_grupo")
                              DicClientes.get(MiThread).setdefault("tipo", int(res1.get("grupos_cod_grupo"))) # ya tenemos tipo
                              DicClientes.get(MiThread).setdefault("codigo", mensaje[1]) # ya tenemos codigo dispositivo
                              DicClientes.get(MiThread).setdefault("codigo_cli", res1.get("codigo_cli")) # ya tenemos el cliente al que pertenece el dispositivo
                              DicClientes.get(MiThread).setdefault("numserie", res1.get("numero_serie"))
                              DicClientes.get(MiThread).setdefault("server", res1.get("server"))
                              DicClientes.get(MiThread).setdefault("mensaje", 0)	
                              DicClientes.get(MiThread).setdefault("Hora_Mensaje", time.time())
                              #del nº de serie tenemos la descripcion, sensores y actuadores, privilegio, funciones, ...
                              NumMensaje+=1
                              if MiTipo == MODULOESP: 
                                    MiEnvio="|%d|OK|%c" % (MiThread, ASCII_EOT)
                              else:
                                    MiEnvio="%d|OK|%c" % (MiThread, ASCII_EOT)
                              MiEnvio ="{} {}  {}".format(MiEnvio, mensaje[1], mensaje[0])
                              #print(MiEnvio)
                              logger.info(MiEnvio)
                              cola_logop.put(MiEnvio);
                              connection.send(str.encode(MiEnvio))
                        else:
                              MiEnvio="Codigo No Valido|ERROR"
                              #print (MiEnvio)
                              connection.send(str.encode("%s|%c" %(MiEnvio, ASCII_EOT)))
                              break
                  elif NumMensaje == 1: 
                        #situación en la que hemos recibido un mensaje con el nº de serie como digest de sha256, + su numero de mensaje,
                        #con estos datos calculamos el sha256 que debe coincidir con el recibido
                        #el campo 0 del mensaje es el digest de numero de serie + numero aleatorio y campo 1 el numero aleatorio
                        num_random = mensaje[1]
                        digest_calculado = code_clave2(DicClientes.get(MiThread).get("numserie"), num_random)
                        if digest_calculado != mensaje[0]:
                              MiEnvio="Numero de Serie No Valido|ERROR"
                              MiEnv2=MiEnvio+" NumRandom:"+num_random+" Digest:"+mensaje[0]+" Calculado:"+digest_calculado
                              #print (MiEnv2)
                              logger.info(MiEnv2)
                              cola_logop.put(MiEnv2)
                              connection.send(str.encode("%s|%c" %(MiEnvio, ASCII_EOT)))
                              break		
                        else:
                              MiEnvio="OK|OK|%c" % (ASCII_EOT)	
                              NumMensaje+=1
                              Timeout1 = int(res1.get("timeout")) #cada dispositivo puede tener un timeout diferente
                              MiEnvio1 = "Conectado!!! , Thread : {}  Num. Serie : {} N.Random : {}  TimeOut: {}".format(MiThread, DicClientes.get(MiThread).get("numserie"), num_random, Timeout1)
                              #print (MiEnvio1)			
                              logger.info(MiEnvio1)
                              cola_logop.put(MiEnvio1)
                              #actualizamos la fila del dispositivo para asignar el thread 
                              MyFunc16.UpdateFilaBD(tab1, upd1, (MiThread, DicClientes.get(MiThread).get("dirip"), DicClientes.get(MiThread).get("codigo"), DicClientes.get(MiThread).get("tipo")))
                              connection.send(str.encode(MiEnvio))	
                              if DicClientes.get(MiThread).get("tipo") != MODULOESP:
                                    Permiso_Envio = 1
                              if(DicClientes.get(MiThread).get("tipo") == MODULO): #para modulos con WINC1500
                                    PonerHora(MiCola, '0', str(MiThread))
                              #añadir aqui enviandolo por la cola los eventos y alarmas correspondientes a este modulo
                              #select * from eventos where mod_origen = DicClientes.get(MiThread).get("codigo")
                  else:
                        #analisis de mensaje, para ejecutarlo, guardarlo en la BD o reenviarlo a otra cola
                        if mensaje[0] == "SALIR":
                              msg = "Recibido Mensaje de Salir, Thread : {}".format(MiThread)
                              #print (msg)
                              logger.info(msg)
                              cola_logop.put(msg)
                              break
                        else:
                              #logger.info(str(mensaje))
                              #aqui debo verificar que la conexion con la BD sigue viva                          
                              ParMens={}
                              ParMens.setdefault("origen", int(mensaje[0]))
                              ParMens.setdefault("destino", int(mensaje[1]))
                              ParMens.setdefault("funcion", int(mensaje[2]))
                              Mibloqueo.Coger() #bloquea hasta soltar cualquier otro thread
                              NumMenGen+=1	
                              ret1 = AnalisisMensaje(DicClientes, MiThread, mensaje, ParMens, data, tab1, NumMenGen, DicFunciones, logger, cola_eventos)
                              Mibloqueo.Soltar()
                              HoraConexion=time.time()
                              NumMensaje+=1
                              if ret1!="Procesando":
                                    Mensaje_Enviado = 1 #para verificar que una vez enviado se recibe respuesta
                                    HoraConEsp = time.time() #para no enviar el mensaje de ESTAS_VIVO
                                    connection.send(str.encode(ret1))
                                    cola_logop.put(ret1)	
      connection.close()	
      if (DicClientes.get(MiThread) != None):
            MyFunc16.UpdateFilaBD(tab1, upd2, ('0', DicClientes.get(MiThread).get("dirip"), DicClientes.get(MiThread).get("codigo"), DicClientes.get(MiThread).get("tipo"), str(MiThread)))
      del(MiCola)
      ThreadAct.pop(DicClientes.get(MiThread).get("thread"))
      DicClientes.pop(MiThread) #elimina la entrada del diccionario	
      termina1="Thread : %d Terminado %s" % (MiThread, ahora())
      logger.info(termina1)
      #print (termina1)
      cola_logop.put(termina1)
      tab1.Salir()

#en ParMens tenemos origen, destino y tipo de mensaje
def AnalisisMensaje(DCliente, Thread, Mensaje, ParMens, data, tab1, nmens, DicFunciones, logger, cola_eventos):
      global Permiso_Envio, DicSentSql
      #logger.info("Analisis Mensaje:"+str(Mensaje)+str(ParMens))
      DCliente.get(Thread).pop("Hora_Mensaje")
      DCliente.get(Thread).setdefault("Hora_Mensaje", time.time())
      if ParMens.get("destino") == 0:#DirServidor: #aqui vienen todas la funciones que se ejecutan en el propio servidor
            try:
                  result = getattr(IoTFunc16, DicFunciones.get(ParMens.get("funcion")))(DCliente, Thread, Mensaje, tab1, nmens, DicSentSql, logger, cola_eventos)
                  #ejecuta la funcion que venga en el diccionario, llenado desde la base de datos
                  #lo que se cambia en los parametros mutables (DCliente) en la funcion, se queda cambiado cuando sale de la funcion
                  #print (DCliente.get(Thread).get("mensaje"))
                  return result
            except:
                  logger.info("ERROR, Funcion No existe"+str(Mensaje)) 
                  return "ERROR, Funcion No existe%c%c" % (SEP1, ASCII_EOT)
      elif ParMens.get("destino") == Thread: #destino es igual a MiThread, luego es otro cliente que me quiere enviar un mensaje
            #print("Mensaje para mi Thread %d : %s" % (Thread, data))
            return data #el modulo cuando devuelve el resultado, debe darle la vuelta, el destino es el origen y al reves
      else: #el destino es otro modulo y debemos reenviarlo, el destino es el nº de trhead
            try: #por si el thread de dicho modulo ha terminado
                  cola_dest = DCliente.get(ParMens.get("destino")).get("cola")
                  cola_dest.put(data)
                  return "Procesando"
            except:
                  #el mensaje debe destinarse al origen desde el servidor como un Error. porque el thread del modulo ya no existe
                  funcion = LOOPBACK
                  parametros = "ERROR|Modulo|No Existe|" #se devuelve al origen el error
                  mens1 = "%d%c%d%c%d%c%s%d%c%c" % (0, SEP1, ParMens.get("origen"), SEP1, funcion, SEP1, parametros, nmens, SEP1, ASCII_EOT) 
                  return mens1



def PonerHora(cola, origen, destino):
      s1=semana1()
      f2=timestamp(0) #devuelve ya una lista con los valores y redondeando los segundos si el microsegundo es mayor de 500000
      VarMensaje={}
      VarMensaje.setdefault(1,str(f2[5]))#segundo
      VarMensaje.setdefault(2,str(f2[4]))#minuto
      VarMensaje.setdefault(3,str(f2[3]))#hora
      VarMensaje.setdefault(4,s1[3]) #dia de la semana
      VarMensaje.setdefault(5,str(f2[2]))#dia del mes
      VarMensaje.setdefault(6,str(f2[1])) #mes
      VarMensaje.setdefault(7,str(f2[0]-2000)) #año
      mens1=ConstruyeMensaje(str(PONER_HORA_INTERNA), VarMensaje, origen, destino)
      cola.put(mens1)
      return 0

#esperamos en una cola, mensajes de eventos como la pulsación de un switch, o cualquier evento de entrada de datos
#se envia a berentecio, para que lo presente en las paginas html, que este conectadas en ese momento
def MsgEventos(cola, cola_log, logger):
      socketIO = SocketIO('localhost', 10824)#, Namespace)
      sid=socketIO._engineIO_session[0]
      logger.info("SID de la Conexion con Berentecio"+sid)
      socketIO.emit('msgcon', {'data': 'Estoy Conectado ServerIoT!'}, path="/serveriot")
      while 1: 
            fila = cola.get() #estamos bloqueados esperando un evento
            #mensaje = "Mensaje srviot! : {}-{}".format(i1, ChimoFunc16.timestamp(1))
            socketIO.emit('srviot', {'data': fila}, path="/serveriot")
            cola_log.put("Evento : "+fila)
#para tener el log en la BD, es más lento, pero nos permite insertar en cualquier tabla de SQLIte o MySQL
def InsertarLogop(cola, connbd, cola_signal):
      tab1 = MyFunc16.DicciDatos_My(connbd.get("bd"), connbd.get("usuario"), connbd.get("password"))
      selx="select desc_grupo from grupos where cod_grupo = 1"
      if tab1.conn == None:
            print("Error de Conexión a Base de Datos, debe estar activa antes de ejecutar el Servidor Socket")
            exit()
      while 1: 
            fila = cola.get() # se queda bloqueado hasta que haya algo en la cola
            fila = cambia(fila, '"', '')
            #print (fila)
            #algunos mensajes repetitivos no hace falta enviarlos al log, como la funcion ESTAS_VIVO
            nc1, campos = extrae2(fila)
            if nc1 > 2:
                  if campos[2] == str(ESTAS_VIVO):
                        nf, dfila = tab1.ResSel(selx) #para no perder la conexion
                        continue
            tab1.Logop(fila) #escribe en la BD, lo recibido de la cola, que es lo recibido del thread
            if fila.find("SERVIDOR|") != -1:
                  break
      tab1.Salir()
#verifica el buen funcionamiento, libera memoria.	
#debemos enviar un mensaje cualquiera a los modulos supuestamente conectados
#y si no responden enviar un mensaje a la cola del correspondiente thread para que termine
def HouseKeeper(tab1, cola_log, cola_sign, DicCli):
      cola_logop.put("HouseKeeper, arranca")
      while 1:
            for th1 in DicCli.keys():
                  #enviamos mensaje a cada uno, y si no responde enviar a su cola un mensaje de salir
                  mens1 = "0%c%d%c%d%c%s%d%c%c" % (SEP1, destino, SEP1, LOOPBACK, SEP1, parametros, nmens, SEP1, ASCII_EOT)
                  cola_dest = DCliente.get(destino).get("cola")
                  mens1 = "SALIR%cSALIR%c%c" % (SEP1, SEP1, ASCII_EOT)
                  cola_dest.put(mens1)
            time.sleep(60)

def Salir_Ordenado(cola_logop, bd1, threads):
      cola_logop.put("SERVIDOR|%s" % (ahora()))
      time.sleep(1)

#Usamos el módulo Myconfig para centralizar la configuración de los programas, de forma que no haya que poner constantes en los programas
#y solo tengamos que modificar en Myconfig para todos los programas
misclv = Myconfig.claves()
if os.name == 'nt':
      fichlog='d:\Tmp\ServerIoT.log'
      connbd=misclv.user_w8()
else:
      fichlog='/media/joaquin/Home2/Tmp/ServerIoT.log'
connbd=misclv.user_linux()
logging.basicConfig(filename=fichlog, 
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%d-%m %H:%M', level=logging.DEBUG)	
logger = logging.getLogger(__name__)
myHost = ''                            # '' = all available interfaces on host
myPort = misclv.puerto_disp()#10821                      # listen on a non-reserved port number
direc=""
bd1=connbd.get("bd")#"placas_samd21" #/home/joaquin/Sybase/Data.db"
sockobj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)       # make a TCP socket object
sockobj.bind((myHost, myPort))               # bind it to server port number
sockobj.listen(15)                            # listen, allow 15 pending connects
fecha1=timestamp(1)
fecha3=fechahoy()
cola_logop = queue.Queue(0)
tab1= MyFunc16.DicciDatos_My(bd1, connbd.get("usuario"), connbd.get("password"))
if tab1.conn == None:
      print ("No se ha podido conectar con la BD")
      exit()
DicSentSql = {}
DicFunciones = {}
sent1 = tab1.ConsSelect("sqls", 0) 
nf0, campos = extrae3(sent1, "select", "from", ",")
nf2, res1 = MyFunc16.ResSel3(tab1, sent1, None, 1) 
for i1 in range(nf2):
      DicSentSql.setdefault(res1.get(str(i1)).get(campos[0]), res1.get(str(i1)).get(campos[2]))
nf0, campos = extrae3(DicSentSql.get("sel10"), "select", "from", ",")
nf2, res1 = MyFunc16.ResSel3(tab1, DicSentSql.get("sel10"), None, 1) 
for i1 in range(nf2):
      #logger.info(str(res1.get(str(i1)).get(campos[0]))+res1.get(str(i1)).get(campos[1]))
      DicFunciones.setdefault(res1.get(str(i1)).get(campos[0]), res1.get(str(i1)).get(campos[1]))     #tenemos codigo y funcion a ejecutar 
cola_signal = queue.Queue(0) #cola de recepción de señales, por ejemplo para salir del Servidor, de forma ordenada.
cola_eventos = queue.Queue(0)
thread1=Thread(InsertarLogop, cola_logop, connbd, cola_signal)
threadmsg = Thread(MsgEventos, cola_eventos, cola_logop, logger)
threads={}
i1=1
NumMenGen=0
DirServidor = 0
Mibloqueo=Semaforo()#thread.allocate_lock()
IdentCliente={} #identificacion de cada cliente por su dirección IP y su Thread y su tipo (cliente python, telefono, modulo, ...)
thread2=Thread(EstasVivo, IdentCliente, cola_logop, logger)
msg="Init:Servidor_ESP8266, Sistema Operativo : "+ sys.platform+", Version de Python : "+sys.version
logger.info(msg)
cola_logop.put(msg)
msg="Dir. IP : "+socket.gethostbyname(socket.gethostname())+" Nombre : "+socket.gethostname()
logger.info(msg)
cola_logop.put(msg)
AtiendeConn=0
upd0 = DicSentSql.get("upd0")
#upd0="update dispositivo set thread = 0"
MyFunc16.UpdateFilaBD(tab1, upd0)
tab1.Salir()
while True:
      msg="Esperando Conexion "+ahora()
      logger.info(msg)
      #print (msg)
      cola_logop.put(msg)
      connection, address = sockobj.accept()   # esperamos bloqueados, hasta una nueva conexión
      if cola_signal.qsize() > 0: #si alguno de los threads, envia un comando, para salir del servidor, se llama a Salir_Ordenado()
            Salir_Ordenado(cola_logop, bd1, threads)
            break
      msg1='Servidor conectado por : {}   {}'.format(address[0], ahora())
      logger.info(msg1)
      #print (msg1)
      #arrancamos el thread de la conexión que acaba de conectarse, y en dicho thread, se hace la recepción de datos
      #tenemos identificado al thread con la dirección, si ya existiese por haberse conectado antes, se actualiza el numero de thread
      #i1 identifica el thread que maneja el socket y i1+1 el que maneja la cola
      cola_cliente = IdentificaCliente(IdentCliente, address[0], i1)
      IdentCliente.get(i1).setdefault("cola", cola_cliente)
      IdentCliente.get(i1).setdefault("cola_eventos", cola_eventos)
      thread0 = Thread(ConSocket, cola_logop, connection, address, i1, IdentCliente, threads, logger)
      thread1=Thread(ConCola, cola_logop, connection, i1, IdentCliente, threads, connbd, DicFunciones, logger, cola_eventos)
      thread1.name="Thread-"+str(i1) #le damos nombre al thread, para su identificación
      thread1.Nombre("Thread-"+str(i1))
      cola_logop.put('Servidor conectado por : '+address[0]+ " "+thread1.name)    # escribimos la información del cliente conectado
      logger.info(thread1.name)
      threads.setdefault(i1, thread1) #para tener controlados los nombre de todos los threads arrancados.
      i1+=1


