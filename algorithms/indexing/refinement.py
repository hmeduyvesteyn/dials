from __future__ import division
#!/usr/bin/env python
# -*- mode: python; coding: utf-8; indent-tabs-mode: nil; python-indent: 2 -*-
#
# dials.algorithms.indexing.refinement.py
#
#  Copyright (C) 2014 Diamond Light Source
#
#  Author: Richard Gildea
#
#  This code is distributed under the BSD license, a copy of which is
#  included in the root directory of this package.

from cctbx.array_family import flex


def refine(params, reflections, crystal_model, detector, beam,
           scan=None, goniometer=None, maximum_spot_error=None,
           verbosity=0, debug_plots=False):
  from dials.algorithms.spot_prediction import ray_intersection
  reflections_for_refinement = ray_intersection(
    detector, reflections)

  # XXX Interim hack to make refinement work for multiple lattices
  reflections_for_refinement = reflections_for_refinement.deep_copy()
  reflections_for_refinement.set_crystal(
    flex.int(reflections_for_refinement.size(), 0))

  from dials.algorithms.refinement import RefinerFactory
  refiner = RefinerFactory.from_parameters_data_models(
    params, reflections_for_refinement,
    beam=beam,
    goniometer=goniometer,
    detector=detector,
    scan=scan,
    crystal=crystal_model,
    verbosity=verbosity)

  if maximum_spot_error is not None:
    residuals = flex.vec3_double()
    matches = refiner.get_matches()
    frame_obs = flex.double()
    panel_ids = flex.size_t()
    for match in matches:
      residuals.append((match.x_resid, match.y_resid, match.phi_resid))
      frame_obs.append(match.frame_obs)
      panel_ids.append(match.panel)
    x_residuals, y_residuals, phi_residuals = residuals.parts()
    mm_residual_norms = flex.sqrt(
      flex.pow2(x_residuals) + flex.pow2(y_residuals))
    # hard cutoff, but this is essentially what XDS does by default
    # assumes pixel size is same for all panels and same in x and y
    inlier_sel = mm_residual_norms < (
      maximum_spot_error * detector[0].get_pixel_size()[0])
    reflections_for_refinement = reflections_for_refinement.select(
      refiner.selection_used_for_refinement()).select(inlier_sel)
    refiner = RefinerFactory.from_parameters_data_models(
      params, reflections_for_refinement,
      beam=beam,
      goniometer=goniometer,
      detector=detector,
      scan=scan,
      crystal=crystal_model,
      verbosity=verbosity)

    if debug_plots:
      from matplotlib import pyplot
      for i_panel in range(len(detector)):
        panel_sel = (panel_ids == i_panel)
        pyplot.scatter(x_residuals.select(inlier_sel & panel_sel).as_numpy_array(),
                       y_residuals.select(inlier_sel & panel_sel).as_numpy_array(),
                       c='b', alpha=0.5)
        pyplot.scatter(x_residuals.select((~inlier_sel) & panel_sel).as_numpy_array(),
                       y_residuals.select((~inlier_sel) & panel_sel).as_numpy_array(),
                       c='r', alpha=0.5)
        #r = maximum_spot_error * self.detector[0].get_pixel_size()
        #pyplot.Circle((r, r), 0.5, color='b', fill=False)
        pyplot.axes().set_aspect('equal')
        pyplot.show()

      min_frame = int(math.floor(flex.min(frame_obs)))
      max_frame = int(math.ceil(flex.max(frame_obs)))
      mean_residuals_x = []
      mean_residuals_y = []
      mean_residuals_phi = []
      frame = []
      for i_frame in range(min_frame, max_frame):
        sel = (frame_obs >= i_frame) & (frame_obs < (i_frame+1))
        if sel.count(True) == 0:
          continue
        mean_residuals_x.append(flex.mean(x_residuals.select(sel)))
        mean_residuals_y.append(flex.mean(y_residuals.select(sel)))
        mean_residuals_phi.append(flex.mean(phi_residuals.select(sel)))
        frame.append(i_frame)

      fig = pyplot.figure()
      ax = fig.add_subplot(311)
      ax.scatter(frame, mean_residuals_x)
      ax.set_xlabel('frame #')
      ax.set_ylabel('mean residual_x')
      ax = fig.add_subplot(312)
      ax.scatter(frame, mean_residuals_y)
      ax.set_xlabel('frame #')
      ax.set_ylabel('mean residual_y')
      ax = fig.add_subplot(313)
      ax.scatter(frame, mean_residuals_phi)
      ax.set_xlabel('frame #')
      ax.set_ylabel('mean residual_phi')
      pyplot.show()

  refined = refiner.run()
  return refiner, refined
