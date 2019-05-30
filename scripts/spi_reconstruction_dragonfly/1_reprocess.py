import h5py
import psana
import numpy as np
import time
import argparse
import os,sys

def main():
    
    params = parse_input_arguments(sys.argv)
    exp_data_path = params['idir']
    outdir = params['odir']



    run_num_list=['182','183','184','185','186','188','190','191','192','193','194','196','197']

    #outdir = "/reg/d/psdm/cxi/cxitut13/res/marcgri/single_hits/data/"

    for fileInd in range(len(run_num_list)):

        t1=time.time()
    
        # Open files and get data
        run_num=run_num_list[fileInd]

        #   f=h5py.File('/reg/d/psdm/amo/amo86615/res/yoon82/data/amo86615_'+run_num+'_PR772_single.h5')
        f = h5py.File(exp_data_path + '_' + run_num + '_PR772_single.h5')
        ts = f['/photonConverter/eventTime'].value
        print(ts)
        fid = f['/photonConverter/fiducials'].value
        ds = psana.DataSource('exp=amo86615:run='+run_num+':idx')
        run = ds.runs().next()    
        times = run.times()
        env = ds.env()
        det = psana.Detector('pnccdBack', env)
        et = psana.EventTime(int(ts[0]),fid[0])
        evt = run.event(et)
        example = det.image(evt)
        shape = example.shape
    
        ## get mask and save mask
        mask_calibOn = True
        mask_statusOn = True
        mask_edgesOn = True
        mask_centralOn = True
        mask_unbondOn = True
        mask_unbondnrsOn = True

        psanaMask = det.mask(evt, calib=mask_calibOn, status=mask_statusOn, 
                             edges=mask_edgesOn, central=mask_centralOn,
                             unbond=mask_unbondOn, unbondnbrs=mask_unbondnrsOn)
        mask = det.image(evt, psanaMask)
        np.save(outdir+'mask_2d_%s.npy'%(run_num_list[fileInd]),mask)
        np.save(outdir+'mask_stack_%s.npy'%(run_num_list[fileInd]),psanaMask)
    
        # Collect photons patterns
        photons = np.zeros((len(ts),shape[0],shape[1]))
        ADUs = np.zeros((len(ts),shape[0],shape[1]))
        print("There are totally %d patterns to process." % len(ts))
    
        for num in range(len(ts)):
           print("This is the %d th pattern"%num )
           et = psana.EventTime(int(ts[num]),fid[num])
           evt = run.event(et)
        
           photon_stack = det.photons(evt, adu_per_photon=130)
           photons[num,:,:] = det.image(evt, photon_stack)   
        
           adu = det.image(evt)
           ADUs[num,:,:] = adu
        
        np.save(outdir+'photons_%s.npy'%(run_num_list[fileInd]),photons)
        np.save(outdir+'ADUs_%s.npy'%(run_num_list[fileInd]),ADUs)
    
        ## close files
        f.close()
        print 'Finished %s' % run_num    
        t2 = time.time()
        print ('total time usage: %f'%(t2-t1))

def parse_input_arguments(args):
    
    del args[0]
    parser = argparse.ArgumentParser()
    parser.add_argument('-i','--idir',type=str,default=os.getcwd(),help='directory for experimental run data, current working directory unless specified')
    parser.add_argument('-o','--odir',type=str,default=os.getcwd(),help='single hits data, directory for output, current working directory unless specified')
   
    return vars(parser.parse_args(args))

if __name__ == '__main__':
    main()
