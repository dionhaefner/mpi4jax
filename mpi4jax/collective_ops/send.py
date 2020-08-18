import numpy as _np

from mpi4py import MPI as _MPI

from jax import abstract_arrays
from jax.lax import create_token
from jax.core import Primitive
from jax.lib import xla_client
from jax.interpreters import xla, batching

from ..utils import (
    to_mpi_ptr,
    _unpack_builder,
    _ops,
    _constant_s32_scalar,
    _constant_u64_scalar,
    dtype_ptr,
)

from ..warn import warn_missing_omnistaging


# The Jax primitive
mpi_send_p = Primitive("send_mpi")  # Create the primitive


# This function applies the primitive to an AST
def Send(x, dest, tag=0, comm=_MPI.COMM_WORLD, token=None):
    if token is None:
        token = create_token(x)

    out = mpi_send_p.bind(x, token, dest=dest, tag=tag, comm=comm)
    return out


#  this function executes the primitive, when not under any transformation
def mpi_send_impl(x, token, dest, tag, comm):
    # TODO: make this support gpus (use cupy?)
    inpt = _np.asarray(x)
    comm.Send(inpt, dest=dest, tag=tag)
    return token


#  This function compiles the operation
def mpi_send_xla_encode(c, x, token, dest, tag, comm):
    warn_missing_omnistaging()

    c = _unpack_builder(c)
    x_shape = c.GetShape(x)
    dtype = x_shape.element_type()
    dims = x_shape.dimensions()

    # compute total number of elements in array
    nitems = dims[0]
    for el in dims[1:]:
        nitems *= el

    _nitems = _constant_s32_scalar(c, nitems)
    _dtype_ptr = dtype_ptr(dtype)

    # ensure void** out type
    sh = xla_client.Shape.tuple_shape([
        xla_client.Shape.token_shape()
    ])

    out = _ops.CustomCall(
        c,
        b"mpi_send",
        operands=(
            _nitems,
            x,
            _constant_s32_scalar(c, dest),
            _constant_s32_scalar(c, tag),
            _constant_u64_scalar(c, to_mpi_ptr(comm)),
            _constant_u64_scalar(c, _dtype_ptr),
            token,
        ),
        shape=sh,
        has_side_effect=True,
    )

    return xla_client.ops.GetTupleElement(out, 0)


# This function evaluates only the shapes during AST construction
def mpi_send_abstract_eval(xs, token, dest, tag, comm):
    return abstract_arrays.abstract_token


# This function binds the batched transformation.
def mpi_send_batching(in_args, batch_axes, **kwargs):
    (x,) = in_args
    res = Send(x, **kwargs)
    return res, batch_axes[0]


# mpi_send_p.multiple_results = True
mpi_send_p.def_impl(mpi_send_impl)
mpi_send_p.def_abstract_eval(mpi_send_abstract_eval)

batching.primitive_batchers[mpi_send_p] = mpi_send_batching

# assign to the primitive the correct encoder
xla.backend_specific_translations["cpu"][mpi_send_p] = mpi_send_xla_encode
