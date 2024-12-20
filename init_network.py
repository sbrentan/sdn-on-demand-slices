import requests


def init_network():
    print("Initializing network via REST...")
    url = "http://127.0.0.1:8080/network/init"
    try:
        response = requests.post(url)
        if response.status_code == 200:
            print("Network is ready!")
            print(response.json())
        else:
            print("Error:", response.status_code, response.text)
    except Exception as e:
        print("Failed to call init_network:", e)


if __name__ == '__main__':
    init_network()
