import socket
import sys

print('Starting Sankofa Library...', flush=True)

from app import create_app

app = create_app()

print('App ready.', flush=True)


def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(('127.0.0.1', port)) == 0


if __name__ == '__main__':
    port = 5000

    if port_in_use(port):
        print(
            f'\nERROR: Port {port} is already in use.\n'
            'Another copy of the app may still be running.\n'
            'Close other terminals running "python run.py", or run:\n'
            f'  netstat -ano | findstr :{port}\n'
            'Then stop the listed PID in Task Manager.\n',
            file=sys.stderr,
        )
        sys.exit(1)

    print(f'Open http://127.0.0.1:{port} in your browser\n', flush=True)
    app.run(debug=True, host='127.0.0.1', port=port, use_reloader=False)
