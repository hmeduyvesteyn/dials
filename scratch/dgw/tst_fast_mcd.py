#!/usr/bin/env python

"""Testing functions for multivariate outlier rejection by the FAST-MCD
algorithm"""

# Want implementation of Mahalanobis distance that matches this R session:

#> x1 <- round(rnorm(10,3), 3)
#> x2 <- round(x1 + rnorm(10), 3)
#> x3 <- round(x2 + runif(10), 3)
#> x1
# [1] 3.853 2.401 2.253 3.067 1.887 3.293 3.995 2.559 2.785 2.228
#> x2
# [1] 4.294 1.915 1.315 4.641 1.611 2.838 3.696 1.337 2.853 2.434
#> x3
# [1] 4.785 2.352 2.023 4.978 2.329 3.101 4.494 2.204 3.468 3.075
#> obs <- cbind(x1, x2, x3)
#> S <- var(obs)
#> S
#          x1        x2       x3
#x1 0.5020374 0.6667232 0.633355
#x2 0.6667232 1.4434718 1.326026
#x3 0.6333550 1.3260262 1.248315
#> mahalanobis(obs, c(mean(x1), mean(x2), mean(x3)), S)
# [1] 2.1838336 1.9673401 1.3335029 4.9191627 2.1246818 5.3297995 4.9022487
# [8] 2.5335913 0.1952562 1.5105832

from math import floor
from scitbx.array_family import flex
from dials.algorithms.statistics.fast_mcd import maha_dist_sq, FastMCD, cov

# test Mahalanobis distance.
x1 = flex.double((3.853, 2.401, 2.253, 3.067, 1.887, 3.293, 3.995, 2.559, 2.785, 2.228))
x2 = flex.double((4.294, 1.915, 1.315, 4.641, 1.611, 2.838, 3.696, 1.337, 2.853, 2.434))
x3 = flex.double((4.785, 2.352, 2.023, 4.978, 2.329, 3.101, 4.494, 2.204, 3.468, 3.075))
cols = [x1, x2, x3]
center = [flex.mean(e) for e in cols]
covmat = cov(x1, x2, x3)
n = len(cols[0])

maha = maha_dist_sq(cols, center, covmat)

from libtbx.test_utils import approx_equal
R_result = [2.1838336, 1.9673401, 1.3335029, 4.9191627, 2.1246818,
            5.3297995, 4.9022487, 2.5335913, 0.1952562, 1.5105832]
assert approx_equal(list(maha), R_result)

# some test data, from R package robustbase: Hawkins, Bradu, Kass's Artificial Data
hbk = """10.1 19.6 28.3
 9.5 20.5 28.9
10.7 20.2 31.0
 9.9 21.5 31.7
10.3 21.1 31.1
10.8 20.4 29.2
10.5 20.9 29.1
 9.9 19.6 28.8
 9.7 20.7 31.0
 9.3 19.7 30.3
11.0 24.0 35.0
12.0 23.0 37.0
12.0 26.0 34.0
11.0 34.0 34.0
 3.4  2.9  2.1
 3.1  2.2  0.3
 0.0  1.6  0.2
 2.3  1.6  2.0
 0.8  2.9  1.6
 3.1  3.4  2.2
 2.6  2.2  1.9
 0.4  3.2  1.9
 2.0  2.3  0.8
 1.3  2.3  0.5
 1.0  0.0  0.4
 0.9  3.3  2.5
 3.3  2.5  2.9
 1.8  0.8  2.0
 1.2  0.9  0.8
 1.2  0.7  3.4
 3.1  1.4  1.0
 0.5  2.4  0.3
 1.5  3.1  1.5
 0.4  0.0  0.7
 3.1  2.4  3.0
 1.1  2.2  2.7
 0.1  3.0  2.6
 1.5  1.2  0.2
 2.1  0.0  1.2
 0.5  2.0  1.2
 3.4  1.6  2.9
 0.3  1.0  2.7
 0.1  3.3  0.9
 1.8  0.5  3.2
 1.9  0.1  0.6
 1.8  0.5  3.0
 3.0  0.1  0.8
 3.1  1.6  3.0
 3.1  2.5  1.9
 2.1  2.8  2.9
 2.3  1.5  0.4
 3.3  0.6  1.2
 0.3  0.4  3.3
 1.1  3.0  0.3
 0.5  2.4  0.9
 1.8  3.2  0.9
 1.8  0.7  0.7
 2.4  3.4  1.5
 1.6  2.1  3.0
 0.3  1.5  3.3
 0.4  3.4  3.0
 0.9  0.1  0.3
 1.1  2.7  0.2
 2.8  3.0  2.9
 2.0  0.7  2.7
 0.2  1.8  0.8
 1.6  2.0  1.2
 0.1  0.0  1.1
 2.0  0.6  0.3
 1.0  2.2  2.9
 2.2  2.5  2.3
 0.6  2.0  1.5
 0.3  1.7  2.2
 0.0  2.2  1.6
 0.3  0.4  2.6"""

# unpack the data into vectors
rows = [[float(e) for e in row.split()] for row in hbk.splitlines()]
x1, x2, x3 = [flex.double(e) for e in zip(*rows)]

# test small dataset algorithm
fast_mcd = FastMCD([x1, x2, x3])
print "Fast MCD raw estimates"
T, S = fast_mcd.get_raw_T_and_S()
print list(T)
print S.as_scitbx_matrix()
print "Fast MCD corrected estimates"
T, S = fast_mcd.get_corrected_T_and_S()
print list(T)
print S.as_scitbx_matrix()
print "with corrections"
print fast_mcd._consistency_fac
print fast_mcd._finite_samp_fac

# test large dataset algorithm
import libtbx.load_env # required for libtbx.env.find_in_repositories
if not libtbx.env.has_module("dials_regression"):
  import sys
  sys.exit("Skipping tests in " + __file__ + " as dials_regression not present")

# load data
import os
dials_regression = libtbx.env.find_in_repositories(
    relative_path="dials_regression",
    test=os.path.isdir)
data_pth = os.path.join(dials_regression, "refinement_test_data",
  "outlier_rejection", "residuals.dat")

with(open(data_pth, "r")) as f:
  residuals = f.readlines()

# ignore first line, which is a header
residuals = [[float(val) for val in e.split()] for e in residuals[1:]]
X_resid_mm, Y_resid_mm, Phi_resid_mm = zip(*residuals)

X_resid_mm = flex.double(X_resid_mm)
Y_resid_mm = flex.double(Y_resid_mm)
Phi_resid_mm = flex.double(Phi_resid_mm)

print "Fast MCD estimates"

# 20 trials
trials = []
for i in xrange(20):
  print "trial {0}".format(i)
  fast_mcd = FastMCD([X_resid_mm, Y_resid_mm, Phi_resid_mm])
  loc, S = fast_mcd.get_raw_T_and_S()
  trials.append((loc, S))

#print "Location estimates for 20 trials follow"
#print "======================================="
#for trial in trials:
#  print "{0} {1} {2}".format(*trial)
