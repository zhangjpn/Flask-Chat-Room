# coding=utf-8
#!/usr/bin/env python
from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, Namespace, emit, join_room, leave_room, \
    close_room, rooms, disconnect

from flask_bootstrap import Bootstrap
bootstrap = Bootstrap()

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

app = Flask(__name__)
bootstrap.init_app(app)

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
app.jinja_env.variable_start_string = '{{ '
app.jinja_env.variable_end_string = ' }}'


def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        socketio.sleep(3)
        count += 1
        socketio.emit('my_response',
                      {'data': 'Server generated event',
                       'count': count,
                       'onlineUser': chatRoom.online_users},
                      namespace='/chat-room'
                      )

@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)


class ChatRoom(Namespace):

    online_users=[]

    def on_my_event(self, message):
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response',
            {'count': session['receive_count'],
                'data': message.get('data'),
                'username': message.get('username'),}
             )
        if message.get('username') not in self.online_users:
            self.online_users.append(message.get('username'))


    def on_my_broadcast_event(self, message):
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response',
             {'count': session['receive_count'],
                'data': message.get('data'),
                'chat': message.get('chat'),
                'username': message.get('username')},
             broadcast=True)

    def on_join(self, message):
        join_room(message['room'])
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response',
             {'data': 'In rooms: ' + ', '.join(rooms()),
              'count': session['receive_count']}
             )


    def on_leave(self, message):
        leave_room(message['room'])
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response',
             {'data': 'In rooms: ' + ', '.join(rooms()),
              'count': session['receive_count']}
             )

    def on_close_room(self, message):
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response', {'data': 'Room ' + message['room'] + ' is closing.',
                             'count': session['receive_count']},
             room=message['room'])
        close_room(message['room'])

    def on_my_room_event(self, message):
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response',
             {'data': message['data'], 'count': session['receive_count']},
             room=message['room'])

    def on_disconnect_request(self):
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response',
             {'data': 'Disconnected!', 'count': session['receive_count']})
        disconnect()


    def on_my_ping(self):
        emit('my_pong')

    def on_connect(self):
        global thread
        if thread is None:
            thread = socketio.start_background_task(target=background_thread)
        emit('my_response', {'data': 'Connected', 'count': 0})


    def on_disconnect(self):
        print('Client disconnected', request.sid)
        self.online_users.remove(session.get('username'))

chatRoom = ChatRoom('/chat-room')
socketio.on_namespace(chatRoom)


if __name__ == '__main__':
    socketio.run(app, debug=True, host="0.0.0.0")
