import numpy as np
import matplotlib.pyplot as plt
import psana
import time
import os,sys
import skimage.measure as skm
import argparse

# This script does not work and is not compatible with Dragonfly.
# Mask convention used by Dragonfly is 0 for X, 1 for Y, 2 for Z.

def main():
    
    params = parse_input_arguments(sys.argv)

    run_number = params['run_num']
    psocake_mask = params['mask']
    outdir = params['odir']
    detector_name = params['detector']
    experiment_name = params['exp_name']
    print run_number

    tic = time.time()

    # Define the detector object
    ds = psana.DataSource('exp={}:run={}:idx'.format(experiment_name, run_number))
    run = ds.runs().next()    
    times = run.times()
    env = ds.env()
    det = psana.Detector(detector_name, env)

    # Get an example pattern
    idx = 0
    evt = run.event(times[idx])
    example = det.image(evt)

    # Get the shape of the example pattern
    shape = example.shape

    toc = time.time()
    print('It takes {:.5} seconds to finishes the initialization.'.format(toc-tic))


    # Show the mask
    data = np.load(psocake_mask)
    # Assemble the pattern
    assembled_mask = det.image(evt=evt, nda_in=data)

    # Show the pattern
    plt.figure(figsize=(16, 12))
    plt.imshow(assembled_mask)
    plt.colorbar()
    plt.show()

    # Save the mask
    save_address = os.path.join(outdir,'mask_2D.npy')
    np.save(save_address, assembled_mask)
    print('The assembled mask is saved to the following address.')
    print(save_address)

    # Downsample mask
    mask_ds = skm.block_reduce(block_size=(4, 4), func=np.min, image=assembled_mask)

    fig = plt.figure(figsize=(16, 12))
    plt.imshow(mask_ds)
    plt.colorbar()
    plt.show()

    # Save the downsampled mask
    np.save(os.path.join(outdir,'mask_ds.npy'),mask_ds)

def parse_input_arguments(args):
    
    del args[0]
    # use command line argument for experimental run number
    # Ex: python prepare_mask.py -r 182
    parser = argparse.ArgumentParser()
   
    parser.add_argument('-r','--run_num',type=int, help='experimental run number')
    parser.add_argument('-m','--mask',type=str,default=os.getcwd(),help='psocake mask input path')
    parser.add_argument('-o','--odir',type=str,default=os.getcwd(),help='output directory')
    parser.add_argument('-d','--detector',type=str, help='detector name')
    parser.add_argument('-e','--exp_name',type=str, help='experiment name')

    return vars(parser.parse_args())

if __name__ == '__main__':
    main()
