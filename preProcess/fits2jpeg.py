import matplotlib.pyplot as plt
from astropy.visualization import astropy_mpl_style
plt.style.use(astropy_mpl_style)
import img_scale
import sys
import os
from astropy.io import fits

def fits2jpeg(path):
    name = path.split('/')[-1].split('.')[0]+'.jpg'
    lastComponent = path.split('/')[-1]
    dir = path.replace(lastComponent, '')
    dir += name
    try:
        img = fits.getdata(path)##, ext=0)
    except:
        # print('no primary hdu or image data')
        os.remove(path)
        return
    if len([d for d in img.shape]) < 2:
        os.remove(path)
        quit()
    print('fits size', img.shape)
    os.remove(path)
    ax = plt.axes()
    ax.set_facecolor("black")
    plt.figure()
    plt.imshow(img, aspect='equal', cmap='gray')
    plt.grid(False)
    plt.axis('off')
    plt.savefig(dir,edgecolor='black')

# if __name__ == "__main__":
#     fits2jpeg(sys.argv[1])