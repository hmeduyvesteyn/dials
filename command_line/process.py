#!/usr/bin/env python
#
# dials.process.py
#
#  Copyright (C) 2013 Diamond Light Source
#
#  Author: James Parkhurst
#
#  This code is distributed under the BSD license, a copy of which is
#  included in the root directory of this package.

from __future__ import division

help_message = '''

This is the main dials program. Given a set of images, the data will be
processed and a list of integrated reflections will be given as output. More
specialised help can be seen by looking at the command line programs that
perform the individual processing steps. See at the following for more
details::

  dials.import
  dials.find_spots
  dials.index
  dials.refine
  dials.integrate
  dials.export_mtz

This program will do the following:

  First the image data will be imported into a datablock. Strong spots will then
  be found on all the images of the datablock. These strong spots will then be
  indexed (the indexing step also includes some static centroid refinement). The
  experimental geometry will then be refined and the reflections integrated.
  Finally, the integrated reflections will be exported to an MTZ file which can
  be input into Aimless to be scaled.

Examples::

  dials.process images*.cbf

  dials.process datablock.json

  find . -name "images*.cbf" | dials.process

'''

from libtbx.phil import parse
phil_scope = parse('''
  verbosity = 1
    .type = int(value_min=0)
    .help = "The verbosity level"

  output {
    datablock_filename = datablock.json
      .type = str
      .help = "The filename for output datablock"

    strong_filename = strong.pickle
      .type = str
      .help = "The filename for strong reflections from spot finder output."

    indexed_filename = indexed.pickle
      .type = str
      .help = "The filename for indexed reflections."

    refined_experiments_filename = refined_experiments.json
      .type = str
      .help = "The filename for saving refined experimental models"

    integrated_filename = integrated.pickle
      .type = str
      .help = "The filename for final integrated reflections."

    profile_filename = profile.phil
      .type = str
      .help = "The filename for output reflection profile parameters"

    mtz_filename = integrated.mtz
      .type = str
      .help = "The filename for output mtz"
  }

  include scope dials.algorithms.peak_finding.spotfinder_factory.phil_scope
  include scope dials.algorithms.indexing.indexer.index_only_phil_scope
  include scope dials.algorithms.refinement.refiner.phil_scope
  include scope dials.algorithms.integration.integrator.phil_scope
  include scope dials.algorithms.profile_model.factory.phil_scope
  include scope dials.algorithms.spot_prediction.reflection_predictor.phil_scope

''', process_includes=True)

class Script(object):
  '''A class for running the script.'''

  def __init__(self):
    '''Initialise the script.'''
    from dials.util.options import OptionParser
    import libtbx.load_env

    # The script usage
    usage = "usage: %s [options] [param.phil] datablock.json" % libtbx.env.dispatcher_name

    # Create the parser
    self.parser = OptionParser(
      usage=usage,
      phil=phil_scope,
      epilog=help_message,
      read_datablocks=True,
      read_datablocks_from_images=True)

  def run(self):
    '''Execute the script.'''
    from dials.util.options import flatten_datablocks
    from dials.util import log
    from logging import info
    from time import time
    import sys

    # Parse the command line
    params, options = self.parser.parse_args(show_diff_phil=True)
    datablocks = flatten_datablocks(params.input.datablock)

    # Save the options
    self.options = options
    self.params = params

    st = time()

    # Import stuff
    if len(datablocks) == 0:
      self.parser.print_help()
      return
    elif len(datablocks) > 1:
      raise RuntimeError('Only 1 datablock can be processed at a time.')
    datablock = datablocks[0]

    # Configure logging
    log.config(
      params.verbosity,
      info='dials.integrate.log',
      debug='dials.integrate.debug.log')

    # Preamble stuff
    info('*' * 80)
    info('')
    info('                       mmmm   mmmmm    mm   m       mmmm            ')
    info('                       #   "m   #      ##   #      #"   "           ')
    info('                      m#mm  #   #     #  #  #      "#mmm            ')
    info('                       #    #   #     #mm#  #          "#           ')
    info('                       #mmm"  mm#mm  #    # #mmmmm "mmm#"           ')
    info('')
    info('Launching dials.process')
    info('')
    info('The following tasks will be performed:')
    info(' 1) Strong spots will be found (dials.find_spots)')
    info(' 2) The strong spots will be indexed (dials.index)')
    info(' 3) The model will be further refined (dials.refine)')
    info(' 4) The reflections will be integrated (dials.integrate)')
    info(' 5) The data will be exported as MTZ (dials.export_mtz)')
    info('')
    info('Please be patient, this may take a few minutes')
    info('')
    info('*' * 80)
    info('')
    info('Command-line: %s' % (' '.join(sys.argv[1:]))[:65])
    info('')
    info('*' * 80)
    info('')

    if self.params.output.datablock_filename:
      from dxtbx.datablock import DataBlockDumper
      dump = DataBlockDumper(datablock)
      dump.as_json(self.params.output.datablock_filename)

    # Do the processing
    observed = self.find_spots(datablock)
    experiments, indexed = self.index(datablock, observed)
    experiments = self.refine(experiments, indexed)
    integrated = self.integrate(experiments, indexed)
    mtz = self.mtz(integrated, experiments)
    mtz.show_summary()

    # Total Time
    info("")
    info("Total Time Taken = %f seconds" % (time() - st))

  def find_spots(self, datablock):
    from time import time
    from logging import info
    from dials.array_family import flex
    st = time()

    info('*' * 80)
    info('Finding Strong Spots')
    info('*' * 80)

    # Find the strong spots
    observed = flex.reflection_table.from_observations(datablock, self.params)

    # Save the reflections to file
    info('\n' + '-' * 80)
    if self.params.output.strong_filename:
      self.save_reflections(observed, self.params.output.strong_filename)

    info('')
    info('Time Taken = %f seconds' % (time() - st))
    return observed

  def index(self, datablock, reflections):
    from time import time
    from logging import info
    import copy
    st = time()

    info('*' * 80)
    info('Indexing Strong Spots')
    info('*' * 80)

    imagesets = datablock.extract_imagesets()

    params = copy.deepcopy(self.params)
    # don't do scan-varying refinement during indexing
    params.refinement.parameterisation.crystal.scan_varying = False
    if params.indexing.method == "fft3d":
      from dials.algorithms.indexing.fft3d import indexer_fft3d as indexer
    elif params.indexing.method == "fft1d":
      from dials.algorithms.indexing.fft1d import indexer_fft1d as indexer
    elif params.indexing.method == "real_space_grid_search":
      from dials.algorithms.indexing.real_space_grid_search \
           import indexer_real_space_grid_search as indexer
    idxr = indexer(reflections, imagesets, params=params)

    indexed = idxr.refined_reflections
    experiments = idxr.refined_experiments

    if self.params.output.indexed_filename:
      self.save_reflections(indexed, self.params.output.indexed_filename)

    info('')
    info('Time Taken = %f seconds' % (time() - st))
    return experiments, indexed

  def refine(self, experiments, centroids):
    from dials.algorithms.refinement import RefinerFactory
    from logging import info
    from time import time
    st = time()

    info('*' * 80)
    info('Refining Model')
    info('*' * 80)

    refiner = RefinerFactory.from_parameters_data_experiments(
      self.params, centroids, experiments)

    refiner.run()
    experiments = refiner.get_experiments()

    # Dump experiments to disk
    if self.params.output.refined_experiments_filename:
      from dxtbx.model.experiment.experiment_list import ExperimentListDumper
      dump = ExperimentListDumper(experiments)
      dump.as_json(self.params.output.refined_experiments_filename)

    info('')
    info('Time Taken = %f seconds' % (time() - st))

    return experiments

  def integrate(self, experiments, indexed):
    from time import time
    from logging import info

    st = time()

    info('*' * 80)
    info('Integrating Reflections')
    info('*' * 80)


    indexed = self.process_reference(indexed)

    # Get the integrator from the input parameters
    info('Configurating integrator from input parameters')
    from dials.algorithms.profile_model.factory import ProfileModelFactory
    from dials.algorithms.integration.integrator import IntegratorFactory
    from dials.array_family import flex

    # Compute the profile model
    # Predict the reflections
    # Match the predictions with the reference
    # Create the integrator
    profile_model = ProfileModelFactory.create(self.params, experiments, indexed)
    info("")
    info("=" * 80)
    info("")
    info("Predicting reflections")
    info("")
    predicted = profile_model.predict_reflections(
      experiments,
      dmin=self.params.prediction.dmin,
      dmax=self.params.prediction.dmax,
      margin=self.params.prediction.margin,
      force_static=self.params.prediction.force_static)
    predicted.match_with_reference(indexed)
    info("")
    integrator = IntegratorFactory.create(self.params, experiments, profile_model, predicted)

    # Integrate the reflections
    reflections = integrator.integrate()

    if self.params.output.integrated_filename:
      # Save the reflections
      self.save_reflections(reflections, self.params.output.integrated_filename)

    if self.params.output.profile_filename:
      with open(self.params.output.profile_filename, "w") as outfile:
        outfile.write(profile_model.dump().as_str())

    info('')
    info('Time Taken = %f seconds' % (time() - st))
    return reflections

  def mtz(self, integrated, experiments):
    from dials.util.export_mtz import export_mtz
    from time import time
    from logging import info
    st = time()
    info('*' * 80)
    info('Exporting measurements to %s' % self.params.output.mtz_filename)
    info('*' * 80)
    m = export_mtz(integrated, experiments, self.params.output.mtz_filename)
    info('')
    info('Time Taken = %f seconds' % (time() - st))
    return m

  def process_reference(self, reference):
    ''' Load the reference spots. '''
    from dials.array_family import flex
    from logging import info
    from time import time
    if reference is None:
      return None
    st = time()
    assert("miller_index" in reference)
    assert("id" in reference)
    info('Removing reference spots with invalid coordinates')
    info(' using %d reference spots' % len(reference))
    mask = flex.bool([x == (0, 0, 0) for x in reference['xyzcal.mm']])
    reference.del_selected(mask)
    info(' removed %d with no coordinates' % mask.count(True))
    mask = flex.bool([h == (0, 0, 0) for h in reference['miller_index']])
    reference.del_selected(mask)
    info(' removed %d with no miller indices' % mask.count(True))
    mask = flex.bool([x < 0 for x in reference['id']])
    reference.del_selected(mask)
    reference['id'] = flex.size_t(list(reference['id']))
    info(' removed %d with negative experiment id' % mask.count(True))
    info(' using %d reference spots' % len(reference))
    info(' time taken: %g' % (time() - st))
    return reference

  def save_reflections(self, reflections, filename):
    ''' Save the reflections to file. '''
    from logging import info
    from time import time
    st = time()
    info('Saving %d reflections to %s' % (len(reflections), filename))
    reflections.as_pickle(filename)
    info(' time taken: %g' % (time() - st))

if __name__ == '__main__':
  from dials.util import halraiser
  try:
    script = Script()
    script.run()
  except Exception as e:
    halraiser(e)
