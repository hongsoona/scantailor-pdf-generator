from PIL import Image
import numpy as np
import img2pdf
from pypdf import PdfReader, PdfWriter
import os
from shutil import rmtree
from tqdm import tqdm

# Get information of image file, including width, height, and dpi
def get_file_info(file_path):
    im = Image.open(file_path)
    width, height = im.size
    dpi = int(im.info['dpi'][0])
    return width, height, dpi

# Convert unit from pixel to point(1/72 inch), which is used in PDF file
def pixel_to_pdf(x, dpi):
    x = x / dpi * 72
    return x

# Get coordinate of bounding box of each object in image
def get_coordinate_of_bounding_box(input_path):    
    im = Image.open(input_path)
    np_im = np.asarray(im)
    np_im = np.pad(np_im, ((1,1), (1,1)), 'constant', constant_values=(255,255)) # padding 1px
    r = []
    while True:
        x_start, y_start = np.unravel_index(np.argmin(np_im), np_im.shape)
        if not x_start and not y_start:
            break
        row = np_im[x_start]
        y_end = np.argwhere(row[1:] != row[:-1])[1][0] + 1
        col = np_im[:, y_start]
        x_end = np.argwhere(col[1:] != col[:-1])[1][0] + 1
        np_im[x_start:x_end, y_start:y_end] = 255
        coord = (y_start - 1, x_start - 1, y_end - 1, x_end - 1)
        r.append(coord)
    return r

# Crop image by list of coordinates
def crop_image_by_list(input_path, coord_list, output_path, dpi=600):
    im = Image.open(input_path)
    for i, coord in enumerate(coord_list):
        cropped_im = im.crop(coord)
        cropped_im.save(f'{output_path}{i}.pdf', format='PDF', quality=80, dpi=(dpi, dpi))

# Process one file
def process_one_file(filename):
    page_name = filename.split('.')[0]
    page_width, page_height, dpi = get_file_info(f'foreground/{page_name}.tif')
    os.makedirs(f'temp/{page_name}', exist_ok=True)

    # converting foreground image
    with open(f'temp/{page_name}.pdf', 'wb') as f:
        f.write(img2pdf.convert(f'foreground/{page_name}.tif'))

    # cropping background image
    l = get_coordinate_of_bounding_box(f'original_background/{page_name}.tif')
    crop_image_by_list(f'background/{page_name}.tif', l, output_path=f'temp/{page_name}/', dpi=dpi)

    # merging background and foreground
    base_pdf = PdfReader(f'temp/{page_name}.pdf')
    for idx, coord in enumerate(l):
        add_pdf = PdfReader(f'temp/{page_name}/{idx}.pdf')
        base_pdf.pages[0].merge_translated_page(add_pdf.pages[0], pixel_to_pdf(coord[0], dpi=dpi), pixel_to_pdf(page_height - coord[3], dpi=dpi))
    
    updated_pdf = PdfWriter()
    updated_pdf.add_page(base_pdf.pages[0])
    updated_pdf.write(f'{page_name}.pdf')
    updated_pdf.close()
    try:
        rmtree(f'temp/{page_name}')
    except:
        pass

def main():
    os.makedirs('temp', exist_ok=True)

    # get page list
    r = os.listdir('foreground')
    r = [i for i in r if i.endswith('.tif')]
    for i in tqdm(r):
        process_one_file(i)
    merger = PdfWriter()
    r = [f'{i.split(".")[0]}.pdf' for i in r]
    for i in tqdm(r):
        merger.add_page(PdfReader(i).pages[0])
    merger.write('output.pdf')
    merger.close()
    try:
        rmtree(f'temp')
    except:
        pass
    for i in r:
        try:
            os.remove(i)
        except:
            pass
    
if __name__ == '__main__':
    main()
