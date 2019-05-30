import numpy as np
import h5py as h5
import argparse
import os,sys

def main():
    
    params = get_input_arguments(sys.argv)
    path = params['path']

    run_num_list=['182','183','184','185','186','188','190','191','192','193','194','196','197']
    #path = "/reg/d/psdm/cxi/cxitut13/res/marcgri/single_hits/data/"

    with h5.File(path + "/single_hits.h5",'w') as h5file:
       for l in range(len(run_num_list)):
        
           # load_photons
           data = np.load(path+ 'photons_{}.npy'.format(run_num_list[l]))
           # Check data shape
           print("photons shape",data.shape)
           # Save data to h5 dataset with chunks 
           h5file.create_dataset("photons_{}".format(run_num_list[l]), data=data, chunks = True)
        
           # load_adus
           data = np.load(path+'ADUs_{}.npy'.format(run_num_list[l]))
           # Check data shape
           print("ADUs shape",data.shape)
           # Save data to h5 dataset with chunks 
           h5file.create_dataset("ADUs_{}".format(run_num_list[l]), data=data, chunks = True)
        
           # load_mask
           data = np.load(path+'mask_2d_{}.npy'.format(run_num_list[l]))
           # Check data shape
           print("Mask shape",data.shape)
           # Save data to h5 dataset with chunks 
           h5file.create_dataset("mask_{}".format(run_num_list[l]), data=data, chunks = True)

def parse_input_arguments(args):

    del args[0]
    parser = argparse.ArgumentParser()
    parser.add_argument('-p','--path',type=str,default=os.getcwd(), help='path to single hits data arrays')
    
    return vars(parser.parse_args(args))
