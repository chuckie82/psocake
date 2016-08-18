import psana
import numpy as np
from mpidata import mpidata 
import PeakFinder as pf

from mpi4py import MPI
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

def runclient(args):
    ds = psana.DataSource("exp="+args.exp+":run="+str(args.run)+':idx')
    run = ds.runs().next()
    env = ds.env()
    times = run.times()
    d = psana.Detector(args.det)
    #hybridGain = d.gain_mask(gain=6.85)

    for nevent in np.arange(len(times)):
        if nevent == args.noe : break
        if nevent%(size-1) != rank-1: continue # different ranks look at different events
        try:
            evt = run.event(times[nevent])
            detarr = d.calib(evt) #* d.gain(evt)
            #if hybridGain is not None:  # None if not cspad or cspad2x2
            #    detarr *= hybridGain
        except:
            print '*** failed to get img: ', rank, nevent
            continue

        if detarr is None:
            continue

        # Initialize hit finding
        if not hasattr(d,'peakFinder'):
            if args.algorithm == 1:
                d.peakFinder = pf.PeakFinder(env.experiment(),evt.run(),args.det,evt,d,
                                          args.algorithm, args.alg_npix_min,
                                          args.alg_npix_max, args.alg_amax_thr,
                                          args.alg_atot_thr, args.alg_son_min,
                                          alg1_thr_low=args.alg1_thr_low, alg1_thr_high=args.alg1_thr_high,
                                          alg1_radius=args.alg1_radius, alg1_dr=args.alg1_dr,
                                          streakMask_on=args.streakMask_on,
                                          streakMask_sigma=args.streakMask_sigma,
                                          streakMask_width=args.streakMask_width,
                                          userMask_path=args.userMask_path,
                                          psanaMask_on=args.psanaMask_on,
                                          psanaMask_calib=args.psanaMask_calib,
                                          psanaMask_status=args.psanaMask_status,
                                          psanaMask_edges=args.psanaMask_edges,
                                          psanaMask_central=args.psanaMask_central,
                                          psanaMask_unbond=args.psanaMask_unbond,
                                          psanaMask_unbondnrs=args.psanaMask_unbondnrs)
            elif args.algorithm == 3:
                d.peakFinder = pf.PeakFinder(env.experiment(),evt.run(),args.det,evt,d,
                                          args.algorithm, args.alg_npix_min,
                                          args.alg_npix_max, args.alg_amax_thr,
                                          args.alg_atot_thr, args.alg_son_min,
                                          alg3_rank=args.alg3_rank, alg3_r0=args.alg3_r0,
                                          alg3_dr=args.alg3_dr,
                                          streakMask_on=args.streakMask_on,
                                          streakMask_sigma=args.streakMask_sigma,
                                          streakMask_width=args.streakMask_width,
                                          userMask_path=args.userMask_path,
                                          psanaMask_on=args.psanaMask_on,
                                          psanaMask_calib=args.psanaMask_calib,
                                          psanaMask_status=args.psanaMask_status,
                                          psanaMask_edges=args.psanaMask_edges,
                                          psanaMask_central=args.psanaMask_central,
                                          psanaMask_unbond=args.psanaMask_unbond,
                                          psanaMask_unbondnrs=args.psanaMask_unbondnrs)
            elif args.algorithm == 4:
                d.peakFinder = pf.PeakFinder(env.experiment(),evt.run(),args.det,evt,d,
                                          args.algorithm, args.alg_npix_min,
                                          args.alg_npix_max, args.alg_amax_thr,
                                          args.alg_atot_thr, args.alg_son_min,
                                          alg4_thr_low=args.alg4_thr_low, alg4_thr_high=args.alg4_thr_high,
                                          alg4_rank=args.alg4_rank, alg4_r0=args.alg4_r0,
                                          alg4_dr=args.alg4_dr,
                                          streakMask_on=args.streakMask_on,
                                          streakMask_sigma=args.streakMask_sigma,
                                          streakMask_width=args.streakMask_width,
                                          userMask_path=args.userMask_path,
                                          psanaMask_on=args.psanaMask_on,
                                          psanaMask_calib=args.psanaMask_calib,
                                          psanaMask_status=args.psanaMask_status,
                                          psanaMask_edges=args.psanaMask_edges,
                                          psanaMask_central=args.psanaMask_central,
                                          psanaMask_unbond=args.psanaMask_unbond,
                                          psanaMask_unbondnrs=args.psanaMask_unbondnrs)
        d.peakFinder.findPeaks(detarr,evt)
        md=mpidata()
        md.addarray('peaks',d.peakFinder.peaks)
        md.small.eventNum = nevent
        md.small.maxRes = d.peakFinder.maxRes
        md.small.powder = 0
        md.send() # send mpi data object to master when desired
    # At the end of the run, send the powder of hits and misses
    md = mpidata()
    md.small.powder = 1
    md.addarray('powderHits', d.peakFinder.powderHits)
    md.addarray('powderMisses', d.peakFinder.powderMisses)
    md.send()
    md.endrun()