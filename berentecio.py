# -*- coding: utf8 -*-

"""

The following converters exist:

int	accepts integers
float	like int but for floating point values
path	like the default but also accepts slashes

with app.test_request_context():
	print url_for('index')
	print url_for('login')
	print url_for('login', next='/')
	print url_for('profile', username='John Doe')


By default, a route only answers to GET requests, but that can be changed by providing the methods argument to the route() decorator. Here are some examples:

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        do_the_login()
    else:
        show_the_login_form()

The following methods are very common:

GET
The browser tells the server to just get the information stored on that page and send it. This is probably the most common method.
HEAD
The browser tells the server to get the information, but it is only interested in the headers, not the content of the page. 
An application is supposed to handle that as if a GET request was received but to not deliver the actual content. 
In Flask you don 't have to deal with that at all, the underlying Werkzeug library handles that for you.
POST
The browser tells the server that it wants to post some new information to that URL and that the server must ensure the data is 
stored and only stored once. This is how HTML forms usually transmit data to the server.
PUT
Similar to POST but the server might trigger the store procedure multiple times by overwriting the old values more than once. Now you might be asking why this is useful, but there are some good reasons to do it this way. Consider that the connection is lost during transmission: in this situation a system between the browser and the server might receive the request safely a second time without breaking things. With POST that would not be possible because it must only be triggered once.
DELETE
Remove the information at the given location.
OPTIONS
Provides a quick way for a client to figure out which methods are supported by this URL. Starting with Flask 0.6, this is implemented for you automatically.

url_for('static', filename='style.css') #dice que debe ponerse en el directorio static, y el nombre del fichero en ese directorio es style.css, para organizar mejor las paginas

Los templates deben ir en el directorio templates, obligatoriamente

from flask import Markup
>>> Markup('<strong>Hello %s!</strong>') % '<blink>hacker</blink>'
Markup(u'<strong>Hello &lt;blink&gt;hacker&lt;/blink&gt;!</strong>')
>>> Markup.escape('<blink>hacker</blink>')
Markup(u'&lt;blink&gt;hacker&lt;/blink&gt;')
>>> Markup('<em>Marked up</em> &raquo; HTML').striptags()
u'Marked up HTML'
Changed in version 0.5: Autoescaping is no longer enabled for all templates. The following extensions for templates trigger autoescaping: .html, .htm, .xml, .xhtml. Templates loaded from a string will have autoescaping disabled.


REQUEST:
with app.test_request_context('/hello', method='POST'):
    # now you can do something with the request until the
    # end of the with block, such as basic assertions:
    assert request.path == '/hello'
    assert request.method == 'POST'

The other possibility is passing a whole WSGI environment to the request_context() method:

from flask import request

with app.request_context(environ):
    assert request.method == 'POST'



COOKIES
Cookies
To access cookies you can use the cookies attribute. To set cookies you can use the set_cookie method of response objects. The cookies attribute of request objects is a dictionary with all the cookies the client transmits. If you want to use sessions, do not use the cookies directly but instead use the Sessions in Flask that add some security on top of cookies for you.

Reading cookies:

from flask import request

@app.route('/')
def index():
    username = request.cookies.get('username')
    # use cookies.get(key) instead of cookies[key] to not get a
    # KeyError if the cookie is missing.
Storing cookies:

from flask import make_response

@app.route('/')
def index():
    resp = make_response(render_template(...))
    resp.set_cookie('username', 'the username')
    return resp


@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login')
def login():
    abort(401)
    this_is_never_executed()

SESSIONS
Sessions
In addition to the request object there is also a second object called session which allows you to store information specific to a user from one request to the next. This is implemented on top of cookies for you and signs the cookies cryptographically. What this means is that the user could look at the contents of your cookie but not modify it, unless they know the secret key used for signing.

In order to use sessions you have to set a secret key. Here is how sessions work:

from flask import Flask, session, redirect, url_for, escape, request

app = Flask(__name__)

@app.route('/')
def index():
    if 'username' in session:
        return 'Logged in as %s' % escape(session['username'])
    return 'You are not logged in'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['username'] = request.form['username']
        return redirect(url_for('index'))
    return '''
        <form action="" method="post">
            <p><input type=text name=username>
            <p><input type=submit value=Login>
        </form>
    '''
    
    
To access parameters submitted in the URL (?key=value) you can use the args attribute:

searchword = request.args.get('key', '')


Se ha configurado Apache para que cuando reciba /ws/ reenvie la peticion a un servidor websockets en el mismo servidor
Por tanto desde cualquier cliente se puede acceder a dicho servidor, pero tenemo dos destinos diferentes.

Si estamos mucho tiempo sin usar la BD, nos desconecta, hay que tener esto en cuenta, para no desconectarnos, unico error que he notado hasta ahora.
"""
import os, sys
sys.path.insert(0, '/media/joaquin/Home2/www/Lib')
from flask import Flask, render_template, Markup, request, abort, redirect, url_for, session, escape, flash, g 
from flask import Blueprint
from flask.views import View
from flask_socketio import SocketIO
from werkzeug import secure_filename
import eventlet
#from flask.ext.login import LoginManager, login_required
import MyFunc16
import ChimoFunc16
import USBFunc16
import Myconfig
import asyncio
#import websockets
import FuncionesApp
import logging
import json
import queue
import threading

PCLINUX=512
global numuser, DictConServer
sys.path.insert(0, '/home/joaquin/Dropbox/Python35/Lib35')
eventlet.monkey_patch()
app = Flask(__name__)
socketio = SocketIO(app)
#app.add_url_rule('/menu/<opcion>', view_func=FuncionesApp.index)
if os.name == 'nt':
	fichlog='d:\Tmp\Berentec.log'
else:
	fichlog='/media/joaquin/Home2/Tmp/berentec.log'
logging.basicConfig(filename=fichlog,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%d-%m-%y %H:%M:%S',
                    level=logging.DEBUG)
logger = logging.getLogger(__name__)
my1=Myconfig.claves()
DictConServer={}
datos_user = my1.user_linux()
numuser=0
miconfig={}
bd = datos_user.get("bd")
user = datos_user.get('usuario')
pwd = datos_user.get('password')		
miconfig.setdefault('bd', bd)
miconfig.setdefault('userdb', user)
miconfig.setdefault('pwddb', pwd)
miconfig.setdefault('numuser', numuser)
# set the secret key.  keep this really secret:
#una forma de generar un numero random, puede ser os.urandom de los bytes que queramos
num_secreto=os.urandom(32) #genera una clave aleatoria cada vez de 32 bytes
app.secret_key = num_secreto#'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT' #secret key para la sesion, de forma que una sesion no pueda ser cambiada por el browser
#tenemos tantas colas y conexiones con serveriot como necesitemos para adaptarnos al numero de clientes de berentecio
Num_Threads=2 #numero actual, 2 threads, solo cambiando el numero de threads a arrancar y el codigo y numero de serie del modulo lo tenemos
DicThreads={}
Modulos=[[PCLINUX, "111111", "1111222211"], [PCLINUX, "111112", "1111222212"]]
for x1 in range(Num_Threads):
	DicTh={}
	sockobj, MiThread = FuncionesApp.ConectaSock('localhost', my1.puerto_server_disp, Modulos[x1][0], Modulos[x1][1], Modulos[x1][2], logger)
	DicTh.setdefault("socket", sockobj)
	DicTh.setdefault("MiThread", MiThread)
	cola_enviar=queue.Queue(0) #cola de enviar mensajes, tipo msgserv
	DicTh.setdefault("cola", cola_enviar)
	th_env=FuncionesApp.Thread(FuncionesApp.enviar_mensaje, cola_enviar,  sockobj, MiThread, logger, socketio) 
	DicTh.setdefault("th_env", th_env)
	DicThreads.setdefault(x1, DicTh)
	del(DicTh)

@app.route('/hola/')
@app.route('/hola/<name>') #los dos router van a la misma funcion, y le pasan el argumento ya sea None o el nombre, la pagina html, decide que hacer con el argumento, se hace con jinja2
def hello(name=None):
	return render_template('hola.html', name=name)
@app.route('/server/<name>')
def servidor(name="ws_time"):
	return render_template(name+'.html')
@app.route('/user/<username>') #es como si nos pasara un parametro, ejecuta siempre la funcion,
def show_user_profile(username):
	# show the user profile for that user
	return 'User %s' % username
@app.route('/post/<int:post_id>') #aqui obliga a recibir un entero, si se pasa un string da un error de pagina no encontrada
def show_post(post_id):
	# show the post with the given id, the id is an integer
	return 'Post %d' % post_id
@app.route('/projects/') #funciona en cualquier caso, tanto si se pasa / del final como si no
def projects():
	return 'The project page'

@app.route('/about') #funciona solo se se pasa sin / del final
def about():
	return 'The about page'
@app.route('/')
@app.route('/login', methods=['POST', 'GET'])
def login():
	global numuser, DictConServer
	if 'user' in session:
		#return 'Logged in as %s' % escape(session['user'])
		return FuncionesApp.Menu(miconfig, numuser, session['user'])
	error = None
	if request.method == 'POST':
		if FuncionesApp.valid_login(miconfig, request.form['user'], request.form['password']):
			session['user'] = request.form['user']
			flash('You were logged in')
			numuser+=1
			logger.info(request)
			logger.info("Login de : "+session.get('user'))
			return FuncionesApp.Menu(miconfig, numuser, request.form['user'])
		else:
			error = 'Invalid username/password'
	return render_template('login.html', fecha=ChimoFunc16.fechahoy(), error=error) #cuando sea GET

@app.route('/upload', methods=['GET', 'POST']) #poner enctype="multipart/form-data" en el fichero html
def upload_file():
	if request.method == 'POST':
		f = request.files['the_file']
		f.save('/uploads/' + secure_filename(f.filename)) #f.save('/var/www/uploads/uploaded_file.txt')
@app.route('/mensaje')
def mensaje():
	return render_template('pymensajes2.html')
@app.errorhandler(404)
def page_not_found(error):
	return render_template('page_not_found.html')

@app.route('/logout')
@app.route('/salir')
@app.route('/menu/salir')
def logout():
	global numuser, DictConServer
	# remove the username from the session if it's there
	if session.get('user'):
		#FuncionesApp.DisconServerIoT(DictConServer, session.get('user'))#DictConServer.pop(session.get('user'))
		logger.info("Logout de : "+session.get('user'))
		#DictConServer.pop(session.get('user'))
		session.pop('user')
		
	return render_template('login.html', fecha=ChimoFunc16.fechahoy())

@app.route('/modulos', methods=['POST', 'GET'])
def modulos():
	global DictConServer
	error = None
	#if 'user' not in session:
	#	return render_template('login.html', fecha=ChimoFunc16.fechahoy(), error=error)
	if request.method == 'POST':
		#se ha rellenado el form y venimos aqui ejecutar lo que venga del form
		return FuncionesApp.ModulosCon('post', DictConServer,  session.get('user'), logger)
	#se debe rellenar el form
	else:
		return FuncionesApp.ModulosCon('get', DictConServer,  session.get('user'), logger)
#si recibimos /funcion, es queremos ejecutar una funcion
#aqui venimos para todos los form del menu
@app.route('/menu/<opcion>', methods=['POST', 'GET'])
def funcion(opcion):
	global DictConServer
	error = None
	assert opcion
	if 'user' not in session:
		return render_template('login.html', fecha=ChimoFunc16.fechahoy(), error=error)
	if request.method == 'POST':
		#se ha rellenado el form y venimos aqui ejecutar lo que venga del form
		return getattr(FuncionesApp, opcion)('post', numuser, session.get('user'), opcion, request.environ, logger, datos_user)
	#se debe rellenar el form
	else:
		return getattr(FuncionesApp, opcion)('post', numuser, session.get('user'), opcion, request.environ, logger, datos_user)
#si recibimos /funcion, es queremos ejecutar una funcion
@app.route('/funcion/<funcion>')
def ejecuta(funcion):
	assert funcion
#todo lo que venga de un movil se manda a una aplicación diferente
@app.route('/mobile/<opcion>')
def MobApp(opcion):
	assert opcion

#con socketio, podemos hacer que ServerIoT sea cliente de este proceso y funcionemos por eventos, de forma
#q ue cuando recibimos un mensaje (por ejemplo un interruptor se ha pulsado, nos envia cual y donde ha sido
#cuando ejecutamos el evento podemos comunicar a la pagina correspondiente que tambien tiene socketio, lo que ha pasado
# cuando una pagina quiere enviar un evento al ServerIoT, enviamos un mensaje al thread que queramos para que lo ejecute
#)
#recibimos un mensaje del servidor, nos dice que modulo ha tenido un evento como pulsar un switch, bajar la temperatura
#de un valor determinado, ... esto debemos enviarselo a un cliente determinado en una pagina determinada
#tambien puede ser en contestacion a un mensaje anterior
#@socketio.on('message', namespace='/serveriot')
#@socketio.on('/serveriot/<message>')
@socketio.on('msgcon', namespace='/serveriot')
def RecMensServerIoT(msg):
	logger.info("Mensaje Conexion: "+msg.get('data'))
	#socketio.emit('msg', {'data':str(msg)}, namespace="/serveriot")
#data puede contener varios campos separados por & y cada uno puede tener 2 items separados por |
#recibimos el thread y la funcion a ejecutar y enviamos el mensaje al servidor
#ejemplo de recepcion : 1|Mkr1000 1&50|LoopBack&ABCD&EFGH, de aqui sacamos el thread destino y la funcion, ademas de campo1 y campo2

@socketio.on('msgdiscon', namespace='/serveriot')
def RecMensServerIoTDis(msg):
	socketio.emit('disconnect', "Desconecta", namespace="/serveriot")
@socketio.on('msgcli', namespace='/serveriot')
def RecMensCli(msg):
	mensrec = msg.get('data')
	#miramos cual de las dos colas tiene menos elementos y la usamos
	#si hiciera falta pondremos más colas y más threads para aumentar la velocidad de respuesta
	nitems=[]
	hecho=0
	for x1 in range(Num_Threads):
		nitems.append(None)
		nitems[x1]=DicThreads.get(x1).get("cola").qsize()
		if nitems[x1] == 0:
			DicThreads.get(x1).get("cola").put(mensrec) #si alguna esta vacia, que es lo normal la usamos
			hecho=1
			break
	if hecho == 0: #si todas las colas estan con elementos, buscamos la que menos elementos tenga
		minimo = 100
		usarcola = 0
		for x1 in range(Num_Threads):
			if minimo >=  nitems[x1]:
				minimo = nitems[x1]
				usarcola = x1
		DicThreads.get(usarcola).get("cola").put(mensrec) 
	del(nitems)
	#se iran despachando conforme se envian a la cola, socketio se ha pasado como argumento a la funcion enviar_mensaje
	
#el ServerIoT actual como cliente, para enviarnos un evento, de tipo srviot que desde aqui se reenvia a la pagina como tipo de mensaje eventserv
#de esta forma no tenemos que usar ni otro thread, ni otra cola
@socketio.on('srviot', namespace='/serveriot')
def RecMensServerIoT(msg):
	#logger.info("Mensaje srviot: "+msg.get('data'))
	socketio.emit('eventserv', {'data':msg.get('data')}, namespace="/serveriot")

#json.dumps({'msg':msg['msg']})
#recibimos un mensaje de una pagina cliente que quiere enviar un mensaje a un modulo dado, como tenemos el modulo
#sacado de la BD, podemos enviar el mensaje sin problemas.
#@socketio.on('message', namespace='/clientiot')
"""
@socketio.on('/clientiot/<message>')
def RecMensClientIoT(message):
	return "Client: "+message
@socketio.on('connect', namespace='/serveriot')
def ws_conn():
	#socket.emit('conectado', {data: 'Estoy Conectado!'});
	logging.info('Conectado')
	#socketio.emit('msg', {'msg':'Conectado'}, namespace='/serveriot')
	, debug=True
"""
if __name__ == '__main__':
	socketio.run(app, host='0.0.0.0', port=10824, log_output=True) #arranca en el 5000
	#app.run(host='0.0.0.0', debug=True) #para que pueda accederse desde cualquier IP, y que recargue el programa cuando cambiemos el contenido : debug=True
