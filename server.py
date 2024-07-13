import socket
from threading import Thread
import uuid

rooms = {}

def handle_client(conn, addr):
    global rooms
    while True:
        try:
            # ヘッダーの取得
            header = conn.recv(4)
            if not header:
                break

            room_name_size = header[0]
            operation = header[1]
            state = header[2]
            token_size = header[3]

            # ボディの取得
            room_name = conn.recv(room_name_size).decode('utf-8')
            payload_token = conn.recv(token_size).decode('utf-8')
            user_name_size = int.from_bytes(conn.recv(1), 'big')
            user_name = conn.recv(user_name_size).decode('utf-8')

            # チャットルーム作成のリクエスト
            if operation == 1 and state == 0:
                if room_name not in rooms:
                    token = str(uuid.uuid4())   # 一意のトークンを生成
                    rooms[room_name] = {'tokens': [token], 'users': [], 'ip': addr[0], 'host': addr}
                    print(f"{addr}によって{room_name}が作成されました")
                    response_state = 1  # 準備完了
                    token_bytes = token.encode('utf-8')
                    token_size = len(token_bytes).to_bytes(1, 'big')
                    conn.sendall((1).to_bytes(1, 'big') + response_state.to_bytes(1, 'big') + token_size + token_bytes)
                else:
                    print(f"{room_name}はすでにあります")
                    response_state = 0  # エラー
                conn.sendall((1).to_bytes(1, 'big') + response_state.to_bytes(1, 'big'))

            # トークンを送信
            elif operation == 2 and state == 0:
                token = rooms[room_name]['tokens'].encode('utf-8')
                conn.sendall((2).to_bytes(1, 'big') + token_size + token_bytes)

            elif operation == 2 and state == 1:
                # トークンとIPアドレスが正しい場合、クライアントをチャットルームに追加
                if payload_token in rooms[room_name]['tokens'] and addr[0] == rooms[room_name]['ip']:
                    rooms[room_name]['users'].append({'conn': conn, 'name': user_name, 'addr': addr})
                    conn.sendall(b'Access granted')
                    print(f"{user_name}が{room_name}に入室しました")
                else:
                    conn.sendall(b'Access denied')

        except Exception as e:
            print(f'エラー：{e}')
            break

    print("コネクションクローズ")
    conn.close()

def udp_listener(udp_socket):
    global rooms
    while True:
        try:
            data, address = udp_socket.recvfrom(4096)
            room_name_size = data[0]
            token_size = data[1]
            room_name = data[2: 2 + room_name_size].decode('utf-8')
            token = data[2 + room_name_size: 2 + room_name_size + token_size].decode('utf-8')
            message = data[2 + room_name_size + token_size:].decode('utf-8')

            if room_name in rooms:
                room = rooms[room_name]
                if token in room['tokens'] and address[0] == room['ip']:
                    for user in room['users']:
                        udp_socket.sendto(data, user['addr'])
                        udp_socket.sendto(b'Connected', address)
                else:
                    disconnect_message = b'Disconnected'
                    udp_socket.sendto(disconnect_message, address)
                    room['tokens'].remove(token)
                    room['users'] = [user for user in room['users'] if user['addr'] != address]
                    print(f"{address}に対してIPもしくはトークンが一致しません。トークンを削除します。")
            else:
                print(f"ルーム：{room_name}はまだ作られていません")

        except Exception as e:
            print(f'エラー：{e}')


def main():
    host = ''
    port = 10200
    udp_port = 10100
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(('', udp_port))

    print("サーバーが接続待期中です")

    # UDPリスナーを別スレッドで起動
    Thread(target=udp_listener, args=(udp_socket,), daemon=True).start()

    try:
        while True:
            conn, addr = server_socket.accept()
            print(f"{addr}と接続しました")
            Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("サーバーをシャットダウンします")
    finally:
        print("サーバーソケットを閉じます")
        server_socket.close()

if __name__ == "__main__":
    main()
