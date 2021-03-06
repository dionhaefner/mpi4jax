from setuptools import setup
from setuptools.extension import Extension
from Cython.Build import cythonize
import os


def mpi_info(cmd):
    import mpi4py

    config = mpi4py.get_config()
    cmd_compile = " ".join([config["mpicc"], "-show"])
    out_stream = os.popen(cmd_compile)
    flags = out_stream.read().strip()
    flags = flags.replace(",", " ").split()

    if cmd == "compile":
        startwith = "-I"
    elif cmd == "libdirs":
        startwith = "-L"
    elif cmd == "libs":
        startwith = "-l"

    out = []
    for flag in flags:
        if flag.startswith(startwith):
            out.append(flag[2:])
    return out


setup(
    name="mpi4jax",
    version="0.2.0",
    author="Filippo Vicentini",
    author_email="filippovicentini@gmail.com",
    long_description="""Jax-mpi provides integration among jax and MPI, so that
    code containing MPI calls can be correctly jit-compiled through jax.""",
    url="https://github.com/PhilipVinc/mpi4jax",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=["mpi4jax", "mpi4jax.collective_ops", "mpi4jax.cython"],
    ext_modules=cythonize(
        [
            Extension(
                name="mpi4jax.cython.mpi_xla_bridge",
                sources=["mpi4jax/cython/mpi_xla_bridge.pyx"],
                include_dirs=mpi_info("compile"),
                library_dirs=mpi_info("libdirs"),
                libraries=mpi_info("libs"),
            ),
        ],
    ),
    setup_requires=["setuptools>=18.0", "cython>=0.21", "mpi4py>=3.0.1"],
    python_requires=">=3.6",
    install_requires=["jax", "jaxlib>=0.1.55", "mpi4py>=3.0.1", "numpy"],
    extras_require={"dev": ["pytest"]},
)
