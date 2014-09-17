#! /usr/bin/python

import os
import sys
import errno
import shutil
import subprocess 
import xml.etree.ElementTree as ET

def setupDirTree (fullPath):

  try:
    os.makedirs (fullPath)
  except OSError as exception:
    if exception.errno != errno.EEXIST:
      raise

  try:
    os.makedirs (fullPath + '/bin')
  except OSError as exception:
    if exception.errno != errno.EEXIST:
      raise

  try:
    os.makedirs (fullPath + '/DATA')
  except OSError as exception:
    if exception.errno != errno.EEXIST:
      raise

  try:
    os.makedirs (fullPath + '/OUTPUT_FILES')
  except OSError as exception:
    if exception.errno != errno.EEXIST:
      raise

  try:
    os.makedirs (fullPath + '/DATABASES_MPI')
  except OSError as exception:
    if exception.errno != errno.EEXIST:
      raise

  try:
    os.makedirs (fullPath + '/DATA/cemRequest')
  except OSError as exception:
    if exception.errno != errno.EEXIST:
      raise

if ( len (sys.argv) < 2 or sys.argv[1] == '--help' ):
  sys.exit (
      'Usage: \n \
      --project_name   [name of lasif project]\n \
      --iteration_name [name of current iteration]\n \
      --scratch_path   [path to scratch directory on machine] \n \
      --lasif_path     [path to lasif project root]\n \
      --compiler_suite [cuda/cray/intel]\n \
      --stage          [mesh/solve]\n \
      --specfem_root   [path to base directory of specfem installation]'
      )

# Initialize blank parameters.
lasifPath     = None
iterationName = None
compilerSuite = None
stage         = None
scratchPath   = None
projectName   = None
specfemRoot   = None

# Read from command line.
for i in range ( len (sys.argv) - 1 ):
  if ( sys.argv[i] == '--lasif_path' ):
    lasifPath = sys.argv[i+1]
  if ( sys.argv[i] == '--iteration_name' ):
    iterationName = sys.argv[i+1]
  if ( sys.argv[i] == '--compiler_suite' ):
    compilerSuite = sys.argv[i+1]
  if ( sys.argv[i] == '--stage' ):
    stage = sys.argv[i+1]
  if ( sys.argv[i] == '--scratch_path' ):
    scratchPath = sys.argv[i+1]
  if ( sys.argv[i] == '--project_name' ):
    projectName = sys.argv[i+1]
  if ( sys.argv[i] == '--specfem_root' ):
    specfemRoot = sys.argv[i+1]

# Make sure inputs are sane.
if not lasifPath or not iterationName or not compilerSuite or not stage \
    or not scratchPath or not projectName or not specfemRoot:
  sys.exit ('Problem specifying some required parameter. Try again.')

if stage == 'mesh':
  # Open iteration descriptor.
  iterationXMLPath = lasifPath + 'ITERATIONS/ITERATION_' + iterationName + '.xml'

  # Find event names.
  tree      = ET.parse (iterationXMLPath)
  root      = tree.getroot()
  eventList = []
  for name in root.findall ('event'):
    for event in name.findall ('event_name'):
      eventList.append (event.text)

  # Just warn as we might be creating many directories.
  print "I'll be creating " + str (len(eventList)) + " directories in " + scratchPath + ".\n \
  +++> Press enter to confirm, or cntl-C to quit. <+++"
  raw_input()

  # Create the forward modelling directories.
  for event in eventList:
    fullPath = scratchPath + projectName + '/' + iterationName + '/' + event
    print "Creating: " + fullPath
    setupDirTree ( fullPath )

  # Make master mesh directory.
  fullPath = scratchPath + projectName + '/' + iterationName + '/mesh'
  setupDirTree ( fullPath )

  # Copy over input files.
  for dir in os.listdir (lasifPath + 'OUTPUT'):
    for event in eventList:
      if iterationName in dir and event in dir:
        for file in os.listdir (lasifPath + 'OUTPUT/' + dir):

          source = lasifPath + 'OUTPUT/' + dir + '/' + file
          dest   = scratchPath + projectName + '/' + iterationName + '/' + event + '/DATA/'
          shutil.copy (source, dest)

          if event == eventList[0]:
            source = lasifPath + 'OUTPUT/' + dir + '/' + file
            dest   = scratchPath + projectName + '/' + iterationName + '/mesh/DATA/'
            shutil.copy (source, dest)

  # Copy one instance of forward files to specfem base directory.
  for file in os.listdir (scratchPath + projectName + '/' + iterationName + '/mesh/DATA/'):
    source = os.path.join (scratchPath + projectName + '/' + iterationName + '/mesh/DATA/' + file)
    dest   = os.path.join (specfemRoot + 'DATA/')
    if os.path.isdir (source):
      continue
    else:
      shutil.copy (source, dest)

  # Change to specfem root directory and compile.
  os.chdir        (specfemRoot)
  subprocess.call (specfemRoot + 'mk_daint.sh ' + compilerSuite + ' yes forward', shell=True, 
    stdout=None)

  # Copy binaries to all directories.
  for event in os.listdir (os.path.join (scratchPath + projectName + '/' + iterationName + '/') ):
    for binary in os.listdir (os.path.join ('./bin/') ):
      source = os.path.join ('./bin/' + binary)
      dest   = os.path.join (scratchPath + projectName + '/' + iterationName + '/' + event + '/bin/')
      if os.path.isdir (source):
        continue
      else:
        shutil.copy (source, dest)

  # Copy parameter file to all directories.
  for event in os.listdir (os.path.join (scratchPath + projectName + '/' + iterationName + '/') ):
    source = os.path.join ('./DATA/Par_file')
    dest   = os.path.join (scratchPath + projectName + '/' + iterationName + '/' + event + '/DATA/')

  # Copy submission scripts to all directories.
  for dir in os.listdir ( os.path.join (scratchPath + projectName + '/' +iterationName + '/') ):
    for file in os.listdir ( os.path.join (lasifPath + 'SUBMISSION') ):
      source = os.path.join (lasifPath + 'SUBMISSION/' + file)
      dest   = os.path.join (scratchPath + projectName + '/' + iterationName + '/' + dir + '/')
      shutil.copy (source, dest)
      
if stage == 'solve':
  for dir in os.listdir ( os.path.join (scratchPath + projectName + '/' +iterationName + '/') ):
    print dir
