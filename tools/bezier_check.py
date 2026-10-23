# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Whole-curve radial bounds for positive-weight rational and polynomial Beziers."""
import math

from step_check import require


def bezier_radial_bound(poles,center,radius,weights=None):
    degree = len(poles)-1
    require(1<=degree<=7 and len(center)==3 and math.isfinite(radius) and radius>0 and
            all(math.isfinite(v) for v in center) and
            all(len(p)==3 and all(math.isfinite(v) for v in p) for p in poles),
            "invalid importer Bezier poles or radius")
    weights = [1.0]*len(poles) if weights is None else weights
    require(len(weights)==len(poles) and all(math.isfinite(w) and w>0 for w in weights),
            "Bezier bound requires positive finite weights")
    scale = max(weights)
    weights = [w/scale for w in weights]
    require(min(weights)**2>0,"Bezier weights are too ill-conditioned for a finite bound")
    # Homogeneous curve numerator H and denominator W obey ||H||^2-r^2*W^2.
    shifted = [tuple(a-b for a,b in zip(p,center)) for p in poles]
    coefficients = []
    for k in range(2*degree+1):
        factors = [(i,k-i,math.comb(degree,i)*math.comb(degree,k-i)/math.comb(2*degree,k)*weights[i]*weights[k-i])
                   for i in range(max(0,k-degree),min(degree,k)+1)]
        numerator = math.fsum(f*math.fsum(a*b for a,b in zip(shifted[i],shifted[j])) for i,j,f in factors)
        denominator = math.fsum(f for i,j,f in factors)
        coefficients.append(numerator-radius**2*denominator)
    # W(t)>=min(weights). Include a conservative floating-point allowance.
    squared_bound = (max(abs(v) for v in coefficients)+1e-9)/min(weights)**2
    require(squared_bound<radius**2,"unbounded importer circle")
    return squared_bound/(math.sqrt(radius**2-squared_bound)+radius)
