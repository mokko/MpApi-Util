from PIL import Image, ExifTags
from PIL.ExifTags import Base as ExifBase

# https://stackoverflow.com/questions/4764932/
test_files = "test.tif"


def tast_exif():
    with Image.open("VII a 62.tif") as img:
        img_data = img.getexif()
    if img_data is None:
        print("Sorry, no exif")
    else:
        assert img_data[ExifBase.Artist.value] == "Claudia Obrocki"
        # for key, val in img_data.items():
        # if key in ExifTags.TAGS:
        # print(f'{ExifTags.TAGS[key]}:{val}')
        # print(f"Artist:{img_data[ExifBase.Artist.value]}")
