import colorama
from PIL import Image
import io
import base64
import json
import os
import numpy as np

# init colorama
colorama.init(autoreset=True)

def save_json(path, target):
    json.dump(target, open(path, "w", encoding="utf-8"), indent=4,ensure_ascii=False)

def load_json_if_exist(path, default={}):
    if not os.path.exists(path):
        return default
    else:
        return json.load(open(path, "r", encoding="utf-8"))

def user_check(message=""):
    """
    Ask for user input until the user enters either Y or N.
    """
    print_with_color(f"{message}\nDo you want to continue? (Y/N)", "yellow")

    while True:
        user_input = input().strip().upper()

        if user_input == 'Y':
            return True
        elif user_input == 'N':
            return False
        else:
            print_with_color("Invalid choice. Please enter either Y or N. Try again.","yellow")

def print_with_color(content, front_color="reset", back_color="reset", style="normal", pad=0, logger=None, log_level="info"):
    """
    !pip install colorama
    Fore: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
    Back: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
    Style: DIM, NORMAL, BRIGHT, RESET_ALL
    """
    content = str(content)
    if len(content) + 4 <= pad:
        content = "=" * ((pad - (len(content) + 2)) // 2) + " " + content + " " + "=" * (pad - (pad - (len(content) + 2)) // 2 - (len(content) + 2))

    content_with_color = getattr(colorama.Fore, front_color.upper()) + getattr(colorama.Back, back_color.upper()) + getattr(colorama.Style, style.upper()) + content
    print(content_with_color)
    if logger:
        getattr(logger,log_level)(content)


def encode_image_base64(image_path,max_size=-1):
    with open(image_path, "rb") as image_file:
        if max_size > 0:
            image = Image.open(image_file)
            image.thumbnail((max_size, max_size))
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='png')
            image_bytes = output_buffer.getvalue()
        else:
            image_bytes = image_file.read()
        return base64.b64encode(image_bytes).decode('utf-8')

def encode_image_PIL(image_path,max_size=-1):
    if max_size > 0:
        image = Image.open(image_path)
        image.thumbnail((max_size, max_size))
    else:
        image = Image.open(image_path)
    return image

def cosine_similarity(vec1, vec2):
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    return dot_product / (norm_vec1 * norm_vec2)


def logo():
    content_1 = """
█████████████████████████████████████████╗
╚════════════════════════════════════════╝"""
    content="""
███╗   ███╗ @  ██████╗  @ ██████╗  @  █████╗ 
████╗ ████║ @ ██╔═══██╗ @ ██╔══██╗ @ ██╔══██╗
██╔████╔██║ @ ██║   ██║ @ ██████╔╝ @ ███████║
██║╚██╔╝██║ @ ██║   ██║ @ ██╔══██╗ @ ██╔══██║
██║ ╚═╝ ██║ @ ╚██████╔╝ @ ██████╔╝ @ ██║  ██║
╚═╝     ╚═╝ @  ╚═════╝  @ ╚═════╝  @ ╚═╝  ╚═╝
"""
    content_2="""█████████████████████████████████████████╗
╚════════════════════════════════════════╝
"""
    print_with_color(content_1,"cyan")

    colorlist=["blue","yellow","red","green"]
    for line in content.split("\n"):
        if line.strip() == "":
            continue
        strings = line.split("@")
        content_with_color = ""
        for i ,string in enumerate(strings):
            content_with_color += getattr(colorama.Fore, colorlist[i].upper()) + getattr(colorama.Back, "RESET") + getattr(colorama.Style, "NORMAL") +string
        print(content_with_color)

    print_with_color(content_2,"MAGENTA")

if __name__ == "__main__":
    logo()
    print_with_color("Test Utils", "blue", "magenta", "bright")
    print_with_color("Test Utils", "blue", "magenta", "bright", pad=20)
