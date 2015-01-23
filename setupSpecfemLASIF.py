#! /usr/bin/python

import os
import sys
import errno
import shutil
import subprocess 
import xml.etree.ElementTree as ET

# Sets up a directory tree appropriate for a specfem forward model
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
      
# A safe way to copy.
def safeCopy (source, dest):
  
  source = os.path.join (source)
  dest   = os.path.join (dest)

  if (os.path.isdir (source)):
    return

  if not (os.path.isdir (dest)):
    return
  
  try: 
    shutil.copy (source, dest)
  except OSError as exception:
    if exception.errno != errno.EEXIST:
      raise
      
# A safe way to copy.
def safeSymlink (source, dest):
  
  source = os.path.join (source)
  dest   = os.path.join (dest)

  if (os.path.isdir (source)):
    return
  
  try: 
    os.symlink (source, dest)
  except OSError as exception:
    if exception.errno != errno.EEXIST:
      raise
      
def safeRemove (source):
  
  source = os.path.join (source)
  
  try:
    os.remove (source)
  except OSError:
    pass

if (len (sys.argv) < 2 or sys.argv[1] == '--help'):
  sys.exit (
      'Usage: \n \
      --project_name   [name of lasif project]\n \
      --iteration_name [name of current iteration]\n \
      --scratch_path   [path to scratch directory on machine] \n \
      --lasif_path     [path to lasif project root]\n \
      --compiler_suite [cuda/cray/intel]\n \
      --stage          [mesh/prepare_solve/submit_solve]\n \
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
  
# This holds the directions to the base directory where we'll be running.
solverBasePath = scratchPath + projectName + '/' + iterationName + '/'  

if stage == 'mesh':
  
  print "Finding LASIF information..."
      
  # Open iteration descriptor.
  iterationXMLPath = lasifPath + 'ITERATIONS/ITERATION_' + iterationName + '.xml'

  # Find event names.
  tree      = ET.parse (iterationXMLPath)
  root      = tree.getroot ()
  eventList = []
  for name in root.findall ('event'):
    for event in name.findall ('event_name'):
      eventList.append (event.text)

  # Just warn as we might be creating many directories.
  print "I'll be creating " + str (len(eventList)) + " directories in " + scratchPath + ".\n \
  \n+++> Press enter to confirm, or cntl-C to quit. <+++"
  raw_input()

  # Create the forward modelling directories.
  print "Creating directories... "
  for event in eventList:
    fullPath = solverBasePath + event
    setupDirTree (fullPath)

  # Make master mesh directory.
  fullPath = solverBasePath + 'mesh'
  setupDirTree (fullPath)

  # Copy over input files.
  print "Copying initial files..."
  for dir in os.listdir (lasifPath + 'OUTPUT'):
    for event in eventList:
      if iterationName in dir and event in dir:
        
        for file in os.listdir (lasifPath + 'OUTPUT/' + dir):

          source = lasifPath + 'OUTPUT/' + dir + '/' + file
          dest   = solverBasePath + event + '/DATA/'
          safeCopy (source, dest)

          if event == eventList[0]:
            source = lasifPath + 'OUTPUT/' + dir + '/' + file
            dest   = solverBasePath + 'mesh/DATA/'
            shutil.copy (source, dest)

  source = lasifPath + 'SUBMISSION/Par_file'
  dest   = solverBasePath + 'mesh/DATA/'
  shutil.copy (source, dest)

  # Copy one instance of forward files to specfem base directory.
  for file in os.listdir (solverBasePath + 'mesh/DATA/'):
    
    source = solverBasePath + 'mesh/DATA/' + file
    dest   = specfemRoot + 'DATA/'
    safeCopy (source, dest)

  # Change to specfem root directory and compile.
  print "Compiling..."
  os.chdir        (specfemRoot)
  subprocess.call (specfemRoot + 'mk_daint.sh ' + compilerSuite + ' adjoint', shell=True, 
    stdout=None)

  print "Copying compiled binaries..."
  # Copy binaries to all directories.
  for event in os.listdir (solverBasePath):
    for binary in os.listdir ('./bin/'):
      
      source = './bin/' + binary
      dest   = solverBasePath + event + '/bin/'
      safeCopy (source, dest)

  # Copy parameter file that was compiled to all directories (uncessesary probably).
  print "Copying compiled parameter files..."
  for event in os.listdir (solverBasePath):
   
    source = './DATA/Par_file'
    dest   = solverBasePath + event + '/DATA/'
    print 'Copying ' + source + ' to ' + dest
    safeCopy (source, dest)

  # Copy submission scripts to all directories.
  print "Copying submission scripts..."
  for dir in os.listdir (solverBasePath):
    for file in os.listdir (lasifPath + 'SUBMISSION'):
     
      if (file != 'Par_file' or file != 'jobArray_solver_daint.sbatch'):
        source = lasifPath + 'SUBMISSION/' + file
        dest   = solverBasePath + dir + '/'
        safeCopy (source, dest)

  # Copy jobarray script to base directory.
  source = os.path.join (lasifPath, 'SUBMISSION', 'jobArray_solver_daint.sbatch')
  dest   = solverBasePath
  safeCopy (source, dest)

  # Make master job log dir.
  if not os.path.isdir (os.path.join (solverBasePath, 'logs')):
      os.makedirs (os.path.join (solverBasePath, 'logs'))

  # Copy topo_bathy to mesh directory.
  dirPath = os.path.join (solverBasePath, 'mesh', 'DATA')

  if not os.path.isdir (os.path.join (dirPath, 'topo_bathy')):
    os.makedirs (os.path.join (dirPath, 'topo_bathy'))

  for file in os.listdir ('./DATA/topo_bathy'):

    source = os.path.join ('./DATA', 'topo_bathy', file)
    dest   = os.path.join (dirPath, 'topo_bathy')
    safeCopy (source, dest)
      
  print "Done. Please run the mesher in " + solverBasePath + "mesh, and then come back here."
            
elif stage == 'prepare_solve' or stage == 'clean_solve':
  
  if stage == 'clean_solve':
    print "Warning. This will delete all simulation files that aren't in the /mesh directory. \
      \n\n+++> Press enter to confirm, or cntl-C to quit. <+++"
  
  for dir in os.listdir (solverBasePath):
    
    # Don't link the mesh directory to itself, obv.
    if dir == 'mesh' or '.sbatch' in dir:
      continue
      
    # Report what's going on.
    if stage == 'prepare_solve':
      print "Linking: " + dir
    elif stage == 'clean_solve':
      print 'Cleaning: ' + dir
        
    # Symbolically link all the mesh files from the master mesh directory.
    for file in os.listdir (solverBasePath + 'mesh/DATABASES_MPI'):

      if stage == 'prepare_solve':
        source = solverBasePath + 'mesh/DATABASES_MPI/' + file
        dest   = solverBasePath + dir + '/DATABASES_MPI/' + file
        safeSymlink (source, dest)
        
      elif stage == 'clean_solve':
        source = solverBasePath + 'mesh/DATABASES_MPI/' + file
        safeRemove (source)
        
    # Copy the output files from the mesh directory as well.
    for file in os.listdir (solverBasePath + 'mesh/OUTPUT_FILES'):

      if stage == 'prepare_solve':
        source = solverBasePath + 'mesh/OUTPUT_FILES/' + file
        dest   = solverBasePath + dir + '/OUTPUT_FILES/'
        safeCopy (source, dest)
      
      elif stage == 'clean_solve':
        source = solverBasePath + 'mesh/OUTPUT_FILES/' + file
        safeRemove (source)
      
elif stage == 'submit_solve':
  
  # Do a quick count of all the jobs we'll submit for no surprises.
  count = 0
  for dir in os.listdir (solverBasePath):
    
    if dir == 'mesh':
      continue
      
    count = count + 1
    
  print "I'm about to submit " + str (count) + " jobs. \
    \n\n+++> Press enter to confirm, or cntl-C to quit. <+++"
  raw_input()
  
  print "Alright. Here we go baby."
  
  os.chdir (solverBasePath)
  count = 0
  for dir in os.listdir ('./'):
    
    # Skip the mesh directory .. no need to forwawrd model there.
    if dir == 'mesh':
      continue
    
    # Change into the actual directory (this was necessary as the dashes in the directory paths
    # screwed up submitting absolute paths).
    os.chdir (solverBasePath + dir)
    
    # Submit the job.
    jobString = './job_solver_daint.sbatch'
    print "Submitting job in: " + dir
    output = subprocess.Popen ('sbatch %s' % (jobString), shell=True,
      stdout=subprocess.PIPE)

    # Print the job number.
    for line in iter (output.stdout.readline, ""):
      print line

    # Wait for completion.
    output.wait()
    count = count + 1
    if (count == 10):
      break
      
    # Move back to the previous directory.
    os.chdir ('../')
      
else:
  
  print "Unrecognized stage. Quitting"
