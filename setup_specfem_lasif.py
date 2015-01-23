#!/usr/bin/env python

import os, errno, shutil
import sys, subprocess
import argparse

import xml.etree.ElementTree as ET

class ParameterError(Exception):
    pass

class PathError(Exception):
    pass
    
class MesherNotRunError(Exception):
    pass
    
class colours:
    ylw = '\033[93m'
    blu = '\033[94m'
    rst = '\033[0m'
    
def print_blu(message):
    print colours.blu + message + colours.rst

def print_ylw(message):
    print colours.ylw + message + colours.rst
    
def read_parameter_file(filename):
    """
    Little function to read the specfem setup parameter file, and returns a
    dictionary of parameters.
    
    :filename: path to parameter file.
    """
    
    # List of required parameters.
    required = ['compiler_suite', 'project_name', 'scratch_path', 
        'specfem_root', 'lasif_path', 'iteration_name']
    
    # Read file, skip lines with #.
    parameters = {}
    file = open(filename, 'r')
    for line in file:        
        if line.startswith('#'):
            continue            
        fields = line.split()
        parameters.update({fields[0]:fields[1]})
        
    # Make sure all required parameters are present.
    for param in required:
        if param not in parameters.keys():
            raise ParameterError('Parameter ' + param + \
                ' not in parameter file.')
        
    # Fix paths.
    parameters['scratch_path'] = os.path.abspath(parameters['scratch_path'])
    parameters['specfem_root'] = os.path.abspath(parameters['specfem_root'])
    parameters['lasif_path']   = os.path.abspath(parameters['lasif_path'])
    
    return parameters  
    
def safe_copy(source, dest):
    """
    Sets up a file copy that won't fail for a stupid reason.
    
    :source: Source file.
    :dest: Destination directory.
    """
    source = os.path.join (source)
    dest   = os.path.join (dest)

    if (os.path.isdir(source)):
        return
    if not (os.path.isdir(dest)):
        return
    try: 
        shutil.copy(source, dest)
    except OSError as exception:    
        if exception.errno != errno.EEXIST:
            raise
    
def safe_sym_link(source, dest):
    """
    Sets up symbolic links that won't fail for a stupid reason.
    
    :source: Source file.
    :dest: Destination file.
    """
    
    source = os.path.join (source)
    dest   = os.path.join (dest)

    if (os.path.isdir(source)):
      return
  
    try: 
      os.symlink(source, dest)
    except OSError as exception:
      if exception.errno != errno.EEXIST:
        raise
    
def setup_dir_tree(event_path):
    """
    Sets up the simulation directory strucutre for one event. 
    
    :event_path: Path the forward simulation directory for a specific event.
    """

    mkdir_p(event_path)
    mkdir_p(event_path + '/bin')
    mkdir_p(event_path + '/DATA')
    mkdir_p(event_path + '/OUTPUT_FILES')
    mkdir_p(event_path + '/DATABASES_MPI')
    mkdir_p(event_path + '/DATA/cemRequest')
    
def find_event_names(iteration_xml_path):
    """
    Quickly parses the iteration xml file and extracts all the event names.
    
    :iteration_xml_path: Path the xml file driving the requested iteration.
    """
    
    # Find event names.
    tree       = ET.parse (iteration_xml_path)
    root       = tree.getroot ()
    event_list = []
    for name in root.findall ('event'):
      for event in name.findall ('event_name'):
        event_list.append (event.text)
        
    return event_list
                    
def mkdir_p(path):
    """
    Makes a directory and doesn't fail if the directory already exists.
    
    :path: New directory path.
    """        
    
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            pass
        else:
            raise

def setup_run():
    """
    Function does a whole bunch of things to set up a specfem run on daint.
    """
    
    # Find iteration xml file.
    iteration_xml_path = os.path.join(p['lasif_path'], 
        'ITERATIONS/ITERATION_%s.xml' % (p['iteration_name']))
    if not os.path.exists(iteration_xml_path):
        raise PathError('Your iteration xml file does not exist in the location\
            you specified.')
    event_list = find_event_names(iteration_xml_path)

    # Create the forward modelling directories.
    print_ylw('Creating forward modelling directories...')
    for event in event_list:
        event_path = os.path.join(solver_base_path, event)
        setup_dir_tree(event_path)
    
    # Make master mesh directory.
    mesh_path = os.path.join(solver_base_path, 'mesh')
    setup_dir_tree(mesh_path)

    # Copy over input files.
    print_ylw('Copying initial files...')
    lasif_output = os.path.join(p['lasif_path'], 'OUTPUT')
    for dir in os.listdir (lasif_output):
        for event in event_list:
            if p['iteration_name'] in dir and event in dir:

                event_output_dir = os.path.join(lasif_output, dir)
                for file in os.listdir(event_output_dir):

                    source = os.path.join(event_output_dir, file)
                    dest   = os.path.join(solver_base_path, event, 'DATA')
                    safe_copy(source, dest)

                    if event == event_list[0]:

                        source = os.path.join(event_output_dir, file)
                        dest   = os.path.join(solver_base_path, 'mesh', 'DATA')
                        safe_copy(source, dest)

    # Copy one instance of forward files to specfem base directory.
    source = os.path.join(p['lasif_path'], 'SUBMISSION', 'Par_file')
    dest   = os.path.join(p['specfem_root'], 'DATA')
    safe_copy(source, dest)

    # # Change to specfem root directory and compile.
    print_ylw('Compiling...')
    os.chdir(p['specfem_root'])
    with open('compilation_log.txt', 'w') as output:
        proc = subprocess.Popen(['./mk_daint.sh', p['compiler_suite'], 
            'adjoint'], stdout=output, stderr=output)
        proc.communicate()
        retcode = proc.wait()

    # Copy binaries to all directories.
    print_ylw('Copying compiled binaries...')
    for event in os.listdir(solver_base_path):
        for binary in os.listdir('./bin/'):

            source = os.path.join('./bin', binary)
            dest   = os.path.join(solver_base_path, event, 'bin')
            safe_copy(source, dest)
            
    print_ylw('Copying compiled parameter file...')
    for event in os.listdir(solver_base_path):
        source = os.path.join('./DATA', 'Par_file')
        dest   = os.path.join(solver_base_path, event, 'DATA')
        safe_copy(source, dest)
        
    # Copy jobarray script to base directory.
    print_ylw('Copying jobarray sbatch script...')
    source = os.path.join(p['lasif_path'], 'SUBMISSION', 
        'jobArray_solver_daint.sbatch')
    dest   = solver_root_path
    safe_copy(source, dest)
    log_directory = os.path.join(solver_root_path, 'logs')
    mkdir_p(log_directory)

    # Copy topo_bathy to mesh directory.
    print_ylw('Copying topography information...')
    mesh_data_path = os.path.join(solver_base_path, 'mesh', 'DATA')
    mesh_topo_path = os.path.join(mesh_data_path, 'topo_bathy')
    master_topo_path = os.path.join('./DATA', 'topo_bathy')
    mkdir_p(mesh_topo_path)
    for file in os.listdir(master_topo_path):
        source = os.path.join(master_topo_path, file)
        dest   = os.path.join(mesh_topo_path)
        safe_copy(source, dest)
    
    # Copy submission script to mesh directory.
    source = os.path.join(p['lasif_path'], 'SUBMISSION', 
        'job_mesher_daint.sbatch')
    dest = os.path.join(solver_base_path, 'mesh')
    safe_copy(source, dest)
    
    print_blu('Done.')
    
def prepare_solve():
    """
    Sets up symbolic link to generated mesh files.
    """
    
    print 'Preparing solver directories.'
    for dir in os.listdir(solver_base_path):
        
        if dir == 'mesh': 
            continue
        
        print_ylw('Linking ' + dir)
        databases_mpi = os.path.join(solver_base_path, 'mesh', 'DATABASES_MPI')
        output_files = os.path.join(solver_base_path, 'mesh', 'OUTPUT_FILES')
        
        if not os.listdir(databases_mpi):
            raise MesherNotRunError("It doesn't look like the mesher has been \
            run. There are no mesh files in the expected mesh directory.")
        
        for file in os.listdir(databases_mpi):
            source = os.path.join(databases_mpi, file)
            dest = os.path.join(solver_base_path, dir, 'DATABASES_MPI', file)
            safe_sym_link(source, dest)
            
        for file in os.listdir(output_files):
            source = os.path.join(output_files, file)
            dest = os.path.join(solver_base_path, dir, 'OUTPUT_FILES')
            safe_copy(source, dest)
            
    print_blu('Done.')
    
def submit_mesher():
    """
    Runs over to the meshing directory, and just submits the job.
    """
    
    mesh_dir = os.path.join(solver_base_path, 'mesh')
    os.chdir(mesh_dir)
    subprocess.Popen(['sbatch', 'job_mesher_daint.sbatch']).wait()
    
def submit_solver(first_job, last_job):
    """
    Submits the job array script in the solver_root_path directory. Submits 
    job array indices first_job to last_job.
    
    :first_job: The job array index of the first job to submit (i.e. 0)
    :last_job: The job array index of the last job to submit (i.e. n_events-1)
    """
    
    os.chdir(solver_root_path)
    subprocess.Popen(['sbatch', '--array=%s-%s' % (first_job, last_job), 
        'jobArray_solver_daint.sbatch', p['iteration_name']]).wait()
                    
parser = argparse.ArgumentParser(description='Assists in the setup of' 
    'specfem3d_globe on Piz Daint')
parser.add_argument('-f', type=str, help='Simulation driver parameter file.', 
    required=True, metavar='parameter_file_name', dest='filename')
parser.add_argument('--setup_run', action='store_true', 
    help='Setup the directory tree on scratch for one iteration. Requires a \
        param file.')
parser.add_argument('--prepare_solve', action='store_true', 
    help='Symbolically links the mesh files to all forward directories.')
parser.add_argument('--submit_mesher', action='store_true', 
    help='Runs the mesher in the "mesh" directory.')
parser.add_argument('--submit_solver', action='store_true',
    help='Submit the job array script for the current iteration.')
parser.add_argument('-fj', type=str, help='First index in job array to submit',
    metavar='first_job', dest='first_job')
parser.add_argument('-lj', type=str, help='Last index in job array to submit',
    metavar='last_job', dest='last_job')

args = parser.parse_args()
if args.submit_solver and args.first_job is None and args.last_job is None:
    parser.error('Submitting the solver required -fj and -lj arguments.')

p = read_parameter_file(args.filename)

# Construct full run path.
solver_base_path = os.path.join(p['scratch_path'], p['project_name'], 
    p['iteration_name'])
solver_root_path = os.path.join(p['scratch_path'], p['project_name'])
mkdir_p(solver_base_path)

if args.setup_run:
    setup_run()
elif args.prepare_solve:
    prepare_solve()
elif args.submit_mesher:
    submit_mesher()
elif args.submit_solver:
    submit_solver(args.first_job, args.last_job)
