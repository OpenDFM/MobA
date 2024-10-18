import sys
import math
from collections import namedtuple
import pdb

sys.path.append('../..')  # Add the path to the project to the sys.path, in case you want to test this script independently
import xml.etree.ElementTree as ET
from moba.utils.utils import print_with_color


class AndroidElement:
    """
    AndroidElement class, representing an element in the Android interface
    """

    def __init__(self, id, bound, attributes, index=0):
        """
        Initializes an instance of the class.
        Args:
            id (int): The resource ID of the agent.
            bound (tuple): The bounding box coordinates of the agent's control.
            attributes (dict): A dictionary containing the non-False attributes of the element.
            num (int, optional): The number of the agent. Defaults to 0.
        """
        self.id = id # The resource ID of the element
        self.index = index  # The number of the element in the list(Starts from 1)
        self.topleft = bound[0]  # The coordinates of the top-left corner of the element (x, y)
        self.bottomright = bound[1]  # The coordinates of the bottom-right corner of the element (x, y)        
        self.attributes = attributes

    @property
    def center(self):
        return [(self.topleft[0] + self.bottomright[0]) / 2, (self.topleft[1] + self.bottomright[1]) / 2]
    
    def __repr__(self):
        return  f"attributes = {self.attributes}\nindex = {self.index}\n"

    @staticmethod
    def parse_xml_bounds(bounds_str):
        """Parse the bounds string into top-left and bottom-right coordinates."""
        bounds = bounds_str[1:-1].split("][")
        x1, y1 = map(int, bounds[0].split(","))
        x2, y2 = map(int, bounds[1].split(","))
        return (x1, y1), (x2, y2)

    @staticmethod
    def from_xml_element(elem, index):
        """Create an AndroidElement instance from an XML element."""
        bounds = AndroidElement.parse_xml_bounds(elem.attrib["bounds"])
        attributes = {k: v for k, v in elem.attrib.items() if v not in ("false", "") and k not in ["index", "resource-id","focusable","enabled"]}
        return AndroidElement(elem.attrib["resource-id"], bounds, attributes, index)

    def get_bbox(self):
        """ return the bounding box (x1,y1),(x2,y2) of the Android element """
        return self.topleft, self.bottomright

    def get_area(self):
        """Return the area of the Android element."""
        x1, y1 = self.topleft
        x2, y2 = self.bottomright
        return (x2 - x1) * (y2 - y1)

    @staticmethod
    def calculate_intersection_area(elem1, elem2):
        """Calculate the intersection area of two elements."""
        (x0,y0), (x1,y1) = elem1.topleft, elem1.bottomright
        (x2,y2), (x3,y3) = elem2.topleft, elem2.bottomright
        x_overlap = max(0, min(x1, x3) - max(x0, x2))
        y_overlap = max(0, min(y1, y3) - max(y0, y2))
        intersection_area = x_overlap * y_overlap
        return intersection_area

    def is_contained_in(self,larger_elem, tolerance=0.35):
        """ return True if self's elem is contained in larger_elem 
        self's area should be smaller than intersection area * (1-tolerance)
        """
        intersection_area = AndroidElement.calculate_intersection_area(self,larger_elem)
        return intersection_area >= (1 - tolerance) * self.get_area()

    def is_interactable(self):
        """Check if an element is interactable."""
        interactable_keys = ["clickable", "long-clickable", "scrollable"]
        return any(self.attributes.get(key, "false") == "true" for key in interactable_keys)

    def contains_text(self):
        """Check if the element contains text or content description."""
        return bool(self.attributes.get("text", "")) or bool(self.attributes.get("content-desc", ""))

    def merge_texts_with(self, elem):
        """ merge elem's content-desc into self's content-desc """
        elem_content_desc = elem.attributes.get("content-desc","")
        self_content_desc = self.attributes.get("content-desc","")
        elem_text = elem.attributes.get("text","")
        self_text = self.attributes.get("text","")
        if (not elem_content_desc) or \
        (self_content_desc and (elem_content_desc in self_content_desc)):
            pass
        else:
            self.attributes["content-desc"] = elem_content_desc + " " + self_content_desc

        if (not elem_text) or (self_text and (elem_text in self_text)):
            pass
        else:
            self.attributes["text"] = elem_text + " " + self_text

def sort_by_coordinate(android_elem_list):
    """ sort the elements by their center coordinates
    from top to bottom, left to right
    set index to -1 if it is not interactable
    """
    sorted_elements = sorted(android_elem_list, key=lambda elem: (elem.center[1], elem.center[0]))
    interact_index = 1
    for elem in sorted_elements:
        if elem.is_interactable():
            elem.index = interact_index
            interact_index += 1
        else:
            elem.index = -1
    return sorted_elements


class ElementProcessor:
    """Processes Android elements extracted from XML."""

    def __init__(self, threshold=50, single_rate=0.25, sum_rate=0.6):
        """ 
        Args:
            threshold (int, optional): The minimum length or width of an element to be considered. 
            single_rate (float, optional): The threshold for IOU to selecting element. 
            sum_rate (float, optional): The threshold for sum-area/area to selecting element. 
            THE larger RATE is, the more element will be selected.
        """
        self.threshold = threshold
        self.single_rate = single_rate
        self.sum_rate = sum_rate
        self.selected_elements = []

    def extract_elements(self, xml_path):
        """Extract and filter elements from the XML file."""
        elements = []
        for _, elem in ET.iterparse(xml_path):
            if elem.attrib.get("enabled","") == "true":
                android_element = AndroidElement.from_xml_element(elem, len(elements))
                (x1, y1),(x2, y2) = android_element.get_bbox()
                if min(x2 - x1, y2 - y1) > self.threshold or \
                (not android_element.is_interactable()):  # Filter small elements
                    elements.append(android_element)
        elements = sorted(elements, key=lambda elem: elem.get_area())# android elements sorted by area
        return elements

    def select_interactable_elements(self, elements):
        """Select interactable elements and filter overlaps."""
        for element in elements:# they have been sorted by area
            if element.is_interactable():
                self._add_element_if_valid(element)

    def select_text_elements(self, elements):
        """Select uninteractable elements that contain text or content-desc."""
        text_elements = []
        for element in elements:
            is_valid = True
            if not element.is_interactable() and element.contains_text():
                for selected_elem in self.selected_elements:
                    if element.is_contained_in(selected_elem):
                        selected_elem.merge_texts_with(element)#merge its text or content-desc
                        # print(f"merge {selected_elem} {element}")#debug
                        is_valid = False
                        break
                if is_valid:
                    text_elements.append(element)
        return text_elements

    def _add_element_if_valid(self, element):
        """Add element if it does not overlap significantly with existing elements."""
        is_valid = True
        sum_overlap_area = 0
        # Check if the overlap between elements is significant.
        for selected_elem in self.selected_elements:
            intersection_area = AndroidElement.calculate_intersection_area(element, selected_elem)
            sum_overlap_area += intersection_area
            if intersection_area > self.single_rate * element.get_area() :
                is_valid = False
                break
        if sum_overlap_area > self.sum_rate * element.get_area():
            is_valid = False

        if is_valid:
            self.selected_elements.append(element)


def extract_elements(xml_path):
    """Main function to extract and process elements.
    set index to -1 if it is not interactable.
    """
    processor = ElementProcessor()
    
    elements = processor.extract_elements(xml_path)

    # First pass: select interactable elements
    processor.select_interactable_elements(elements)

    # Second pass: select text elements
    text_elements = processor.select_text_elements(elements)

    # Combine interactable and text elements
    if text_elements:
        processor.selected_elements.extend(text_elements)

    sorted_selected_elements = sort_by_coordinate(processor.selected_elements)
    # print("Selected elements:" ,[sorted_selected_element for sorted_selected_element in sorted_selected_elements])#debug
    return sorted_selected_elements


def clean_element_list(elem_list, simplify=False):
    """
    Generate the description of the interface in XML format based on elem_list.
    For the attributes dictionary 'attributes', for each key-value pair:
    - If the value is not True, add the key-value pair to the XML description.
    - If the value is True, only add the key.
    Specifically, retain key-value pairs for 'text', 'resource-id', 'class', 'package', 'content-desc', and 'bounds'.
    Return the description in XML format.
    
    Args:
        elem_list (list): List of elements to generate XML description from.
        simplify (bool, optional): If True, do not include the attributes: "resource-id", "class", "package".
    
    Returns:
        str: XML description of the elements.
    """
    xml_description = ""
    for elem in elem_list:
        xml_description += f'<element '
        xml_description += f'index={elem.index} '
        xml_description += f'text="{elem.attributes["text"].strip()}" ' if "text" in elem.attributes else ""
        if not simplify:
            xml_description += f'resource-id="{elem.id}" '
            xml_description += f'class="{elem.attributes["class"]}" ' if "class" in elem.attributes else ""
            # xml_description += f'package="{elem.attributes["package"]}" ' if "package" in elem.attributes else ""
        xml_description += f'content-desc="{elem.attributes["content-desc"]}" ' if "content-desc" in elem.attributes else ""
        xml_description += f'bounds="{elem.attributes["bounds"]}" ' if "bounds" in elem.attributes else ""
        xml_description += f'true_attributes="{",".join([key for key, value in elem.attributes.items() if value == "true"])}" '
        xml_description += '/>\n'
    return xml_description

