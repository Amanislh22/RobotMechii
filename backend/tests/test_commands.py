import requests
import os

def test_generate_path_commands():
    url = "http://localhost:8000/generate-path-commands/"
    test_image = os.path.join("uploads", "test_path.png")  # Add a test image
    if not os.path.exists(test_image):
        print("Test image not found. Please add a test_path.png to uploads/")
        return

    with open(test_image, "rb") as f:
        files = {"file": (test_image, f, "image/png")}
        data = {"scale_factor": 0.01}
        response = requests.post(url, files=files, data=data)

    print("Status Code:", response.status_code)
    print("Response:", response.json())

def test_send_commands_uart():
    url = "http://localhost:8000/send-commands-uart/"
    data = {"commands": ["forward: 1.0m", "Right: 90.0°"]}
    response = requests.post(url, json=data)
    print("UART Test - Status Code:", response.status_code)
    print("UART Test - Response:", response.json())

def test_send_commands_mqtt():
    url = "http://localhost:8000/send-commands-mqtt/"
    data = {"commands": ["forward: 1.0m", "Right: 90.0°"]}
    response = requests.post(url, json=data)
    print("MQTT Test - Status Code:", response.status_code)
    print("MQTT Test - Response:", response.json())

if __name__ == "__main__":
    test_generate_path_commands()
    test_send_commands_uart()
    test_send_commands_mqtt()
