#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import flask
from flask import Flask, request, url_for
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

queue = queue.Queue()

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()
        
    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space

myWorld = World()

def set_listener( entity, data ):
    ''' do something with the update ! 
        Rather, do something after the update, which is to emit() tell all
        client to update their data
    '''
    message = {}
    message[entity] = data
    msg = json.dumps(message)
    queue.put_nowait(msg)

myWorld.add_set_listener( set_listener )
        
@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    '''return None'''
    return flask.redirect(url_for('static', filename='index.html'))

def read_ws(ws):
    '''A greenlet function that reads from the websocket and updates the world
       Read from web socket and use update'''
    # XXX: TODO IMPLEMENT ME
    try:
        while True:
            msg = ws.receive()
            '''print("WS RECV: %s" % msg)'''
            if (msg is not None):
                packet = json.loads(msg)
                for key, value in packet.items():
                    myWorld.set(key, value)
            else:
                break
    except:
        '''Done'''

@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    # XXX: TODO IMPLEMENT ME

    g = gevent.spawn( read_ws, ws )
    print("Subscribing")
    try:
        while True:
            msg = queue.get()
            '''print("WS SEND: %s" % msg)'''
            ws.send(msg)
    except Exception as e:# WebSocketError as e:
        print("WS Error %s" % e)
    finally:
        gevent.kill(g)

    '''
    This works
    while True:
        msg = ws.receive()
        print("WS RECV: %s" % msg)
        
        content = json.loads(msg)
        for key, value in content.items():
            myWorld.set(key, value) 

        ws.send(msg)
    '''

# I give this to you, this is how you get the raw body/data portion of a post in flask
# this should come with flask but whatever, it's not my project.
def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data.decode("utf8") != u''):
        return json.loads(request.data.decode("utf8"))
    else:
        return json.loads(request.form.keys()[0])

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    '''update the entities via this interface'''
    '''return None'''
    if request.is_json:
        content = request.get_json()
    
        for key, value in content.items():
            myWorld.set(key, value)

    else:
        data = request.get_data()
        content = json.loads(data)

        for key, value in content.items():
            myWorld.set(key, value)

    return myWorld.get(entity), 200

@app.route("/world", methods=['POST','GET'])    
def world():
    '''you should probably return the world here'''
    '''return None'''
    return myWorld.space, 200, {'ContentType':'application/json'}

@app.route("/entity/<entity>")    
def get_entity(entity):
    '''This is the GET version of the entity interface, return a representation of the entity'''
    '''return None'''
    return myWorld.get(entity), 200, {'ContentType':'application/json'}

@app.route("/clear", methods=['POST','GET'])
def clear():
    '''Clear the world out!'''
    '''return None'''
    myWorld.clear()
    return myWorld.space, 200, {'ContentType':'application/json'}


if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
