#
#HILLIPOP tools library
#
#Sep 2020   - M. Tristram -
import numpy as np
from numpy.linalg import *
import astropy.io.fits as fits
import scipy.ndimage as nd

tagnames = ['TT','EE','BB','TE','TB','EB']

from foregrounds_v3 import *


#------------------------------------------------------------------------------------------------
#Hillipop with foregounds
#------------------------------------------------------------------------------------------------
class hillipop(object):
    """
    High-L Likelihood for Polarized Planck
    Spectra-based Gaussian-approximated likelihood with foreground models for cross-correlation spectra from Planck 100, 143 and 217GHz split-frequency maps
    """
    def __init__( self, paramfile, verbose=False):
        '''
        init Hillipop likelihood
        
        Parameters
        ----------
        paramfile: string
            parameter file containing likelihood information
        '''
        
        pars = read_parameter( paramfile)
        self.verbose = verbose
        self._modenames = ["TT","EE","BB","TE","ET"]
        self.nmap = int(pars["map"])
        self._set_modes( pars)
        self.fqs = self._get_freqs( pars)
        self.nfreq = len(np.unique(self.fqs))
        self.nxfreq = self.nfreq*(self.nfreq+1)/2
        self.nxspec = self.nmap*(self.nmap-1)/2
        self._set_lists()
        
        #Multipole ranges
        if self.verbose: print( "Multipole Ranges")
        self._set_multipole_ranges( pars['MultipolesRange'])        

        #Data
        if self.verbose: print( "Read Data")
        self.dldata = self._read_dl_xspectra( pars['XSpectra'])

        #Weights
        if self.verbose: print( "Read Weights")
        self.dlweight = self._read_dl_xerrors( pars['XSpectraErrors'])

        #Inverted Covariance matrix
        if self.verbose: print( "Read covmat")
        self.invkll = self._read_invcovmatrix( pars['CovMatrix'])

        #Nuisances
        self.parname = ["Aplanck"]
        for m in range(self.nmap): self.parname.append( "c%d" % m)

        #Init foregrounds TT
        if self.isTT:
            self.fgsTT = []
            self.fgsTT.append( ps_radio( self.lmax, self.fqs, self.parname))
            self.fgsTT.append( ps_dusty( self.lmax, self.fqs, self.parname))
            if "Dust" in pars.keys():
                self.fgsTT.append( dust_model( self.lmax, self.fqs, self.parname, pars["Dust"], mode="TT"))
            if "SZ" in pars.keys():
                self.fgsTT.append( sz_model( self.lmax, self.fqs, self.parname, pars["SZ"]))
            if "CIB" in pars.keys():
                self.fgsTT.append( cib_model( self.lmax, self.fqs, self.parname, pars["CIB"]))
            if "kSZ" in pars.keys():
                self.fgsTT.append( ksz_model( self.lmax, self.fqs, self.parname, pars["kSZ"]))
            if "SZxCIB" in pars.keys():
                self.fgsTT.append( szxcib_model( self.lmax, self.fqs, self.parname, pars["SZxCIB"]))
    
        #Init foregrounds EE
        if self.isEE:
            self.fgsEE = []
            if "Dust" in pars.keys():
                self.fgsEE.append( dust_model( self.lmax, self.fqs, self.parname, pars["Dust"], mode="EE"))

        #Init foregrounds TE
        if self.isTE:
            self.fgsTE = []
            if "Dust" in pars.keys():
                self.fgsTE.append( dust_model( self.lmax, self.fqs, self.parname, pars["Dust"], mode="TE"))
        if self.isET:
            self.fgsET = []
            if "Dust" in pars.keys():
                self.fgsET.append( dust_model( self.lmax, self.fqs, self.parname, pars["Dust"], mode="ET"))


    def _set_modes(self,pars):
        self.isTT = True if int(pars["TT"]) == 1 else False
        self.isEE = True if int(pars["EE"]) == 1 else False
        self.isTE = True if int(pars["TE"]) == 1 else False
        self.isET = True if int(pars["ET"]) == 1 else False
    
    def _get_freqs(self,pars):
        fqs = []
        for f in range(self.nmap):
            fqs.append( int(pars["freq%d"%f]))
        return( fqs)

    def _set_lists(self):
        self.xspec2map = []
        list_xfq = []
        for m1 in range(self.nmap):
            for m2 in range(m1+1,self.nmap):
                self.xspec2map.append( (m1,m2))
        
        list_fqs = []
        for f1 in range(self.nfreq):
            for f2 in range(f1, self.nfreq):
                list_fqs.append( (f1,f2))
        
        freqs = list(np.unique(self.fqs))
        self.xspec2xfreq = []
        for m1 in range(self.nmap):
            for m2 in range(m1+1,self.nmap):
                f1 = freqs.index(self.fqs[m1])
                f2 = freqs.index(self.fqs[m2])
                self.xspec2xfreq.append( list_fqs.index((f1,f2)))
    
    def _set_multipole_ranges( self, filename):
        '''
        Return the (lmin,lmax) for each cross-spectra for each mode (TT,EE,BB,TE)
        array(nmode,nxspec)
        '''
        if self.verbose: print( filename)
        
        self.lmins = []
        self.lmaxs = []
        for m in range(4):
            data = fits.getdata( filename, m+1)
            self.lmins.append( np.array(data.field(0),int))
            self.lmaxs.append( np.array(data.field(1),int))
        self.lmax = max([max(l) for l in self.lmaxs])
    
    def _read_dl_xspectra( self, filename):
        '''
        Read xspectra from Xpol [Dl in K^2]
        Output: Dl in muK^2
        '''
        if self.verbose: print( filename)
        
        dldata = []
        for m1 in range(self.nmap):
            for m2 in range(m1+1,self.nmap):
                tmpcl = []
                #TT EE BB TE ET
                for hdu in [1,2,3,4,4]:
                    data = fits.getdata( "%s_%d_%d.fits" % (filename,m1,m2), hdu)
                    ell = np.array(data.field(0),int)
                    datacl = np.zeros( max(ell)+1)
                    datacl[ell] = data.field(1) * 1e12
                    tmpcl.append( datacl[:self.lmax+1])
                
                dldata.append(tmpcl)
        return( np.transpose( np.array(dldata), ( 1,0,2)))
    
    def _read_dl_xerrors( self, filename):
        '''
        Read xspectra errors from Xpol [Dl in K^2]
        Output: Dl 1/sigma_l^2 in muK^-4
        '''
        if self.verbose: print( filename)
        
        dlweight = []
        for m1 in range(self.nmap):
            for m2 in range(m1+1,self.nmap):
                tmpcl = []
                #TT EE BB TE ET
                for hdu in [1,2,3,4,4]:
                    data = fits.getdata( "%s_%d_%d.fits" % (filename,m1,m2), hdu)
                    ell = np.array(data.field(0),int)
                    datacl = np.zeros( max(ell)+1)
                    datacl[ell] = data.field(2) * 1e12
                    datacl[datacl == 0] = np.inf
                    tmpcl.append( 1./datacl[:self.lmax+1]**2)
                
                dlweight.append(tmpcl)
        return( np.transpose( np.array(dlweight), (1,0,2)))
    
    def _read_invcovmatrix( self, filename):        
        '''
        Read xspectra inverse covmatrix from Xpol [Dl in K^-4]
        Output: invkll [Dl in muK^-4]
        '''
        ext = "_"
        if self.isTT: ext += "TT"
        if self.isEE: ext += "EE"
        if self.isTE: ext += "TE"
        if self.isET: ext += "ET"
        if self.verbose: print( filename+ext+".fits")
        
        #count dim
        nell = 0
        if self.isTT:
            nells = self.lmaxs[0]-self.lmins[0]+1
            nell += sum([nells[self.xspec2xfreq.index(k)] for k in range(self.nxfreq)])
        if self.isEE:
            nells = self.lmaxs[1]-self.lmins[1]+1
            nell += sum([nells[self.xspec2xfreq.index(k)] for k in range(self.nxfreq)])
        if self.isTE:
            nells = self.lmaxs[2]-self.lmins[2]+1
            nell += sum([nells[self.xspec2xfreq.index(k)] for k in range(self.nxfreq)])
        if self.isET:
            nells = self.lmaxs[3]-self.lmins[3]+1
            nell += sum([nells[self.xspec2xfreq.index(k)] for k in range(self.nxfreq)])
        
        #read
        data = fits.getdata( filename+ext+".fits").field(0)
        nel = int(np.sqrt(len(data)))
        data = data.reshape( (nel,nel))/1e24  #muK^-4
        
        if nel != nell:
            raise ValueError('Incoherent covariance matrix')
        
        return( data)
    
    def _select_spectra( self, cl, mode=0):
        '''
        Cut spectra given Multipole Ranges and flatten
        '''
        acl = np.asarray(cl)
        xl = []
        for xf in range(self.nxfreq):
            lmin = self.lmins[mode][self.xspec2xfreq.index(xf)]
            lmax = self.lmaxs[mode][self.xspec2xfreq.index(xf)]
            xl = xl+list(acl[xf,lmin:lmax+1])
        return( np.array(xl))
    
    def _xspectra_to_xfreq( self, cl, weight):
        '''
        Average cross-spectra per cross-frequency
        '''
        xcl = np.zeros( (self.nxfreq, self.lmax+1))
        xw8 = np.zeros( (self.nxfreq, self.lmax+1))
        for xs in range(self.nxspec):
            xcl[self.xspec2xfreq[xs]] += weight[xs] * cl[xs]
            xw8[self.xspec2xfreq[xs]] += weight[xs]
        
        xw8[xw8 == 0] = np.inf
        return( xcl / xw8)
    
    def _compute_residuals( self, pars, cl_boltz):
        #cl_boltz from Boltzmann (Cl in K^2)
        lth = np.arange( self.lmax+1)
        dlth = np.asarray(cl_boltz)[:,lth] * (lth*(lth+1)/2./np.pi * 1e12) #Dl in muK^2
        
        #nuisances
        cal = []
        for m1 in range(self.nmap):
            for m2 in range(m1+1,self.nmap):
                cal.append( pars["Aplanck"]*pars["Aplanck"] * (1.+ pars["c%d" % m1] + pars["c%d" % m2]))
        
        #TT
        if self.isTT:
            dlmodel = [dlth[0]]*self.nxspec
            for fg in self.fgsTT:
                dlmodel += fg.compute_dl( pars)
            
            #Compute Rl = Dl - Dlth
            Rspec = [self.dldata[0][xs] - cal[xs]*dlmodel[xs] for xs in range(self.nxspec)]
            Rl = self._xspectra_to_xfreq( Rspec, self.dlweight[0])
#            Rl = Rspec
        return( Rl)
    
    def compute_likelihood( self, pars, cl_boltz):
        '''
        Compute likelihood from model out of Boltzmann code
        Units: Dl in muK^2
        
        Parameters
        ----------
        pars: dict
              parameter values
        cl_boltz: array or arr2d
              CMB power spectrum (Cl in K^2)
        
        Returns
        -------
        lnL: float
            Log likelihood for the given parameters -2ln(L)
        '''
        
        #cl_boltz from Boltzmann (Cl in K^2)
        lth = np.arange( self.lmax+1)
        dlth = np.asarray(cl_boltz[:,lth]) * (lth*(lth+1)/2./np.pi * 1e12) #Dl in muK^2
        
        #nuisances
        cal = []
        for m1 in range(self.nmap):
            for m2 in range(m1+1,self.nmap):
                cal.append( pars["Aplanck"]*pars["Aplanck"] * (1.+pars["c%d" % m1]) * (1.+pars["c%d" % m2]))
        
        #TT
        if self.isTT:
            dlmodel = [dlth[0]]*self.nxspec
            for fg in self.fgsTT:
                dlmodel += fg.compute_dl( pars)
            
            #Compute Rl = Dl - Dlth
            Rl = self._xspectra_to_xfreq( [self.dldata[0][xs] - cal[xs]*dlmodel[xs] for xs in range(self.nxspec)], self.dlweight[0])
            Xl = self._select_spectra( Rl)
        
        return( Xl.dot(self.invkll).dot(Xl))

#------------------------------------------------------------------------------------------------

















#------------------------------------------------------------------------------------------------
#Tools
#------------------------------------------------------------------------------------------------
def read_parameter( filename):
    d = {}
    FILE = open(filename)
    for line in FILE:
        name, value = line.split("=")
        value = value.strip()
        if " " in value:
            value = map(str, value.split())
        else:
            value = str(value)
        d[name.strip()] = value
#        setattr(self, d[name], value)
    return(d)

def list_cross( nmap):
    return( [(i,j) for i in range(0,nmap) for j in range(i+1,nmap)])



def create_bin_file( filename, lbinTT, lbinEE, lbinBB, lbinTE, lbinET):
    """
    lbin = [(lmin,lmax)] for each 15 cross-spectra
    """
    h = fits.Header()
    hdu = [fits.PrimaryHDU(header=h)]

    def fits_layer( lbin):
        h = fits.Header()
        lmin = np.array([l[0] for l in lbin])
        lmax = np.array([l[1] for l in lbin])
        c1 = fits.Column(name='LMIN', array=lmin, format='1D')
        c2 = fits.Column(name='LMAX', array=lmax, format='1D')
        return(fits.BinTableHDU.from_columns([c1,c2],header=h))

    hdu.append(fits_layer( lbinTT))
    hdu.append(fits_layer( lbinEE))
    hdu.append(fits_layer( lbinBB))
    hdu.append(fits_layer( lbinTE))
    hdu.append(fits_layer( lbinET))

    hdulist = fits.HDUList(hdu)
    hdulist.writeto( filename, overwrite=True)



#smooth cls before Cov computation
def SG( l, cl, nsm=5, lcut=0):
    clSG = np.copy(cl)
    
    #gauss filter
    if lcut < 2*nsm:
        shift=0
    else:
        shift=2*nsm
    
    data = nd.gaussian_filter1d( clSG[max(0,lcut-shift):], nsm)
    clSG[lcut:] = data[shift:]
    
    return clSG


def convert_to_stdev(sigma):
    """
    Given a grid of likelihood values, convert them to cumulative
    standard deviation.  This is useful for drawing contours from a
    grid of likelihoods.
    """
#    sigma = np.exp(-logL+np.max(logL))

    shape = sigma.shape
    sigma = sigma.ravel()

    # obtain the indices to sort and unsort the flattened array
    i_sort = np.argsort(sigma)[::-1]
    i_unsort = np.argsort(i_sort)

    sigma_cumsum = sigma[i_sort].cumsum()
    sigma_cumsum /= sigma_cumsum[-1]
    
    return sigma_cumsum[i_unsort].reshape(shape)


def ctr_level(histo2d, lvl):
    """
    Extract the contours for the 2d plots
    """
    
    h = histo2d.flatten()*1.
    h.sort()
    cum_h = np.cumsum(h[::-1])
    cum_h /= cum_h[-1]
    
    alvl = np.searchsorted(cum_h, lvl)
    clist = h[-alvl]
    
    return clist

#------------------------------------------------------------------------------------------------







#------------------------------------------------------------------------------------------------
#Binning
#------------------------------------------------------------------------------------------------
class Bins(object):
    """
        lmins : list of integers
            Lower bound of the bins
        lmaxs : list of integers
            Upper bound of the bins
    """
    def __init__( self, lmins, lmaxs):
        if not(len(lmins) == len(lmaxs)):
            raise ValueError('Incoherent inputs')

        lmins = np.asarray( lmins)
        lmaxs = np.asarray( lmaxs)
        cutfirst = np.logical_and(lmaxs>=2 ,lmins>=2)
        self.lmins = lmins[cutfirst]
        self.lmaxs = lmaxs[cutfirst]
        
        self._derive_ext()
    
    @classmethod
    def fromdeltal( cls, lmin, lmax, delta_ell):
        nbins = (lmax - lmin + 1) // delta_ell
        lmins = lmin + np.arange(nbins) * delta_ell
        lmaxs = lmins + delta_ell-1
        return( cls( lmins, lmaxs))

    def _derive_ext( self):
        for l1,l2 in zip(self.lmins,self.lmaxs):
            if( l1>l2):
                raise ValueError( "Incoherent inputs")
        self.lmin = min(self.lmins)
        self.lmax = max(self.lmaxs)
        if self.lmin < 1:
            raise ValueError('Input lmin is less than 1.')
        if self.lmax < self.lmin:
            raise ValueError('Input lmax is less than lmin.')
        
        self.nbins = len(self.lmins)
        self.lbin = (self.lmins + self.lmaxs) / 2.
        self.dl   = (self.lmaxs - self.lmins + 1)

    def bins(self):
        return (self.lmins,self.lmaxs)
    
    def cut_binning(self, lmin, lmax):
        sel = np.where( (self.lmins >= lmin) & (self.lmaxs <= lmax) )[0]
        self.lmins = self.lmins[sel]
        self.lmaxs = self.lmaxs[sel]
        self._derive_ext()
    
    def _bin_operators(self,Dl=False,cov=False):
        if Dl:
            ell2 = np.arange(self.lmax+1)
            ell2 = ell2 * (ell2 + 1) / (2 * np.pi)
        else:
            ell2 = np.ones(self.lmax+1)
        p = np.zeros((self.nbins, self.lmax+1))
        q = np.zeros((self.lmax+1, self.nbins))
        
        for b, (a, z) in enumerate(zip(self.lmins, self.lmaxs)):
            dl = (z-a+1)
            p[b, a:z+1] = ell2[a:z+1] / dl
            if cov:
                q[a:z+1, b] = 1 / ell2[a:z+1] / dl
            else:
                q[a:z+1, b] = 1 / ell2[a:z+1]
        
        return p, q

    def bin_spectra(self, spectra, Dl=False):
        """
        Average spectra in bins specified by lmin, lmax and delta_ell,
        weighted by `l(l+1)/2pi`.
        Return Cb
        """
        spectra = np.asarray(spectra)
        minlmax = min([spectra.shape[-1] - 1,self.lmax])
#        if Dl:
#            fact_binned = 1.
#        else:
#            fact_binned = 2 * np.pi / (self.lbin * (self.lbin + 1))
        
        _p, _q = self._bin_operators()
        return np.dot(spectra[..., :minlmax+1], _p.T[:minlmax+1,...]) #* fact_binned


