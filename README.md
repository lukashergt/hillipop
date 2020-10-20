**HiLLiPoP: High-L Likelihood Polarized for Planck**

``Hillipop`` is a multifrequency CMB likelihood for Planck data. The likelihood is a spectrum-based Gaussian approximation for cross-correlation spectra from Planck 100, 143 and 217GHz split-frequency maps, with semi-analytic estimates of the Cl covariance matrix based on the data. The cross-spectra are debiased from the effects of the mask and the beam leakage using [``Xpol``](https://gitlab.in2p3.fr/tristram/Xpol) (a generalization to polarization of the algorithm presented in [Tristram et al. 2005](https://arxiv.org/abs/astro-ph/0405575)) before being compared to the model, which includes CMB and foreground residuals.

The model consists of a linear combination of the CMB power spectrum and several foregrounds residuals. These are:
- Galactic dust (estimated directly from the 353 GHz channel);
- the cosmic infrared background (as measured in [Planck Collaboration XXX 2014](https://arxiv.org/abs/1309.0382));
- thermal Sunyaev-Zeldovich emission (based on the Planck measurement reported in [Planck Collaboration XXI 2014](https://arxiv.org/abs/1303.5081));
- kinetic Sunyaev-Zeldovich emission, including homogeneous and patchy reionization components from [Shaw et al. (2012)](https://arxiv.org/abs/1109.0553) and [Battaglia et al. (2013)](https://arxiv.org/abs/1211.2832);
- a tSZ-CIB correlation consistent with both models above; and
- unresolved point sources as a Poisson-like power spectrum with two components (extragalactic radio galaxies and infrared dusty galaxies).

HiLLiPoP has been used as an alternative to the public Planck likelihood in the 2013 and 2015 Planck releases [[Planck Collaboration XV 2014](https://arxiv.org/abs/1303.5075); [Planck Collaboration XI 2016](https://arxiv.org/abs/1507.02704)], and is described in detail in [Couchot et al. (2017)](https://arxiv.org/abs/1609.09730).

It is interfaced with the ``cobaya`` MCMC sampler.