import h5py 
import numpy as np
import re
import time
import skimage.measure as sm
import os.path
"""
Get dataset info
"""
path = 'data/'

# specific names, change as necessary
h5filename = 'single_hits.h5'
h5filename_ds = 'single_hits_ds.h5'
h5_dataset_name = '/photonConverter/pnccdBack/photonCount'

sh = os.path.join(path,h5filename)
with h5py.File(sh) as h5file:
    keys_all = list(h5file.keys())
    keys_photons = [x for x in keys_all if re.search("photons", x)]
    print(keys_photons)
    
pattern_num_tot = 0
pattern_num_list = []

with h5py.File(sh) as h5file:
    for key in keys_photons:
        dataset = h5file[key]
        pattern_num_tot += dataset.shape[0]
        pattern_num_list.append(dataset.shape[0])

print("There are totally {} patterns in this h5file to convert.".format(pattern_num_tot))


"""
Load the images and downsample them
"""
sh_ds = os.path.join(path,h5filename_ds)

with h5py.File(sh,"r") as ifile:
    # Create a h5 file to save the downsampled image
    with h5py.File(sh_ds,"w") as ofile:

        tic = time.time()
        
        # This is the holder for all the entries
        ds_photons_holder = []
        
        # Get a test pattern
        pattern = np.array(ifile[keys_photons[0]][0])
        pattern_ds = sm.block_reduce(pattern, block_size=(4,4), func=np.sum)
               
        # Get pattern shape
        ds_shape = pattern_ds.shape
        
        # Get a global counter
        counter = 0
        
        # Loop through all the keys
        for idx in range(len(keys_photons)):
            
            key = keys_photons[idx]
            print("Current key is: ",key)
            print("There are {} patterns in this dataset".format(pattern_num_list[idx]))
            
            # Create a holder 
            local_holder = np.zeros((pattern_num_list[idx],) + ds_shape, dtype=np.int64)
            
            # Loop through all the data in this data entry
            for n in range(pattern_num_list[idx]):
                
                # Get the pattern
                pattern = np.array(ifile[key][n])

                # Downsample and save to the holder
                local_holder[n] = sm.block_reduce(pattern, block_size=(4,4), func=np.sum)
                
                # Increase the counter
                counter += 1
                if np.mod(counter , 100) ==0:
                    toc = time.time()
                    print("{} seconds per pattern".format((toc-tic)/counter))
            
            # Copy the holder to the global holder
            ds_photons_holder.append(np.copy(local_holder))
            
        # Stack all the patterns together 
        ds_photons_together = np.concatenate(ds_photons_holder, axis=0)
        # Save to the new h5 file
        ds2 = np.swapaxes(ds_photons_together,1,2)
        ofile.create_dataset(h5_dataset_name, data=ds2)
