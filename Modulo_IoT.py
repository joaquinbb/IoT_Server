# -*- coding: utf-8 -*-

"""
Este programa debe valer para todos los modulos de tipo : PcDuino, Raspberry, Raspberry con SenseHat, RaspberryZero, RaspberryZero con Unicorn y BeagleBoneGreen Wireless
para tener el numero de serie del pcduino
$ sudo insmod cpu_id.ko
$ cat /proc/cpu_id
VER:C
ID:165166c380485370515248480301dc8b
Se ha ejecutado y se tiene un fichero con todos los numeros de serie, se llama : CpuId.txt, esta en mismo directorio
la linea con separador |, tiene el nombre del PcDuino y el nº de serie

cambiar timezone en Ubuntu : sudo dpkg-reconfigure tzdata
debemos pasar desde ControlGen.py el codigo y el numero de serie del modulo
ControlGen.py y Modulo_IoT.py sirver para los modulos de tipo : PcDuino, Raspberry y BeagleBone. y Con cualquier tipo de Hat o Cape.
El formato del mensaje siempre lleva origen, destino, tipo, num_mensaje y los diferentes valores a la hora de enviar al servidor
"""
import os, sys
import socket
import time
import random
from hashlib import sha256
import ChimoFunc16
import IoTModulos16
try:
	from sense_hat import SenseHat #para Raspberry con placa sensehat
except:
	SenseHat = None
try:
	import pigpio #para Raspberry, libreria de control de entrada salida, incluye : Pines, PWM, serial, I2C y SPI
except:
	pigpio = None
	
MODULO = 500
ANDROID = 501
TABLET=502
PCWINDOWS=503
PCLINUX=504
IPHONE=505
ASCII_EOT = 0x04 #la contestación de un modulo termina con EOT
SET_THREAD = 20
QUIERES_ALGO = 21
ESTAS_VIVO = 22
ENVIADO_OK = 23
EN_ESPERA = 24
MODULO_PCDUINO = 510
MODULO_RASPBERRY = 511
MOULO_BEAGLEBONE = 514
CONTESTACION_MODULO = 25
SEP1 = '|'
LOOPBACK=50
SALIR=20
ALARMA = 30
LEER_HORA=81
LEER_NUM_SERIE=29
BLINK_LED=60
NUM_PLACAS = 5
#-----------------------------------------------------------------------------------------------------

def DesgloseMensaje(mensaje):
	#el primer campo es el origen, el segundo el destino, el tercero el tipo de mensaje, y despues pueden venir hasta 10
	#campos de 10 caracteres cada uno, todos separados por |
	camposd = {}
	nc, campos = ChimoFunc16.extrae2(mensaje) #por defecto ya los separa por |
	if nc<3:
		origen=None
		destino=None
		tipo=None
		camposd={}
	else:
		origen = campos[0]
		destino = campos[1]
		tipo = int(campos[2])
		for i1 in range(nc-3):
			camposd.setdefault(i1, campos[i1+3])
	return origen, destino, tipo, camposd

def EnviaMensaje(puerto,  mensaje, retardo=0.02, eot = 'S', tiempo_maximo_espera = 10): #eot cambio para esperar hasta recibir EOT
	resp=None
	#para que funcione en Python 3.4, mensaje debe codificarse con encode. Muy Importante, a la placa le llega lo mismo, hacer decode cuando se lee de la placa
	barr2=mensaje.encode('ascii')#unicode(mensaje)
	puerto.write(barr2)
	puerto.flush() #espera hasta haber escrito
	puerto.flushInput() #limpia el buffer de entrada
	#puerto.flushOutput() #limpia el buffer de salida, que se supone ya est�ac�por flush()
	time.sleep(retardo)
	if eot != 'S' :
		carac=puerto.inWaiting()
		if carac > 0:
			resp1 =puerto.read(carac) #leemos carac caracteres
			resp = resp1.decode('ascii')
			return resp
		else:
			return None
	else:
		Respuesta = ""
		resp = ""
		tiempo_respuesta = 0
		while resp != ASCII_EOT and tiempo_respuesta < tiempo_maximo_espera: #por defecto 10 sg.
			c1=puerto.inWaiting() #devuelve el numero de bytes pendientes de leer
			if c1 > 0:
				resp1 = puerto.read(c1)
				resp = resp1.decode('ascii') #se codifica cuando se envia y se decodifica cuando se recibe, la placa no tiene que hacer nada. En Python 3.4 se manejan bytes
				#que es mucho mas correcto, se codifica en lo que queramos en mi caso siempre son bytes de tipo ascii, podria ser tambien latin-1, 
				#un caracter = a 1 byte, es la unica restriccion
				if resp[len(resp)-1] != ASCII_EOT: # no hemos recibido EOT
					Respuesta += resp
					print (resp)
				else:
					Respuesta += resp[:len(resp)-1]
					break
			tiempo_respuesta+=1
			time.sleep(retardo)
		if tiempo_respuesta >=tiempo_maximo_espera:
			return None #no hemos recibido EOT, pero hemos superado el tiempo de espera
		return Respuesta

def ConstruyeMensaje(sock, tipomens, valoresd, origen = '0', destino = '1',  salida='N', separador = '|', fin_mensaje = ASCII_EOT):
	mens1 = "%s%c%s%c%s%c" % (origen, separador, destino, separador, str(tipomens), separador) 
	print(valoresd)
	for codid in sorted(valoresd.keys()):
		if isinstance(codid, str):
			continue
		valor = valoresd.get(codid)
		if valor != fin_mensaje and valor != None:
			mens1+=valor+separador
	mens1 = "%s%c" % (mens1, fin_mensaje)
	if sys.version_info.major == 2:
		MensEnviadob = bytes(mens1)#, 'utf8')
	else:
		MensEnviadob = bytes(mens1, 'utf8')
	sockobj.send(MensEnviadob)
	print ("Enviado : ", mens1)
	#respuesta = EnviaMensaje(sock, mens1)
	if salida == 'S':# or respuesta != None:
		print (mens1, "->Respuesta : ", respuesta)
	return mens1


def EjecutaMensaje(MensRecibido):
	origen, destino, tipo, campos = DesgloseMensaje(MensRecibido)
	#ahora dependiendo del tipo hacemos algo diferente
	if tipo == EN_ESPERA:
		#nos piden que esperemos hacemos sleep unos segundos, que es nuestra ejecución y volvemos
		time.sleep(3)
	return 1
def obtener_thread(sockobj, tipo, nserie):
	linea="%s|%s|%c" % (tipo, nserie, ASCII_EOT)
	if sys.version_info.major == 2:
		lineab = bytes(linea)#, 'utf8')
	else:
		lineab = bytes(linea, 'utf8')
	sockobj.send(lineab)
	try:
		mensaje = bytes.decode(sockobj.recv(1024))
	except:
		return -1
	print (mensaje)
	nc, mensaje1 = ChimoFunc16.extrae2(mensaje)
	if nc <3: #recibimos OK|nºthread|EOT
		return "Error"
	else:
		return mensaje1[0]


def Loopback(Port1, cuantos):
	VarMensaje = {}
	VarMensaje.setdefault(1, "ABCDE") #numero lampara
	VarMensaje.setdefault(2, "12345") # encender 1, apagar 0
	VarMensaje.setdefault(3, "FGHIJ") # porcentaje de encendido
	for i in range(cuantos):
		resp1=ConstruyeMensaje(str(LOOPBACK), VarMensaje, Port1)
		print (resp1)

def EnviaMensaje(sockobj, MensEnviado):
	MensEnviadob = bytes(MensEnviado)#, 'utf8')
	sockobj.send(MensEnviadob)
	#print ("Enviado : ", MensEnviado)
	MensRecibido = bytes.decode(sockobj.recv(1024))
	#print ("Recibido : ", MensRecibido) #el servidor no envia el mensaje de que esta procesando el envio hacia el modulo
	return MensRecibido

def ConectaSock(serverHost, serverPort):
	sockobj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)      # make a TCP/IP socket object
	try:
		sockobj.connect((serverHost, serverPort))   # connect to server machine + port
	except:
		try:
			serverHost="192.168.0.194"
			sockobj.connect((serverHost, serverPort))   # connect to server machine + port
		except:
			serverHost = "127.0.0.1"#clv1.servidor_local()
			sockobj.connect((serverHost, serverPort))   # connect to server machine + port
	print ("Abriendo Socket")
	sockobj.settimeout(10)  #medio segundo por si tenemos que enviar algo al servidor
	print ("Servidor con Tipo:%s y Codigo:%s obtiene el N.Serie de su BD" % (MiTipo, MiCodigo))
	thread = obtener_thread(sockobj, str(MiTipo), str(MiCodigo))
	if thread == -1:
		return -1
	print ("Nos establece el N. de Thread a enviar en cada mensaje : ", thread)
	MiThread = int(thread)
	print ("MiThread : %d" % (MiThread))
	#ahora enviamos el numero de serie, pero encriptado, el servidor ya sabe el numero de serie, y lo calculara, junto con un numero aleatorio
	num_rnd = str(int(round(random.random()*10000, 0)))
	digest_completo = ChimoFunc16.code_clave2(num_serie, num_rnd)
	print ("Con N.Serie:%s y N.Random:%s, se envia encriptado : " % (num_serie, num_rnd))
	print (digest_completo)
	resultado = obtener_thread(sockobj, digest_completo, num_rnd)
	if resultado == -1:
		return -1
	print ("Servidor calcula con : %s y su N. Serie sacado de su BD, el mismo digest, y devuelve OK si ha ido bien" % (num_rnd))
	if resultado.find("Error") != -1:
		print (resultado)
		exit()
	#sockobj.settimeout(10)
	return sockobj, MiThread



if len(sys.argv) < 4:
	print ("Pase como argumento Tipo, Codigo y Numero de Serie del Modulo")
	exit()
MiTipo = sys.argv[1]
MiCodigo = sys.argv[2]
num_serie = sys.argv[3]
set_pigpio = 0
set_sense = 0
if SenseHat != None:
	try:
		sense = SenseHat()
		set_sense = 1
	except:
		sense = None
else:
	sense = None
if pigpio != None:
	try:
		pix = pigpio()
		set_pigpio = 1
	except:
		pix = None
else:
	pix = None
nmens=10
espera=0.03
#leemos las funciones disponibles del fichero funciones16.txt
funciones={}
eventos={} #contiene los eventos que tenemos que controlar
cod_evento=1
func_evento = {}
ix1=1
fd1 = open("funciones16.txt", 'r')
linea = fd1.readline()
while linea != "":
	if linea[0] != '#':
		nc, campos = ChimoFunc16.extrae2(linea)
		funciones.setdefault(int(campos[0]), campos[2])
		if campos[3] == '511': #funciones a usar para eventos
			func_evento.setdefault(ix1, int(campos[0]))
			ix1+=1
	linea = fd1.readline()
fd1.close()
RecEstasVivo = time.time()
minombre = socket.gethostname()
serverHost = 'berentec.ddns.net'
serverPort = 10821
Enviar_Algo = 0;
destino = 0 # que es el servidor
num_mensaje=1
PideDatos = 0
sockobj, MiThread = ConectaSock(serverHost, serverPort)
#a continuacion recibimos desde el servidor los eventos que tenemos que controlar, definidos en la tabla eventos en el servidor.
ntimeout=0
while True:
	try:
		MensRecibido = bytes.decode(sockobj.recv(1024)) # espera timeout y mira si hay que enviar algo, porque haya un evento
	except socket.timeout:
		#aqui podemos aprovechar para enviar mensajes de entorno de forma automatica
		if PideDatos == 1: #tenemos que enviar datos del entorno, para ello simulamos un mensaje recibido desde el servidor
			#simulamos un evento
			#para decidir la funcion, de momento lo hacemos aleatorio con las funciones definidas como tipo 511 en el fichero funciones16.txt 
			funcevento = random.randint(1, ix1-1)
			MensRecibido = "0|%d|%d|%d|%c" % (MiThread, func_evento.get(funcevento), num_mensaje, ASCII_EOT)#"0|{}|{}|{:c}".format(MiThread, LEER_TPH, ASCII_EOT)
			#print ("Evento", MensRecibido)
		else:
			continue
	except: #el servidor se ha parado y salimos, se volvera a conectar con crontab
		break
	if MensRecibido == '0': #puede ocurrir cuando volvemos de evento
		continue
	origen, destino, tipo, camposd = DesgloseMensaje(MensRecibido)
	#print ("Origen : %s Destino : %s Tipo : %s" % (origen, destino, tipo))
	campos={} #algunas funciones necesitan datos que pasaremos en camposd
	ejecuta = funciones.get(tipo)
	camposd.setdefault("TipoModulo", MiTipo)
	camposd.setdefault("sense", sense)
	camposd.setdefault("pigpio", pix)
	camposd.setdefault("PideDatos", PideDatos)
	#print("Funcion:", ejecuta)
	if ejecuta == None:
		continue
	Enviar_Algo = getattr(IoTModulos16, ejecuta)(campos, camposd) #cuando vuelva de la funcion, campos contiene el resultado a devolver al servidor
	if "PideDatos" in campos:
		PideDatos = campos.get("PideDatos")
	if isinstance(Enviar_Algo, dict): #unico caso que devuelve un dict
		eventos.setdefault(cod_evento, Enviar_Algo.get(1))
		#aqui establecemos la funcion que debera controlar el evento, normalmente poner una interrupcion a vigilar un periferico
		#un switch, un sensor, ..., en dict eventos tenemos la funcion_origen a controlar, que deberemos ejecutar para que se ponga en marcha
		ejecuta = eventos.get(cod_evento).get("funcion_origen")
		Enviar_Algo = getattr(IoTPcDuino16, ejecuta)(cod_evento, eventos)
		cod_evento+=1
	if Enviar_Algo == -1: #salimos hemos recibido terminar, Enviar_Algo puede ser 0 que es lo normal, 1 hay que enviar el dic. campos o -1 que termina el programa
		break
	if PideDatos == 1 and tipo != 26:
		tipo = 26 #si estamos en modo evento, el servidor, debe saber que es tipo 26 para que lo trate como tal y lo envie a la cola de eventos
	campos.setdefault(1000, str(num_mensaje)) #para que el numero de mensaje sea el primer campo de cualquier mensaje a enviar, el
	#servidor quitara este primer campo, para tratar el resto de campos.
	MensEnviado = ConstruyeMensaje(sockobj, tipo, campos, destino, origen)
	del(campos)		
	num_mensaje+=1
	#time.sleep(espera)



