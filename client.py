import socket

# ヘッダーとボディの送信
def send_data(client_socket, room_name, operation, state, token='', user_name=''):
    room_name_bytes = room_name.encode("utf-8")
    operation_bytes = operation.to_bytes(1, 'big')
    state_bytes = state.to_bytes(1,'big')
    room_name_size = len(room_name_bytes).to_bytes(1,'big')
    token_bytes = token.encode('utf-8')
    token_size = len(token_bytes).to_bytes(1, 'big')

    header = room_name_size + operation_bytes + state_bytes + token_size

    user_name_bytes = user_name.encode('utf-8')
    user_name_size = len(user_name_bytes).to_bytes(1, 'big')

    client_socket.sendall(header + room_name_bytes + token_bytes + user_name_size + user_name_bytes)

# チャットルーム作成
def create_room(client_socket, room_name):
    operation = 1
    state = 0

    send_data(client_socket, room_name, operation, state)

    response = client_socket.recv(3)
    if response[0] == 1:
        if response[1] == 1:
            token_size = response[2]
            token = client_socket.recv(token_size).decode('utf-8')
            print("チャットルームの作成に成功しました")
            print(f"トークン：{token}")
            return token
        else:
            print("すでに存在するチャット名です")
            return None
    else:
        print("チャットルームの作成に失敗しました")
        return None

# チャットルームに参加
def join_room(client_socket, user_name, room_name, token):
    operation = 2
    state = 1

    send_data(client_socket,room_name, operation, state, token, user_name)

    while True:
            response = client_socket.recv(14)
            if not response:
                break
            if response == b'Access granted':
                print("チャットルームへの参加に成功しました")
                return True
    
    print("チャットルームへの参加に失敗しました")
    return False

def main():
    # サーバーの指定
    server_address = input("サーバーアドレスを入力してください：")
    server_port = 10200
    udp_port = 10100

    # クライアントソケット
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    udp_socket = None

    try:
        client_socket.connect((server_address, server_port))

        user_name = input("ユーザー名を入力してください：")
        token = ''
        action = input("新しいチャットルームを作りますか？（yes/no）:")
        if action.lower() == "yes":
            room_name = input("チャットルーム名を入力してください")
            token = create_room(client_socket, room_name)
            if token is None:
                return
        else:
            room_name = input("参加したいチャットルーム名を入力してください：")
            token = input("参加トークンを入力してください：")

        if not join_room(client_socket, user_name, room_name, token):
            return

        # TCPコネクションを閉じる
        client_socket.close()

        # UDPでサーバーに接続
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        room_name_bytes = room_name.encode('utf-8')
        room_name_size = len(room_name_bytes).to_bytes(1, 'big')
        token_bytes = token.encode('utf-8')
        token_size = len(token_bytes).to_bytes(1, 'big')

        while True:
            message = input('メッセージを入力してください：')
            message_bytes = message.encode('utf-8')
            packet = room_name_size + token_size + room_name_bytes + token_bytes + message_bytes
            udp_socket.sendto(packet, (server_address, udp_port))

            try:
                udp_socket.settimeout(2)
                response, _ = udp_socket.recvfrom(4096)
                print(response)
                if response == b'Disconnected':
                    print("サーバーから切断されました。もう一度接続してください。")
                    break
                else:
                    print(f"{response.decode('utf-8')}:メッセージを送信しました")
            
            except socket.timeout:
                print("サーバーから応答がありません。サイド試行してください。")

    except ConnectionResetError:
        print("サーバーからの接続がリセットされました。再度接続してください。")
        return
    except KeyboardInterrupt:
        print("サーバーとの接続を解除します")
    finally:  
        if client_socket:
            client_socket.close()
        if udp_socket:
            udp_socket.close()     

if __name__ == "__main__":
    main()