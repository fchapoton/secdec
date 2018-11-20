from __future__ import print_function
from pySecDec.integral_interface import IntegralLibrary
import sympy as sp

# load c++ library
pentabox = IntegralLibrary('pentabox_fin/pentabox_fin_pylink.so')

# choose integrator
pentabox.use_Qmc(transform='korobov3',verbosity=3,minn=10**8,maxeval=1,fitfunction='polysingular')

# integrate non-Euclidean point;
s12, s23, s34, s45, s51 = [5.,-4.,2.,-6.,3.]
str_integral_without_prefactor, str_prefactor, str_integral_with_prefactor = pentabox([s12,s23,s34,s45,s51],deformation_parameters_maximum=0.1)

# convert complex numbers from c++ to sympy notation
str_integral_with_prefactor = str_integral_with_prefactor.replace(',','+I*')
str_prefactor = str_prefactor.replace(',','+I*')
str_integral_without_prefactor = str_integral_without_prefactor.replace(',','+I*')

# convert result to sympy expressions
integral_with_prefactor = sp.sympify(str_integral_with_prefactor.replace('+/-','*value+error*'))
integral_with_prefactor_err = sp.sympify(str_integral_with_prefactor.replace('+/-','*value+error*'))
prefactor = sp.sympify(str_prefactor)
integral_without_prefactor = sp.sympify(str_integral_without_prefactor.replace('+/-','*value+error*'))
integral_without_prefactor_err = sp.sympify(str_integral_without_prefactor.replace('+/-','*value+error*'))

# numerical result
print('eps^0:', integral_with_prefactor.coeff('eps',0).coeff('value'), '+/- (', integral_with_prefactor_err.coeff('eps',0).coeff('error'), ')')

# result: eps^0: -0.019823659271430049 - 0.0341514491102190842*I +/- ( 8.60492332244851086e-9 + 7.45328059295334506e-9*I )
