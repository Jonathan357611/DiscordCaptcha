from captcha.image import ImageCaptcha
import random
import string
import json


def generate_captcha(lenght, text=''):
    if text == '':
        text = ''.join([random.choice(string.ascii_letters) for _ in range(lenght)])
    image = ImageCaptcha(width = 280, height = 90)
    return image.generate(text), text, image

def load_data():
    with open("data.json", "r") as f:
        return json.loads(f.read())

def write_data(data):
    with open(f"data.json", "w") as f:
        f.write(json.dumps(data, indent=4))
    return True

#g = generate_captcha(15)
#g[2].write(g[1], f"{g[1]}.png")
