import cv2 as cv
import numpy as np
import scipy as sp

def gaussianSubtract(source, maxPixels = 8):
    # Using the gaussian subtraction method to find the blobs of stars
    shifted = [cv.blur(source, (i, i)) for i in range(2, maxPixels)]
    subtracted = [cv.subtract(source, b) for b in shifted]
    
    # Now we get some local maxima across the image, gather them 
    # and compare the same position for each image in the subtracted stack to find its largest blob radius
    return shifted, subtracted
