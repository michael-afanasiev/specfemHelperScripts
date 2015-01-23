#! /bin/bash -l

if [ "$2" == "" ]; then echo "Did not specify compiler suite."; exit 1; fi

compiler_suite=$1
mode=$2

module purge

# forward simulations
echo "compiling forward simulations..."
make clean

# Clean up anything from before
rm -rf OUTPUT_FILES/*
rm -rf bin
rm -rf bin.forward
rm -rf bin.kernel

# Change simulation type to forward.
if [ "$mode" == "forward" ]; then
    ./change_simulation_type.pl -f;
fi

if [ "$mode" == "adjoint" ]; then
    ./change_simulation_type.pl -F;
fi

if [ "$compiler_suite" == "cray" ]; then
  
    module load PrgEnv-cray cray-mpich cray-hdf5-parallel cray-netcdf-hdf5parallel;
    CEM_LIBS="-L$HDF5_DIR/lib -lhdf5_parallel_cray -lhdf5_hl_parallel_cray -L$NETCDF_DIR/lib -lnetcdf_parallel_cray" \
    FC=ftn CC=cc MPIF90=ftn \
    LDFLAGS='-dynamic' MPI_INC=$CRAY_MPICH2_DIR/include FLAGS_CHECK='-hpic -dynamic' \
    CFLAGS='-hpic -dynamic' FCFLAGS='-O3' ./configure --with-cem
    
    mkdir -p bin;
    
    CRAY_CPU_TARGET=x86_64 make -j 4;
    
fi

if [ "$compiler_suite" == "cuda.adios" ]; then

    module load PrgEnv-gnu
    module load cray-mpich
    module load cray-netcdf-hdf5parallel
    module load cray-hdf5-parallel
    module load cudatoolkit
    module load adios/1.7.0_gnu

    module list

    FC=ftn CC=cc MPIF90=ftn MPICC=cc \
    CEM_LIBS="-L$HDF5_DIR/lib -lhdf5 -lhdf5_hl -L$NETCDF_DIR/lib -lnetcdff" \
    CUDA_INC=$CRAY_CUDATOOLKIT_DIR/include \
    CUDA_LIB=$CRAY_CUDATOOLKIT_DIR/lib64 MPI_INC=$CRAY_MPICH2_DIR/include \
    FLAGS_CHECK='-O3' \
    CFLAGS='-O3' \
    ADIOS_INC=$ADIOS_POST_COMPILE_OPTS \
    ADIOS_LIB=$ADIOS_POST_LINK_OPTS \
    ./configure --with-cuda=cuda5 --with-adios --with-cem 

    mkdir -p bin;

    CRAY_CPU_TARGET=x86_64 make -j 4

fi

if [ "$compiler_suite" == "cuda" ]; then
    
    module load PrgEnv-cray cray-mpich cray-hdf5-parallel cray-netcdf-hdf5parallel cudatoolkit;
    
    CEM_LIBS="-L$HDF5_DIR/lib -lhdf5_parallel_cray -lhdf5_hl_parallel_cray -L$NETCDF_DIR/lib -lnetcdf_parallel_cray" \
    FC=ftn CC=cc MPIF90=ftn \
    CUDA_INC=$CRAY_CUDATOOLKIT_DIR/include \
    CUDA_LIB=$CRAY_CUDATOOLKIT_DIR/lib64 MPI_INC=$CRAY_MPICH2_DIR/include \
    FLAGS_CHECK="-hpic -dynamic" CFLAGS="-hpic -dynamic" FCFLAGS='-O3' \
    ./configure --with-cem --with-cuda=cuda5 
    
    mkdir -p bin;
    
    CRAY_CPU_TARGET=x86_64 make -j 4;
    
fi

if [ "$compiler_suite" == "cudaNoCem" ]; then
    
    module load PrgEnv-cray cray-mpich cray-hdf5-parallel cray-netcdf-hdf5parallel cudatoolkit;
    
    FC=ftn CC=cc MPIF90=ftn \
    CUDA_INC=$CRAY_CUDATOOLKIT_DIR/include \
    CUDA_LIB=$CRAY_CUDATOOLKIT_DIR/lib64 MPI_INC=$CRAY_MPICH2_DIR/include \
    FLAGS_CHECK="-hpic -dynamic" CFLAGS="-hpic -dynamic" FCFLAGS='-O3' \
    ./configure --with-cuda=cuda5;
    
    mkdir -p bin;
    
    CRAY_CPU_TARGET=x86_64 make -j 4;
    
fi

# Copy from bin to bin.forward directory
if [ "$mode" == "forward" ]; then
  cp -rp bin bin.forward;
  if [ ! -e bin.forward/xspecfem3D ]; then exit; fi
fi

if [ "$mode" == "adjoint" ]; then
  cp -rp bin bin.kernel;
  if [ ! -e bin.kernel/xspecfem3D ]; then exit; fi
fi
