import base64
import pdb
import cv2
import os
import sys
import numpy as np
import time

sys.path.append('../..')  # Add the path to the project to the sys.path, in case you want to test this script independently
from moba.process.vh_proc import *
from moba.utils.utils import print_with_color, encode_image_base64


def concatenate_images(image1_path, image2_path):
    """
    Concatenate two images into one image and save it to the same directory as the original images
    :param image1_path: the path of the first image
    :param image2_path: the path of the second image
    :return: the path of the concatenated image
    """
    image1_path = image1_path.replace("\\", "/")
    image2_path = image2_path.replace("\\", "/")
    # Extract names of image1 and image2
    image1_name = image1_path.split("/")[-1].split(".")[0]
    image2_name = image2_path.split("/")[-1].split(".")[0]
    # print("image1_name:", image1_name)
    # print("image2_name:", image2_name)

    # Set the name for the concatenated image
    concatenated_image_name = f"{image1_name.split('_')[0]}_{image2_name.split('_')[0]}_cat.png"
    # print("concatenated_image_name:", concatenated_image_name)

    # Read image1 and image2
    # image1 = cv2.imread(image1_path)
    # image2 = cv2.imread(image2_path)
    image1 = cv2.imdecode(np.fromfile(image1_path, dtype=np.uint8), cv2.IMREAD_COLOR)
    image2 = cv2.imdecode(np.fromfile(image2_path, dtype=np.uint8), cv2.IMREAD_COLOR)

    """
    # 拼接image1和image2
    concatenated_image = cv2.hconcat([image1, image2])
    # 保存拼接后的图片, 保存的路径为image1和image2的路径的前缀+拼接后的图片的名字
    # 设置保存图片的路径
    concatenated_image_path = os.path.join(os.path.dirname(image1_path), concatenated_image_name)
    print("concatenated_image_path:", concatenated_image_path)
    # 保存图片
    cv2.imwrite(concatenated_image_path, concatenated_image)
    # 返回拼接后的图片的路径
    return concatenated_image_path
    """

    # Get height of image1 and image2
    height1, width1 = image1.shape[:2]
    height2, width2 = image2.shape[:2]
    max_height = max(height1, height2)

    # Create a separator line
    separator_line = np.ones((max_height, 8, 3), dtype=np.uint8) * 128

    # Concatenate image1, separator line, and image2 horizontally
    concatenated_image = np.hstack((image1, separator_line, image2))

    # Save the concatenated image
    concatenated_image_path = os.path.join(os.path.dirname(image1_path), concatenated_image_name)
    # print("concatenated_image_path:", concatenated_image_path)
    # cv2.imwrite(concatenated_image_path, concatenated_image)
    cv2.imencode('.png', concatenated_image)[1].tofile(concatenated_image_path)

    return concatenated_image_path


def putBText(img, text, text_offset_x=20, text_offset_y=20, vspace=10, hspace=10, font_scale=1.0, background_RGB=(228, 225, 222), text_RGB=(1, 1, 1), font=cv2.FONT_HERSHEY_DUPLEX, thickness=2, alpha=0.6, gamma=0):
    """
    From pyshine library
    https://pypi.org/project/pyshine/

    Inputs:
    img: cv2 image img
    text_offset_x, text_offset_x: X,Y location of text start
    vspace, hspace: Vertical and Horizontal space between text and box boundries
    font_scale: Font size
    background_RGB: Background R,G,B color
    text_RGB: Text R,G,B color
    font: Font Style e.g. cv2.FONT_HERSHEY_DUPLEX,cv2.FONT_HERSHEY_SIMPLEX,cv2.FONT_HERSHEY_PLAIN,cv2.FONT_HERSHEY_COMPLEX
          cv2.FONT_HERSHEY_TRIPLEX, etc
    thickness: Thickness of the text font
    alpha: Opacity 0~1 of the box around text
    gamma: 0 by default

    Output:
    img: CV2 image with text and background
    """
    R, G, B = background_RGB[0], background_RGB[1], background_RGB[2]
    text_R, text_G, text_B = text_RGB[0], text_RGB[1], text_RGB[2]
    (text_width, text_height) = cv2.getTextSize(text, font, fontScale=font_scale, thickness=thickness)[0]
    x, y, w, h = text_offset_x, text_offset_y, text_width, text_height
    crop = img[y - vspace:y + h + vspace, x - hspace:x + w + hspace]
    white_rect = np.ones(crop.shape, dtype=np.uint8)
    b, g, r = cv2.split(white_rect)
    rect_changed = cv2.merge((B * b, G * g, R * r))

    res = cv2.addWeighted(crop, alpha, rect_changed, 1 - alpha, gamma)
    img[y - vspace:y + vspace + h, x - hspace:x + w + hspace] = res

    cv2.putText(img, text, (x, (y + h)), font, fontScale=font_scale, color=(text_B, text_G, text_R), thickness=thickness)
    return img


def mark_screenshot(image_path, elem_list):
    """
    Mark the position of the elements on the image, including the bounding box and the tag of the element
    :param image_path: the path of the image
    :param elem_list: the list of elements
    :return: the path of the marked image
    """
    # Set the color of the bounding box for each type of element
    color = {
        "clickable": (0, 0, 255),
        # "focusable": (0, 255, 255),
        "long_clickable": (0, 255, 0),
        # "checkable": (255, 0, 255),
        "scrollable": (255, 0, 0)
    }

    img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)

    for elem in elem_list:
        for key in color.keys():
            if key in elem.attributes.keys():
                x1, y1 = elem.topleft
                x2, y2 = elem.bottomright
                if x1 == 0 and y1 == 0 and x2 == 0 and y2 == 0:
                    continue
                """
                # 画num tag(控件在list中的编号), 右上角(以控件的右上角为基准，向左偏移50，向下偏移50)，字体颜色为白色，用pyshine库中的函数实现
                # cv2.putText(img, text= str(elem.index), org = (x2-50 , y1+50), fontFace= cv2.FONT_HERSHEY_SIMPLEX, fontScale=1.2, color=(0, 0, 0), thickness=3)
                """
                tag_text = str(elem.index)
                font_color = (255, 255, 255)
                bg_color = (64, 64, 64)  # Background color: dark grey

                # we make the bounding box smaller to avoid overlapping the lines
                scale = 0.9
                # solve: (x2-x1-pad_size)*(y2-y1-pad_size) = (x2-x1)*(y2-y1)*scale
                pad_size = int((1 - scale) * (x2 - x1) * (y2 - y1) / (x2 - x1 + y2 - y1))

                # bounding box
                cv2.rectangle(img, (x1 + pad_size, y1 + pad_size), (x2 - pad_size, y2 - pad_size), color[key], 5)

                # In function putBText
                # crop=img[y-vspace:y+h+vspace, x-hspace:x+w+hspace]
                x = (x1 + x2) // 2 + 5
                y = (y1 + y2) // 2 + 5

                img = putBText(img, tag_text, text_offset_x=x, text_offset_y=y, vspace=5, hspace=5, font=cv2.FONT_HERSHEY_SIMPLEX, font_scale=2, thickness=5, background_RGB=bg_color, text_RGB=font_color, alpha=0.5)
                # alpha: transparency of the background, 0: opaque, 1: transparent
                break

    # print_with_color("image_path:", image_path, "white")
    marked_image_path = image_path.replace(".png", "_mark.png")
    print_with_color(f"The marked image is save in {marked_image_path}", "yellow")
    cv2.imencode('.png', img)[1].tofile(marked_image_path)

    return marked_image_path


