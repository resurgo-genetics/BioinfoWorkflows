#!/usr/bin/env python

#python wrapper for deeptools heatmapper
#Copyright 2015 Eric Milliman
#National Institutes of Environmental Health Sciences

#ToDo:  Sanity check direct-passthrough arguments to heatmapper (everything captured by -hf)
#       Test multithreading, conflicting arguments got me stuck in an endless array of child processes
#       Dynamically extract highest intensity values (zMax) to be used across all matrix files
#       multi word passthrough arguments need to be quoted on the command line otherwise they get parsed as seperate arguments

import argparse
import imp
import os
import gzip
import multiprocessing
import signal
import time
import numpy as np
import matplotlib as plt
from deeptools import parserCommon ## contains many of the option flags for heatmapper and profiler
from deeptools import heatmapper ##contains matrix handling routines
hmScript=imp.load_source('hmScript', '/home/millimanej/workspace/deepTools/bin/heatmapper')

parser=argparse.ArgumentParser(description="Batch process matrix files into heatmaps using deepTools heatmapper")
parser.add_argument("-f","--files", nargs='+', help="list of matrices to be processed in batch")
parser.add_argument("--zMax", type=float, help="Maximum value for heatmap intensities and profile (for all matrices)", default=None)
parser.add_argument("--zMin", type=float, help="Minimum value for heatmap intensities and profile (for all matrices)", default=None)
parser.add_argument("--ext", choices=["png","pdf","eps","svg","emf"], default="png", help="Specifies filetype for heatmap image")
parser.add_argument("--prefix", default="", help="string to prepend outfile filenames")
parser.add_argument("--suffix", default="", help="string to append to outfile names")
parser.add_argument("-hh", action="store_true", help="Equivalent to: heatmapper --help")
parser.add_argument("-p",type=int, help="Number of processers to disrisbute heatmapper across", default=1)
parser.add_argument('-hf', help="Extra heatmapper flags: string of flags and values to be passed "
                    "directly to the heatmapper script for all matrix files; Must be last argument "
                    "on command-line. WARNING: There is no sanity check for the flags passed directly to heatmapper. "
                    "Multiword arguments need to be quoted, otherwise they get parsed as seperate arguments by this script. This is a hacky workaround to passthrough "
                    "arguments and may result in your files catching fire..."
                    , nargs=argparse.REMAINDER) ##Hacky pass-through of arguments into heatmapper; there is currently
                    #no sanity check and conflicting parameters causes problems with the multiprocessing.


batch_args=parser.parse_args()

if batch_args.hh:
    parser.print_help()
    print "\n\n"
    args = hmScript.parseArguments(['--help'])
    hmScript.main(args)
    exit

files=batch_args.files
longest=0
lines={}
length={}
zMaxTest=0
zMinTest=0
zMxL={}
zMnL={}

if batch_args.zMax is None:
    zMaxTest=1
if batch_args.zMin is None:
    zMinTest=1

def flattenMatrix(matrixDict):
    """
    concat and flatten
    """
    matrixFlatten = np.concatenate([x for x in matrixDict.values()]).flatten()
    # nans are removed from the flattened array
    return matrixFlatten[np.isnan(matrixFlatten) == False]

def zMx_set(f):
    if zMaxTest:
        zMx=0
        matrixFlatten=None
        content=heatmapper.heatmapper()
        content.readMatrixFile(f)
        matrixFlatten = flattenMatrix(content.matrixDict)
        # try to avoid outliers by using np.percentile
        zMx = np.percentile(matrixFlatten, 98.0)
        print np.shape(content.matrixDict["genes"])[0]
       
    return f, zMx

def zMn_set(f):
    if zMinTest:
        zMn=0
        matrixFlatten=None
        content=heatmapper.heatmapper()
        content.readMatrixFile(f)
        matrixFlatten = flattenMatrix(content.matrixDict)
        zMn = np.percentile(matrixFlatten, 1.0)
    return f, zMn

def heatmap(f):
    outfile = os.path.splitext(f)[0]
    
    def outfileEdit(outfile):
        if batch_args.suffix:
            outfile=outfile+"."+batch_args.suffix    
        if batch_args.prefix:
            outfile=batch_args.prefix+outfile

    if batch_args.suffix:
        outFileEdit(outfile)
   
    outfile=outfile+"."+batch_args.ext
    
    if batch_args.hf:
        argList=batch_args.hf+['-m',f,'-o',outfile]
        args = hmScript.parseArguments(argList)
    else:
        args = hmScript.parseArguments(['-m', f,'-o', outfile])

    args.zMax=batch_args.zMax
    args.zMin=batch_args.zMin
        
    args.heatmapHeight=(float(lines[f])/float(longest))*25
    
    hmScript.main(args)
    
def mp_handler(files):
    pool = multiprocessing.Pool(batch_args.p)
    print "Initialized",
    print batch_args.p,
    print "workers"
    pool.map(heatmap, files)

def file_length(f):
    d={}
    with gzip.open(f, 'rb') as infile:
        content= [line.strip().split("\t") for line in infile.readlines()]
    d[f]=float(len(content))

    return f,float(len(content))
   
def PPResults(alist, func):                                       #Parallel processing
    results={}
    d1={}
    npool = multiprocessing.Pool(int(batch_args.p))    
    res = npool.map_async(func, alist)
    results=(res.get())                                     #results returned in form of a list
    d1=dict(results)
    return d1
 
if __name__ == '__main__':
    
    lines.update(PPResults(files, file_length))
    longest=max(lines.values())
    if zMaxTest:
        zMxL.update(PPResults(files,zMx_set))
        batch_args.zMax=max(zMxL.values())
    if zMinTest:
        zMnL.update(PPResults(files,zMn_set))
        batch_args.zMin=max(zMnL.values())
    mp_handler(files)




   
