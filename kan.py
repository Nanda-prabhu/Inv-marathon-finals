import cv2
import pytesseract
import re
from pytesseract import Output
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
date_extract_pattern = "[0-9]{1,2}\-[0-9]{1,2}\-[0-9]{4}"
def ocr_from_image(imgsrc):
    img = cv2.imread(imgsrc)
    d = pytesseract.image_to_data(img, output_type=Output.DICT)
    lis=d['text']
    string=" ".join(lis)
    result=re.findall(date_extract_pattern, string)
    n=lis.index('VENUE')+2
    venue=""
    y=[]
    for i in range(3):
        if(lis[n]!=" "):
            y.append(lis[n])
            n+=1
    return (" ".join(y),result[0])
print(ocr_from_image('test2.png'))